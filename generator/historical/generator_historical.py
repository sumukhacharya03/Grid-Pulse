import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `gridpulse`

from gridpulse.config import HISTORICAL_DIR
from gridpulse.season import CALENDAR, HISTORICAL_ROUNDS
from gridpulse.simulation import WeekendSimulator

# Builds the simulated results for the first half of the 2025 season
# (rounds 1-14), one JSON file per race weekend.


def race_filename(race_name):
    return f"{race_name.lower().replace(' ', '_')}.json"


def main():
    parser = argparse.ArgumentParser(description="Generate historical race weekend results")
    parser.add_argument("--seed", type=int, default=2025,
                        help="random seed, so the same history can be rebuilt (default: 2025)")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    HISTORICAL_DIR.mkdir(parents=True, exist_ok=True)

    for race in CALENDAR:
        if race.round > HISTORICAL_ROUNDS:
            break
        weekend = WeekendSimulator(race, rng).run_weekend()
        filepath = HISTORICAL_DIR / race_filename(race.name)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(weekend, f, indent=2)
        print(f"Saved Results to {filepath}")
    print("Generated all Races Historical Data")


if __name__ == "__main__":
    main()
