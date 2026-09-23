import argparse
import datetime
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `gridpulse`

from gridpulse.season import race_on_date

# Run daily (cron / Task Scheduler). On a race-weekend day it starts the
# live producer and generates that day's sessions.
# The calendar lives in gridpulse/season.py (this file used to keep its own
# copy, which disagreed with the generator's on the Hungarian GP).

SCRIPT_DIR = Path(__file__).resolve().parent
# How long the producer lingers once the queue is empty. It used to run
# forever, so every race day stacked up another copy.
PRODUCER_IDLE_EXIT_SECONDS = 120


def check_and_launch_simulator(today_str):
    race, day_index = race_on_date(today_str)
    if race is None:
        print(f"Today ({today_str}) is not an F1 session day. No simulation started.")
        return

    print(f"Today is day {day_index + 1} of the {race.name} weekend! Starting live simulator...")
    python_executable = sys.executable
    try:
        print("Launching the live producer in the background...")
        # producer3 holds a lock, so this is a no-op if one is already running.
        subprocess.Popen([python_executable, str(SCRIPT_DIR / "producer3.py"),
                          "--exit-when-idle", str(PRODUCER_IDLE_EXIT_SECONDS)])
        time.sleep(5)
        print(f"Launching the live generator for '{race.name}' on date {today_str}...")
        subprocess.Popen([python_executable, str(SCRIPT_DIR / "generator_real_time.py"), race.name, today_str])
        print("Both live simulator processes launched successfully.")
    except OSError as e:
        print(f"Error launching simulator processes: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the live simulator on race-weekend days")
    parser.add_argument("--date", default=datetime.date.today().isoformat(),
                        help="pretend today is this date (YYYY-MM-DD), e.g. 2025-08-30")
    check_and_launch_simulator(parser.parse_args().date)
