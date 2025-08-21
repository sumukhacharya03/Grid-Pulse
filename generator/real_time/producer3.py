import time
import json
import os
from kafka import KafkaProducer

KAFKA_BROKER = 'kafka:9092'
QUEUE_DIRECTORY = 'live_events_queue'

TOPICS = {
    "practice": "realtime-performance-practice",
    "qualifying": "realtime-performance-qualifying",
    "race": "realtime-performance-race"
}

def create_kafka_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Kafka Producer connected successfully.")
        return producer
    except Exception as e:
        print(f"Error connecting to Kafka: {e}")
        return None

def watch_and_produce(producer):
    print("Starting Live Event Producer... Watching for event files; Press Ctrl+C to stop")
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
                    
                    if 'practice' in session_type: topic = TOPICS['practice']
                    elif 'qualifying' in session_type: topic = TOPICS['qualifying']
                    elif 'race' in session_type: topic = TOPICS['race']

                    if topic:
                        producer.send(topic, key=driver_code.encode('utf-8'), value=event)
                        print(f"  > Sent {session_type} event for {driver_code} to topic '{topic}'")
                    
                    os.remove(filepath)

                except (json.JSONDecodeError, KeyError, PermissionError) as e:
                    print(f"Error processing file {filename}: {e}; Deleting corrupt/locked file")
                    try: os.remove(filepath)
                    except OSError as e_os: print(f"Could not delete file {filepath}: {e_os}")
            
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

# Kafka Commands for later (all in Kafka Directory)
# 1. Create Topic:
# ./kafka-topics.sh --create --topic realtime-performance-practice --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# ./kafka-topics.sh --create --topic realtime-performance-race --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# ./kafka-topics.sh --create --topic realtime-performance-qualifying --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# 2. Delete Topic:
# ./kafka-topics.sh --delete --topic realtime-performance-practice --bootstrap-server localhost:9092
# ./kafka-topics.sh --delete --topic realtime-performance-race --bootstrap-server localhost:9092
# ./kafka-topics.sh --delete --topic realtime-performance-qualifying --bootstrap-server localhost:9092
# 3. Check list of Topics:
# ./kafka-topics.sh --list --bootstrap-server localhost:9092
# 4. To go to Kafka Directory:
# cd ~/kafka_2.13-3.7.0/bin
# 5. Check messages sent to a Topic:
# ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic realtime-performance-practice --from-beginning
# ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic realtime-performance-race --from-beginning
# ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic realtime-performance-qualifying --from-beginning
# 6. Keep Zookeeper running:
# ./bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
# 7. Keep Kafka Broker running (in another terminal):
# ./bin/kafka-server-start.sh -daemon config/server.properties
# How to stop Kafka Broker:
# ./bin/kafka-server-stop.sh
# How to stop Zookeeper Server:
# ./bin/zookeeper-server-stop.sh
