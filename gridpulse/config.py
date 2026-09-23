"""Central configuration. Every path is anchored to the repo root so scripts
behave the same no matter which directory they are launched from (cron,
Task Scheduler, the dashboard, or a terminal)."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KAFKA_BROKER = os.environ.get("GRIDPULSE_KAFKA_BROKER", "localhost:9092")

TOPIC_BASELINE = "drivers-baseline-value"
TOPIC_HIST_PRACTICE = "historical-performance-practice"
TOPIC_HIST_QUALIFYING = "historical-performance-qualifying"
TOPIC_HIST_RACE = "historical-performance-race"
TOPIC_LIVE_PRACTICE = "realtime-performance-practice"
TOPIC_LIVE_QUALIFYING = "realtime-performance-qualifying"
TOPIC_LIVE_RACE = "realtime-performance-race"
# Latest value per driver (keyed by driver code).
TOPIC_STOCK_VALUES = "driver-stock-values"
# Every individual price move, with the reasons behind it. Powers the charts
# and the live feed on the dashboard.
TOPIC_MARKET_TICKS = "market-ticks"

HISTORICAL_TOPICS = [TOPIC_HIST_PRACTICE, TOPIC_HIST_QUALIFYING, TOPIC_HIST_RACE]
REALTIME_TOPICS = [TOPIC_LIVE_PRACTICE, TOPIC_LIVE_QUALIFYING, TOPIC_LIVE_RACE]
ALL_TOPICS = [TOPIC_BASELINE, *HISTORICAL_TOPICS, *REALTIME_TOPICS,
              TOPIC_STOCK_VALUES, TOPIC_MARKET_TICKS]

BASELINE_CSV = ROOT / "baseline_market_value" / "drivers_baseline_value.csv"
HISTORICAL_DIR = ROOT / "generator" / "historical" / "generated_historical_results"
REAL_DATA_DIR = ROOT / "generator" / "real_data" / "results_2025"

# Which season the market trades on:
#   real      - the actual 2025 results (fetched with FastF1); "Go live" replays them
#   simulated - the generated season; "Go live" simulates new weekends
DATA_SOURCES = ("real", "simulated")
DATA_SOURCE = os.environ.get("GRIDPULSE_DATA", "real")
LIVE_QUEUE_DIR = ROOT / "generator" / "real_time" / "live_events_queue"
LIVE_WEEKEND_STATE_DIR = ROOT / "generator" / "real_time" / "weekend_state"
ASSETS_DIR = ROOT / "assets"
WEB_DIST_DIR = ROOT / "web" / "dist"
