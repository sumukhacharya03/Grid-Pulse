"""Long-running service: prices live race-weekend results as they arrive.

On start it rebuilds the market by replaying `market-ticks` (so it resumes
exactly where it left off), then consumes the real-time topics. Every result
is applied at most once per epoch, even if a producer sends it twice."""
from kafka import KafkaConsumer, TopicPartition

from gridpulse.config import KAFKA_BROKER, REALTIME_TOPICS, TOPIC_MARKET_TICKS, TOPIC_STOCK_VALUES
from gridpulse.kafka_io import deserialize, ensure_topics, make_producer, read_to_end
from gridpulse.market import MarketEngine


def load_market():
    print("Rebuilding market state from Kafka...")
    engine = MarketEngine()
    for message in read_to_end([TOPIC_MARKET_TICKS]):
        engine.replay(message.value)
    if engine.epoch is None:
        raise SystemExit("FATAL: No market found in 'market-ticks'.\n"
                         "Please run 'calculation_service.py' once to process historical data.")
    print(f"Market epoch {engine.epoch} loaded: {len(engine.drivers)} drivers, {len(engine.ticks)} price moves.")
    return engine


def tail_consumer(topic):
    """Positioned at the end of `topic`, to notice new epochs from the batch job."""
    consumer = KafkaConsumer(bootstrap_servers=KAFKA_BROKER, value_deserializer=deserialize,
                             enable_auto_commit=False, group_id=None)
    tp = TopicPartition(topic, 0)
    consumer.assign([tp])
    consumer.seek_to_end(tp)
    return consumer


def main():
    ensure_topics()
    engine = load_market()
    producer = make_producer()
    epoch_watch = tail_consumer(TOPIC_MARKET_TICKS)
    consumer = KafkaConsumer(
        *REALTIME_TOPICS,
        bootstrap_servers=KAFKA_BROKER,
        # 'earliest' so events produced while this service was down are not
        # lost; anything already priced is skipped by the engine.
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id="gridpulse-realtime-service",
        value_deserializer=deserialize,
    )

    print("\nReal-time Calculation Service is running and listening for live events...")
    try:
        while True:
            for batch in epoch_watch.poll(timeout_ms=0).values():
                for m in batch:
                    if m.value and engine.replay(m.value) == "epoch":
                        print(f"\nMarket was rebuilt by the batch job; now on epoch {engine.epoch}.")

            records = consumer.poll(timeout_ms=1000)
            for batch in records.values():
                for message in batch:
                    data = message.value
                    if not data:
                        continue
                    tick = engine.apply(data, live=True)
                    if tick is None:
                        print(f"Skipped {data.get('driverCode')} {data.get('session_type')} (duplicate or unknown)")
                        continue
                    producer.send(TOPIC_MARKET_TICKS, key=tick["driver_code"], value=tick)
                    producer.send(TOPIC_STOCK_VALUES, key=tick["driver_code"],
                                  value=engine.state_message(tick["driver_code"]))
                    print(f"{tick['race']} {tick['session_name']}: {tick['driver_code']} "
                          f"{tick['change_pct']:+.2f}% -> ${tick['value_after']:,.0f}")
            if records:
                producer.flush()
                consumer.commit()
    except KeyboardInterrupt:
        print("\nShutting down Real-time Service...")
    finally:
        consumer.close()
        epoch_watch.close()
        producer.close()
        print("Service stopped.")


if __name__ == "__main__":
    main()
