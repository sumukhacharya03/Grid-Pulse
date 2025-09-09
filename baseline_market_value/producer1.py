import csv
import json
from kafka import KafkaProducer

topic_name = 'drivers-baseline-value'

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    # Serializes dictionary to JSON bytes
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

with open('drivers_baseline_value.csv', mode='r', encoding='utf-8') as file:
    csv_reader = csv.DictReader(file) # Reads rows as dictionaries
    for row in csv_reader:
        # Converts the values to numbers like 78M to 78000000
        try:
            value_str = row['Baseline Value'].strip().replace('$', '').replace(' ', '')
            if 'M' in value_str:
                value_num = float(value_str.replace('M', '')) * 1_000_000
            else: # To add more conditions later if needed for cases other than M
                value_num = float(value_str)

            message = {
                'driver_name': row['Driver Name'],
                'baseline_value': int(value_num)
            }
            
            # I am using the driver's name as the key
            producer.send(topic_name, key=row['Driver Name'].encode('utf-8'), value=message)
            print(f"Message Sent: {message}")
            
        except (ValueError, AttributeError) as e:
            print(f"Skipping row due to parsing error: {row} - {e}")


producer.flush()
print("All messages sent successfully")


# Kafka Commands for later (all in Kafka Directory)
# 1. Create Topic:
# ./kafka-topics.sh --create --topic drivers-baseline-value --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
# 2. Delete Topic:
# ./kafka-topics.sh --delete --topic drivers-baseline-value --bootstrap-server localhost:9092
# 3. Check list of Topics:
# ./kafka-topics.sh --list --bootstrap-server localhost:9092
# 4. To go to Kafka Directory:
# cd ~/kafka_2.13-3.7.0/bin
# 5. Check messages sent to a Topic:
# ./kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic drivers-baseline-value --from-beginning
# 6. Keep Zookeeper running:
# ./bin/zookeeper-server-start.sh -daemon config/zookeeper.properties
# 7. Keep Kafka Broker running (in another terminal):
# ./bin/kafka-server-start.sh -daemon config/server.properties
# 8. How to stop Kafka Broker:
# ./bin/kafka-server-stop.sh
# 9. How to stop Zookeeper Server:
# ./bin/zookeeper-server-stop.sh
