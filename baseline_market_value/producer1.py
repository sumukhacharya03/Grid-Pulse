from kafka import KafkaProducer

topic_name='drivers_baseline_value'
producer=KafkaProducer(bootstrap_servers='localhost:9092')

with open('drivers_baseline_value.csv', 'r') as file:
    for line in file:
        producer.send(topic_name, value=line.encode('utf-8'))

producer.flush()
