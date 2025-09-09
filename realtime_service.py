import json
from kafka import KafkaConsumer, KafkaProducer
import time

# --- Configuration ---
KAFKA_BROKER = 'localhost:9092'
REALTIME_INPUT_TOPICS = [
    'realtime-performance-practice',
    'realtime-performance-qualifying',
    'realtime-performance-race'
]
STATE_TOPIC = 'driver-stock-values' # This is both our input for state and output for updates

# --- In-Memory Data Store ---
drivers_data = {}

def apply_change(driver_code, percentage_change):
    if driver_code in drivers_data and 'current_value' in drivers_data[driver_code]:
        drivers_data[driver_code]['current_value'] *= (1 + percentage_change)
        print(f"Applied {percentage_change*100:.4f}% change to {driver_code}. New value: ${drivers_data[driver_code]['current_value']:,.2f}")
    else:
        print(f"Could not apply change, driver {driver_code} not found in memory.")

def process_realtime_message(data, topic):
    driver_code = data.get('driverCode')
    if not driver_code or driver_code not in drivers_data:
        return False

    position = data.get('position') or data.get('finishingPosition')

    # Using the same balanced weights
    if 'practice' in topic and position and position <= 3:
        apply_change(driver_code, 0.0003)
    elif 'qualifying' in topic and position:
        if position == 1:
            apply_change(driver_code, 0.003)
        elif position <= 3:
            apply_change(driver_code, 0.001)
    elif 'race' in topic:
        points = data.get('points', 0)
        if points > 0: apply_change(driver_code, points * 0.0005)
        if data.get('fastestLap'): apply_change(driver_code, 0.0015)
        if data.get('crashes', 0) > 0 or data.get('collisions', 0) > 0: apply_change(driver_code, -0.005)
        if data.get('status') != 'Finished': apply_change(driver_code, -0.003)
    
    return True

def load_initial_state(broker):
    """Reads the driver-stock-values topic to build the current market state."""
    print("Loading initial market state from Kafka...")
    state_consumer = KafkaConsumer(
        STATE_TOPIC,
        bootstrap_servers=broker,
        auto_offset_reset='earliest',
        consumer_timeout_ms=10000, # Stop after 10s of no new messages
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in state_consumer:
        driver_code = message.key.decode('utf-8')
        drivers_data[driver_code] = message.value
    
    state_consumer.close()
    if not drivers_data:
        print("FATAL: No initial state found in 'driver-stock-values' topic.")
        print("Please run the main 'calculation_service.py' once to process historical data.")
        exit()
    print(f"Initial state loaded successfully for {len(drivers_data)} drivers.")


def main():
    # Phase 1: Load the last known state from our state topic
    load_initial_state(KAFKA_BROKER)

    # Phase 2: Connect to real-time topics and start processing
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    
    consumer = KafkaConsumer(
        *REALTIME_INPUT_TOPICS,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset='latest', # IMPORTANT: Only process new messages
        group_id='gridpulse-realtime-service', # A fixed group ID for this service
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    print("\n🚀 Real-time Calculation Service is running and listening for live events...")
    
    try:
        for message in consumer:
            print(f"\nReceived new event from topic '{message.topic}' for {message.value.get('driverCode')}")
            if process_realtime_message(message.value, message.topic):
                driver_code = message.value.get('driverCode')
                if driver_code and driver_code in drivers_data:
                    # Publish the ENTIRE updated driver object back to the state topic
                    producer.send(STATE_TOPIC, key=driver_code.encode('utf-8'), value=drivers_data[driver_code])
                    producer.flush()

    except KeyboardInterrupt:
        print("\nShutting down Real-time Service...")
    finally:
        consumer.close()
        producer.close()
        print("Service stopped.")

if __name__ == "__main__":
    main()
