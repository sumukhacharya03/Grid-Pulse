import json
from kafka import KafkaConsumer, KafkaProducer
import time

# --- Configuration ---
KAFKA_BROKER = 'kafka:29092'
INPUT_TOPICS = [
    'drivers-baseline-value',
    'historical-performance-practice',
    'historical-performance-qualifying',
    'historical-performance-race'
]
OUTPUT_TOPIC = 'driver-stock-values'

# --- In-Memory Data Store ---
drivers_data = {}

# Manual mapping from full driver names to 3-letter codes
DRIVER_CODE_MAP = {
    "Max Verstappen": "VER", "Lewis Hamilton": "HAM", "Oscar Piastri": "PIA",
    "Lando Norris": "NOR", "Charles Leclerc": "LEC", "Fernando Alonso": "ALO",
    "George Russell": "RUS", "Pierre Gasly": "GAS", "Carlos Sainz": "SAI",
    "Kimi Antonelli": "ANT", "Ollie Bearman": "BEA", "Gabriel Bortoleto": "BOR",
    "Jack Doohan": "DOO", "Franco Colapinto": "COL", "Yuki Tsunoda": "TSU",
    "Liam Lawson": "LAW", "Isack Hadjar": "HAD", "Lance Stroll": "STR",
    "Nico Hulkenberg": "HUL", "Esteban Ocon": "OCO", "Alex Albon": "ALB"
}


def apply_change(driver_code, percentage_change):
    if driver_code in drivers_data:
        drivers_data[driver_code]['current_value'] *= (1 + percentage_change)


def process_message(data, topic):
    if topic == 'drivers-baseline-value':
        driver_name = data.get('driver_name')
        driver_code = DRIVER_CODE_MAP.get(driver_name)
        if driver_code and driver_code not in drivers_data:
            drivers_data[driver_code] = {
                'driver_name': driver_name,
                'driver_code': driver_code,
                'baseline_value': data.get('baseline_value'),
                'current_value': data.get('baseline_value')
            }
    else:
        driver_code = data.get('driverCode')
        if not driver_code or driver_code not in drivers_data:
            return

        position = data.get('position') or data.get('finishingPosition')

        if 'practice' in topic and position and position <= 3:
            apply_change(driver_code, 0.0005)
        elif 'qualifying' in topic and position:
            if position == 1:
                apply_change(driver_code, 0.005)
            elif position <= 3:
                apply_change(driver_code, 0.002)
        elif 'race' in topic:
            points = data.get('points', 0)
            if points > 0: apply_change(driver_code, points * 0.001)
            if data.get('fastestLap'): apply_change(driver_code, 0.0025)
            if data.get('crashes', 0) > 0 or data.get('collisions', 0) > 0: apply_change(driver_code, -0.02)
            if data.get('status') != 'Finished': apply_change(driver_code, -0.015)


def main():
    print("Starting Calculation Service...")

    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    consumer.subscribe(INPUT_TOPICS)

    print("Consuming all available messages from topics. This will take a moment...")

    all_messages = []
    empty_polls = 0
    # Poll for messages. If we get 5 empty polls in a row, we assume the topics are drained.
    while empty_polls < 5:
        # Poll with a 1-second timeout
        records = consumer.poll(timeout_ms=1000)
        if not records:
            empty_polls += 1
            print(f"Polling... No new messages found ({empty_polls}/5)")
            continue

        empty_polls = 0  # Reset counter if we get messages
        for topic_partition, messages in records.items():
            all_messages.extend(messages)

    consumer.close()
    print(f"\nSuccessfully consumed {len(all_messages)} messages. Now processing...")

    # Process baseline messages first
    for message in all_messages:
        if message.topic == 'drivers-baseline-value':
            process_message(message.value, message.topic)

    # Process performance messages
    for message in all_messages:
        if message.topic != 'drivers-baseline-value':
            process_message(message.value, message.topic)

    print(f"Processing complete. Calculated values for {len(drivers_data)} drivers.")

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )

    print("Publishing final stock values to 'driver-stock-values'...")
    for driver_code, data in drivers_data.items():
        producer.send(OUTPUT_TOPIC, key=driver_code.encode('utf-8'), value=data)

    producer.flush()
    producer.close()

    print(f"Successfully published all driver stock values.")
    print("Calculation Service finished.")


if __name__ == "__main__":
    main()
