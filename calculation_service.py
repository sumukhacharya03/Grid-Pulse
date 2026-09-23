"""Batch job: builds the market from the baseline values plus every
historical session, then publishes it as a fresh market epoch.

Safe to re-run: duplicate messages (e.g. from running a producer twice) are
collapsed, and consumers discard the previous epoch. Only history from the
chosen data source is used, so real and simulated runs can share a broker."""
import argparse

from gridpulse import roster
from gridpulse.config import (DATA_SOURCE, DATA_SOURCES, HISTORICAL_TOPICS, TOPIC_BASELINE, TOPIC_MARKET_TICKS,
                              TOPIC_STOCK_VALUES)
from gridpulse.kafka_io import ensure_topics, make_producer, read_to_end
from gridpulse.market import MarketEngine, result_sort_key, tick_id
from gridpulse.season import normalize_session


def collect_baselines(messages):
    baselines = {}
    for m in messages:
        data = m.value
        code = data.get("driver_code") or roster.code_for_name(data.get("driver_name"))
        if code in roster.DRIVERS and data.get("baseline_value") is not None:
            baselines[code] = (roster.DRIVERS[code]["name"], data["baseline_value"])  # latest wins
        else:
            print(f"Ignoring baseline for unknown driver: {data}")
    return baselines


def collect_results(messages, source):
    """One result per (round, session, driver) from `source`, latest wins, in race order."""
    unique = {}
    for m in messages:
        data = m.value
        if data.get("data_source", "simulated") != source:
            continue
        try:
            key = tick_id(data["round"], normalize_session(data.get("session_type")), data["driverCode"])
        except (KeyError, ValueError):
            print(f"Ignoring malformed result on {m.topic}: {data}")
            continue
        unique[key] = data
    return sorted(unique.values(), key=result_sort_key)


def main():
    parser = argparse.ArgumentParser(description="Build the market from baseline + historical data")
    parser.add_argument("--data", choices=DATA_SOURCES, default=DATA_SOURCE,
                        help=f"price the real or the simulated history (default: {DATA_SOURCE})")
    args = parser.parse_args()
    print(f"Starting BATCH Calculation Service for HISTORICAL data ({args.data})...")
    ensure_topics()

    print("Consuming all available baseline and historical messages...")
    baseline_messages = read_to_end([TOPIC_BASELINE])
    result_messages = read_to_end(HISTORICAL_TOPICS)
    print(f"Consumed {len(baseline_messages)} baseline and {len(result_messages)} result messages.")

    baselines = collect_baselines(baseline_messages)
    if not baselines:
        raise SystemExit("No baseline values found. Run baseline_market_value/producer1.py first.")
    missing = sorted(set(roster.DRIVERS) - set(baselines))
    if missing:
        print(f"WARNING: no baseline value for {', '.join(missing)}; they will not be traded.")

    engine = MarketEngine()
    epoch_record = engine.start_epoch(baselines)
    results = collect_results(result_messages, args.data)
    ticks = [t for t in (engine.apply(r) for r in results) if t]
    print(f"Processed {len(results)} unique results into {len(ticks)} price moves for {len(baselines)} drivers.")

    producer = make_producer()
    producer.send(TOPIC_MARKET_TICKS, key="epoch", value=epoch_record)
    for tick in ticks:
        producer.send(TOPIC_MARKET_TICKS, key=tick["driver_code"], value=tick)
    for code in engine.drivers:
        producer.send(TOPIC_STOCK_VALUES, key=code, value=engine.state_message(code))
    producer.flush()
    producer.close()

    print(f"Published market epoch {engine.epoch} to '{TOPIC_MARKET_TICKS}' and '{TOPIC_STOCK_VALUES}'.")
    for code, d in sorted(engine.drivers.items(), key=lambda kv: -kv[1]["current_value"]):
        change = (d["current_value"] / d["baseline_value"] - 1) * 100
        print(f"  {code}  ${d['current_value']:>14,.0f}  {change:+6.2f}%")
    print("Historical Calculation Service finished.")


if __name__ == "__main__":
    main()
