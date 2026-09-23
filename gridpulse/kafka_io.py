"""Kafka plumbing shared by every service."""
import json
import time

from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import NoBrokersAvailable, TopicAlreadyExistsError

from .config import ALL_TOPICS, KAFKA_BROKER, TOPIC_STOCK_VALUES

# Kafka's default retention is 7 days, after which the baseline and
# historical topics would silently empty out. Keep everything.
TOPIC_CONFIG = {"retention.ms": "-1"}
COMPACTED_TOPICS = {TOPIC_STOCK_VALUES}


def _serialize(value):
    return json.dumps(value).encode("utf-8")


def deserialize(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def wait_for_broker(broker=KAFKA_BROKER, attempts=10, delay=3):
    for attempt in range(1, attempts + 1):
        try:
            admin = KafkaAdminClient(bootstrap_servers=broker, client_id="gridpulse-admin")
            return admin
        except NoBrokersAvailable:
            print(f"Kafka not reachable at {broker} (attempt {attempt}/{attempts}); retrying in {delay}s")
            time.sleep(delay)
    raise SystemExit(f"Could not reach Kafka at {broker}. Is the broker running? (docker compose up -d)")


def ensure_topics(broker=KAFKA_BROKER, topics=ALL_TOPICS):
    """Create any missing Grid-Pulse topics, so no manual kafka-topics.sh step is needed."""
    admin = wait_for_broker(broker)
    try:
        existing = set(admin.list_topics())
        missing = [t for t in topics if t not in existing]
        if missing:
            new = []
            for t in missing:
                config = dict(TOPIC_CONFIG)
                if t in COMPACTED_TOPICS:
                    config["cleanup.policy"] = "compact"
                new.append(NewTopic(name=t, num_partitions=1, replication_factor=1, topic_configs=config))
            try:
                admin.create_topics(new)
                print(f"Created Kafka topics: {', '.join(missing)}")
            except TopicAlreadyExistsError:
                pass
    finally:
        admin.close()


def make_producer(broker=KAFKA_BROKER):
    return KafkaProducer(bootstrap_servers=broker, value_serializer=_serialize,
                         key_serializer=lambda k: k.encode("utf-8") if isinstance(k, str) else k,
                         acks="all")


def _assign_from_start(consumer, topics):
    partitions = []
    for topic in topics:
        for p in consumer.partitions_for_topic(topic) or ():
            partitions.append(TopicPartition(topic, p))
    consumer.assign(partitions)
    consumer.seek_to_beginning(*partitions)
    return partitions


def read_to_end(topics, broker=KAFKA_BROKER):
    """Every message currently on `topics`, in per-partition order.

    Reads until each partition's end offset instead of stopping at the first
    empty poll, which could return nothing while the consumer was still
    connecting."""
    consumer = KafkaConsumer(bootstrap_servers=broker, value_deserializer=deserialize,
                             enable_auto_commit=False, group_id=None)
    try:
        partitions = _assign_from_start(consumer, topics)
        if not partitions:
            return []
        end = consumer.end_offsets(partitions)
        messages = []
        while any(consumer.position(tp) < end[tp] for tp in partitions):
            for batch in consumer.poll(timeout_ms=1000).values():
                messages.extend(m for m in batch if m.value is not None)
        return messages
    finally:
        consumer.close()


def follow(topics, broker=KAFKA_BROKER, on_caught_up=None, stop=None):
    """Yield every message on `topics` from the beginning, then keep tailing.
    `on_caught_up` fires once the backlog that existed at start is consumed;
    `stop` is an optional threading.Event that ends the loop."""
    consumer = KafkaConsumer(bootstrap_servers=broker, value_deserializer=deserialize,
                             enable_auto_commit=False, group_id=None)
    try:
        partitions = _assign_from_start(consumer, topics)
        end = consumer.end_offsets(partitions) if partitions else {}
        caught_up = False
        while not (stop and stop.is_set()):
            for batch in consumer.poll(timeout_ms=500).values():
                for m in batch:
                    if m.value is not None:
                        yield m
            if not caught_up and all(consumer.position(tp) >= end[tp] for tp in partitions):
                caught_up = True
                if on_caught_up:
                    on_caught_up()
    finally:
        consumer.close()
