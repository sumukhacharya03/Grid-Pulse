import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root, for `gridpulse`

from gridpulse.baseline import read_baselines
from gridpulse.config import BASELINE_CSV, TOPIC_BASELINE
from gridpulse.kafka_io import ensure_topics, make_producer

# Publishes each driver's baseline value ("$78 M" -> 78000000) to Kafka.
baselines, problems = read_baselines(BASELINE_CSV)
for problem in problems:
    # Unknown names used to be dropped silently further down the pipeline
    # (that is how a typo kept Esteban Ocon out of the market).
    print(f"Skipping row: {problem}")

ensure_topics()
producer = make_producer()

for code, (name, value) in baselines.items():
    message = {"driver_name": name, "driver_code": code, "baseline_value": int(value)}
    # I am using the driver's name as the key
    producer.send(TOPIC_BASELINE, key=name, value=message)
    print(f"Message Sent: {message}")

producer.flush()
producer.close()
print(f"All {len(baselines)} baseline messages sent successfully")

# Topics are created automatically now (gridpulse.kafka_io.ensure_topics).
# Handy Kafka commands for inspecting them (with the docker-compose broker):
# docker exec -it gridpulse-kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092
# docker exec -it gridpulse-kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic drivers-baseline-value --from-beginning
