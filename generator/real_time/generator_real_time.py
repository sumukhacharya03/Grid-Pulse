import argparse
import json
import os
import random
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `gridpulse`

from gridpulse.config import DATA_SOURCE, DATA_SOURCES, LIVE_QUEUE_DIR, LIVE_WEEKEND_STATE_DIR
from gridpulse.history import live_weekend
from gridpulse.season import HISTORICAL_ROUNDS, race_by_name

# Streams live sessions into the queue directory, one JSON file per driver
# result; producer3.py ships them to Kafka. With --data real the sessions are
# the actual 2025 results replayed; with --data simulated they are simulated.
#
#   python generator_real_time.py "Dutch Grand Prix" 2025-08-30    # that day's sessions (cron)
#   python generator_real_time.py "Dutch Grand Prix" --weekend      # the whole weekend, now


def write_event(event):
    """Write atomically: the producer only ever sees complete files (it used
    to catch half-written ones, fail to parse them and delete them)."""
    name = f"{datetime.now().timestamp():.6f}_{uuid.uuid4()}"
    tmp = LIVE_QUEUE_DIR / f"{name}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(event, f)
    os.replace(tmp, LIVE_QUEUE_DIR / f"{name}.json")


def state_path(race):
    return LIVE_WEEKEND_STATE_DIR / f"{race.name.lower().replace(' ', '_')}.json"


def load_grids(race):
    try:
        with open(state_path(race), encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_grids(race, grids):
    LIVE_WEEKEND_STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(state_path(race), "w", encoding="utf-8") as f:
        json.dump(grids, f)


def main():
    parser = argparse.ArgumentParser(description="Generate live race weekend events")
    parser.add_argument("race", help='e.g. "Dutch Grand Prix"')
    parser.add_argument("date", nargs="?", help="weekend date (YYYY-MM-DD) whose sessions to run")
    parser.add_argument("--weekend", action="store_true", help="run every session of the weekend")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="average seconds between results (default 1.0; 0 for instant)")
    parser.add_argument("--seed", type=int, help="random seed for a reproducible simulated weekend")
    parser.add_argument("--data", choices=DATA_SOURCES, default=DATA_SOURCE,
                        help=f"replay real results or simulate (default: {DATA_SOURCE})")
    args = parser.parse_args()

    try:
        race = race_by_name(args.race)
    except KeyError as e:
        sys.exit(str(e))
    if race.round <= HISTORICAL_ROUNDS:
        print(f"Note: {race.name} is part of the historical data; its results are already priced.")

    if args.weekend:
        sessions = [s[0] for s in race.sessions]
    else:
        date = args.date or datetime.now().date().isoformat()
        if date not in race.dates:
            sys.exit(f"{date} is not part of the {race.name} weekend ({', '.join(race.dates)}). "
                     f"Use --weekend to run the whole weekend now.")
        sessions = [s[0] for s in race.sessions_on_day(race.dates.index(date))]

    print(f"Starting Live Generator for '{race.name}' (round {race.round}): {', '.join(sessions)}")
    LIVE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    # Grids persist between cron runs, so Sunday's simulated race starts in
    # the order Saturday's qualifying produced.
    try:
        sim = live_weekend(race, args.data, rng, grids=load_grids(race))
    except FileNotFoundError as e:
        sys.exit(str(e))

    for session_key in sessions:
        results = sim.live_results(session_key)
        if args.data == "simulated":
            save_grids(race, sim.grids)
        print(f"\nSession: {results[0]['session_name']}")
        for result in results:
            write_event(result)
            pos = result.get("position") or result.get("finishingPosition") or "DNF"
            print(f"  P{pos} {result['driverCode']}")
            if args.delay:
                time.sleep(random.uniform(0.5, 1.5) * args.delay)
        print(f"Session Generation Complete: {results[0]['session_name']}")

    print(f"\nAll requested sessions for {race.name} are complete. Generator is exiting.")


if __name__ == "__main__":
    main()
