import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `gridpulse`

from gridpulse.config import LIVE_QUEUE_DIR, TOPIC_LIVE_PRACTICE, TOPIC_LIVE_QUALIFYING, TOPIC_LIVE_RACE
from gridpulse.kafka_io import ensure_topics, make_producer
from gridpulse.season import SESSION_KIND, normalize_session

TOPIC_FOR_KIND = {
    "practice": TOPIC_LIVE_PRACTICE,
    "qualifying": TOPIC_LIVE_QUALIFYING,
    "sprint_qualifying": TOPIC_LIVE_QUALIFYING,
    "race": TOPIC_LIVE_RACE,
    "sprint": TOPIC_LIVE_RACE,  # "Sprint" used to match no topic, so sprint results were dropped
}
FAILED_DIR = LIVE_QUEUE_DIR / "failed"
LOCK_PATH = LIVE_QUEUE_DIR / ".producer3.lock"


def acquire_single_instance_lock():
    """Only one producer may drain the queue; two would both send the same
    file before either deleted it. The OS releases the lock if we crash."""
    LIVE_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK_PATH, "a+")
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def quarantine(path, reason):
    print(f"Moving unreadable event {path.name} to {FAILED_DIR}: {reason}")
    FAILED_DIR.mkdir(exist_ok=True)
    shutil.move(str(path), FAILED_DIR / path.name)


def drain_queue(producer):
    """Send every queued event; delete a file only once Kafka has acked it."""
    in_flight = []
    for path in sorted(LIVE_QUEUE_DIR.glob("*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                event = json.load(f)
            topic = TOPIC_FOR_KIND[SESSION_KIND[normalize_session(event.get("session_type"))]]
        except PermissionError:
            continue  # still locked by the writer; pick it up next time
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError) as e:
            quarantine(path, e)
            continue
        driver_code = event.get("driverCode", "UNKNOWN")
        in_flight.append((path, event, topic, producer.send(topic, key=driver_code, value=event)))

    producer.flush()
    for path, event, topic, future in in_flight:
        try:
            future.get(timeout=10)
        except Exception as e:
            print(f"Kafka did not accept {path.name} ({e}); will retry")
            continue
        path.unlink(missing_ok=True)
        print(f"Sent {event.get('session_type')} event for {event.get('driverCode')} to topic '{topic}'")
    return len(in_flight)


def main():
    parser = argparse.ArgumentParser(description="Ship queued live events to Kafka")
    parser.add_argument("--exit-when-idle", type=float, metavar="SECONDS",
                        help="stop after the queue has been empty this long (default: run forever)")
    args = parser.parse_args()

    lock = acquire_single_instance_lock()
    if lock is None:
        print("Another producer3 is already draining the queue; exiting.")
        return

    ensure_topics()
    producer = make_producer()
    print(f"Starting Live Event Producer... Watching for event files in '{LIVE_QUEUE_DIR}'. Press Ctrl+C to stop.")
    last_activity = time.monotonic()
    try:
        while True:
            try:
                if drain_queue(producer):
                    last_activity = time.monotonic()
                elif args.exit_when_idle and time.monotonic() - last_activity > args.exit_when_idle:
                    print(f"Queue idle for {args.exit_when_idle:g}s; exiting.")
                    break
            except OSError as e:
                print(f"An unexpected error occurred: {e}")
                time.sleep(5)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nShutting down producer")
    finally:
        producer.close()
        lock.close()


if __name__ == "__main__":
    main()
