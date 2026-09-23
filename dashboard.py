"""Launch the Grid-Pulse dashboard.

    python dashboard.py                  # Kafka if a broker is reachable, else demo mode
    python dashboard.py --mode demo      # no Kafka needed; the market is built in-process
    python dashboard.py --data simulated # trade the simulated season instead of the real one
    python dashboard.py --public         # hosting it for strangers (see README)
"""
import argparse
import os
import socket
import webbrowser

import uvicorn

from gridpulse.config import DATA_SOURCE, DATA_SOURCES, KAFKA_BROKER
from gridpulse.history import check_source
from gridpulse.server import DEFAULT_DB, create_app


def broker_reachable(broker=KAFKA_BROKER, timeout=1.5):
    host, _, port = broker.partition(":")
    try:
        with socket.create_connection((host, int(port or 9092)), timeout=timeout):
            return True
    except OSError:
        return False


def env_flag(name):
    return os.environ.get(name, "").lower() in ("1", "true", "yes")


def main():
    parser = argparse.ArgumentParser(description="Grid-Pulse dashboard")
    parser.add_argument("--mode", choices=["auto", "kafka", "demo"], default=os.environ.get("GRIDPULSE_MODE", "auto"))
    parser.add_argument("--data", choices=DATA_SOURCES, default=DATA_SOURCE,
                        help=f"real 2025 results or the simulated season (default: {DATA_SOURCE})")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    parser.add_argument("--db", default=os.environ.get("GRIDPULSE_DB", str(DEFAULT_DB)),
                        help="SQLite file for the game and the demo market's live weekends")
    parser.add_argument("--public", action="store_true", default=env_flag("GRIDPULSE_PUBLIC"),
                        help="hosting for strangers: no instant replays, trading window between weekends")
    parser.add_argument("--open", action="store_true", help="open the dashboard in a browser")
    args = parser.parse_args()

    try:
        check_source(args.data)
    except (FileNotFoundError, ValueError) as e:
        raise SystemExit(str(e))

    mode = args.mode
    if mode == "auto":
        mode = "kafka" if broker_reachable() else "demo"
        if mode == "demo":
            print(f"No Kafka broker at {KAFKA_BROKER}; starting in demo mode (market built in-process).")
    admin_token = os.environ.get("GRIDPULSE_ADMIN_TOKEN")
    if args.public and not admin_token:
        print("Public mode without GRIDPULSE_ADMIN_TOKEN: nobody can stop a weekend or reset mid-season.")

    url = f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port}"
    print(f"Grid-Pulse dashboard ({mode} mode, {args.data} data{', public' if args.public else ''}) -> {url}")
    if args.open:
        webbrowser.open(url)
    app = create_app(mode, data=args.data, public=args.public, db_path=args.db, admin_token=admin_token)
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", proxy_headers=True)


if __name__ == "__main__":
    main()
