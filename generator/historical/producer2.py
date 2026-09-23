import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `gridpulse`

from gridpulse.config import DATA_SOURCE, DATA_SOURCES, TOPIC_HIST_PRACTICE, TOPIC_HIST_QUALIFYING, TOPIC_HIST_RACE
from gridpulse.history import historical_weekends, weekend_sessions
from gridpulse.kafka_io import ensure_topics, make_producer
from gridpulse.season import SESSION_KIND

TOPIC_FOR_KIND = {
    "practice": TOPIC_HIST_PRACTICE,
    "qualifying": TOPIC_HIST_QUALIFYING,
    "sprint_qualifying": TOPIC_HIST_QUALIFYING,
    "race": TOPIC_HIST_RACE,
    "sprint": TOPIC_HIST_RACE,
}


def produce_historical_data(producer, source):
    try:
        weekends = historical_weekends(source)
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"Error: {e}")

    print(f"Sending {len(weekends)} {source} race weekends (the historical part of the season)")
    total_messages = 0
    for weekend in weekends:
        print(f"\n--- Round {weekend['round']}: {weekend['raceName']} ---")
        for session_key, results in weekend_sessions(weekend):
            topic = TOPIC_FOR_KIND[SESSION_KIND[session_key]]
            for result in results:
                result["data_source"] = source  # lets calculation_service keep sources apart
                producer.send(topic, key=result.get("driverCode", "UNKNOWN"), value=result)
            total_messages += len(results)
            print(f"  Queued {len(results)} messages for {session_key} to topic '{topic}'")

    producer.flush()
    print(f"\nSuccessfully sent a total of {total_messages} historical messages to Kafka")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send the historical race weekends to Kafka")
    parser.add_argument("--data", choices=DATA_SOURCES, default=DATA_SOURCE,
                        help=f"real 2025 results or the simulated season (default: {DATA_SOURCE})")
    args = parser.parse_args()
    ensure_topics()
    kafka_producer = make_producer()
    produce_historical_data(kafka_producer, args.data)
    kafka_producer.close()
