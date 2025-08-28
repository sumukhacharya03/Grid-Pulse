import json
from kafka import KafkaProducer
import os
import time

KAFKA_BROKER = 'kafka:29092'
HISTORICAL_DIR = 'generator/historical/generated_historical_results'
TOPICS = {
    "practice": "historical-performance-practice",
    "qualifying": "historical-performance-qualifying",
    "sprint_qualifying": "historical-performance-qualifying",
    "race": "historical-performance-race",
    "sprint_race": "historical-performance-race"
}

def create_kafka_producer():
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        print("Kafka Producer connected successfully")
        return producer
    except Exception as e:
        print(f"Error connecting to Kafka: {e}")
        return None

def produce_historical_data(producer):
    if not os.path.isdir(HISTORICAL_DIR):
        print(f"Error: Directory '{HISTORICAL_DIR}' not found; Run the generator script first")
        return

    json_files = [f for f in os.listdir(HISTORICAL_DIR) if f.endswith('.json')]
    if not json_files:
        print(f"No JSON result files found in '{HISTORICAL_DIR}'")
        return
    
    print(f"Found {len(json_files)} race weekend files to process from '{HISTORICAL_DIR}'")
    total_messages = 0

    for filename in sorted(json_files):
        filepath = os.path.join(HISTORICAL_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            weekend = json.load(f)
        
        race_name = weekend['raceName']
        print(f"\n--- Processing {race_name} ---")
        
        def send_batch(session_key, session_type, topic):
            if session_key not in weekend:
                return 0
            count = 0
            for result in weekend[session_key]:
                result.update({
                    'raceName': race_name, 'season': weekend['season'],
                    'round': weekend['round'], 'session_type': session_type
                })
                driver_code = result.get('driverCode', 'UNKNOWN')
                producer.send(topic, key=driver_code.encode('utf-8'), value=result)
                count += 1
            print(f"  Queued {count} messages for {session_type} to topic '{topic}'")
            return count

        total_messages += send_batch("practice1Results", "practice1", TOPICS['practice'])
        total_messages += send_batch("practice2Results", "practice2", TOPICS['practice'])
        total_messages += send_batch("practice3Results", "practice3", TOPICS['practice'])
        total_messages += send_batch("sprintQualifyingResults", "sprint_qualifying", TOPICS['sprint_qualifying'])
        total_messages += send_batch("sprintRaceResults", "sprint_race", TOPICS['sprint_race'])
        total_messages += send_batch("qualifyingResults", "qualifying", TOPICS['qualifying'])
        total_messages += send_batch("raceResults", "race", TOPICS['race'])
        
    producer.flush()
    print(f"\n")
    print(f"Successfully sent a total of {total_messages} historical messages to Kafka")


if __name__ == "__main__":
    kafka_producer = create_kafka_producer()
    if kafka_producer:
        produce_historical_data(kafka_producer)
        kafka_producer.close()

# Kafka Commands for later (all in Kafka Directory)
# 1. Create Topic:
# ./kafka-topics.sh --create --topic historical-performance-practice --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# ./kafka-topics.sh --create --topic historical-performance-race --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# ./kafka-topics.sh --create --topic historical-performance-qualifying --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# 2. Delete Topic:
# ./kafka-topics.sh --delete --topic historical-performance-practice --bootstrap-server localhost:9092
# ./kafka-topics.sh --delete --topic historical-performance-race --bootstrap-server localhost:9092
# ./kafka-topics.sh --delete --topic historical-performance-qualifying --bootstrap-server localhost:9092
# 3. Check list of Topics:
# ./kafka-topics.sh --list --bootstrap-server localhost:9092
# 4. To go to Kafka Directory:
# cd ~/kafka_2.13-3.7.0/bin
# 5. Check messages sent to a Topic:
# ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic historical-performance-practice --from-beginning
# ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic historical-performance-race --from-beginning
# ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic historical-performance-qualifying --from-beginning
# 6. Keep Zookeeper running:
# ./bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
# 7. Keep Kafka Broker running (in another terminal):
# ./bin/kafka-server-start.sh -daemon config/server.properties
# How to stop Kafka Broker:
# ./bin/kafka-server-stop.sh
# How to stop Zookeeper Server:
# ./bin/zookeeper-server-stop.sh
