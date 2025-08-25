import time
import json
import os
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

KAFKA_BROKER = 'kafka:9092'
QUEUE_DIRECTORY = 'generator/real_time/live_events_queue'
MAX_CONNECTION_RETRIES = 10
RETRY_DELAY_SECONDS = 5

TOPICS = {
    "practice": "realtime-performance-practice",
    "qualifying": "realtime-performance-qualifying",
    "race": "realtime-performance-race"
}


def create_kafka_producer():
    retries = 0
    while retries < MAX_CONNECTION_RETRIES:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BROKER,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            print("Kafka Producer connected successfully")
            return producer
        except NoBrokersAvailable:
            retries += 1
            print(
                f"Failed to connect to Kafka. Retrying in {RETRY_DELAY_SECONDS}s ({retries}/{MAX_CONNECTION_RETRIES})")
            time.sleep(RETRY_DELAY_SECONDS)
    print("Error: Could not connect to Kafka after several retries")
    return None


def watch_and_produce(producer):
    print(f"Starting Live Event Producer... Watching for event files in '{QUEUE_DIRECTORY}'. Press Ctrl+C to stop.")
    if not os.path.exists(QUEUE_DIRECTORY):
        os.makedirs(QUEUE_DIRECTORY)

    while True:
        try:
            event_files = [f for f in os.listdir(QUEUE_DIRECTORY) if f.endswith('.json')]
            if not event_files:
                time.sleep(1)
                continue

            for filename in sorted(event_files):
                filepath = os.path.join(QUEUE_DIRECTORY, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        event = json.load(f)

                    session_type = event.get('session_type', '').lower()
                    driver_code = event.get('driverCode', 'UNKNOWN')
                    topic = None

                    if 'practice' in session_type:
                        topic = TOPICS['practice']
                    elif 'qualifying' in session_type:
                        topic = TOPICS['qualifying']
                    elif 'race' in session_type:
                        topic = TOPICS['race']

                    if topic:
                        producer.send(topic, key=driver_code.encode('utf-8'), value=event)
                        print(f"Sent {session_type} event for {driver_code} to topic '{topic}'")

                    os.remove(filepath)

                except (json.JSONDecodeError, KeyError, PermissionError) as e:
                    print(f"Error processing file {filename}: {e}; Deleting corrupt/locked file")
                    try:
                        os.remove(filepath)
                    except OSError as e_os:
                        print(f"Could not delete file {filepath}: {e_os}")

            producer.flush()

        except KeyboardInterrupt:
            print("\nShutting down producer")
            break
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            time.sleep(5)


if __name__ == "__main__":
    kafka_producer = create_kafka_producer()
    if kafka_producer:
        watch_and_produce(kafka_producer)
        kafka_producer.close()