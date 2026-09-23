"""Build (and optionally publish) the browser-only edition for GitHub Pages.

    python scripts/publish_pages.py            # build into web/dist-static
    python scripts/publish_pages.py --push     # ...and publish it to the gh-pages branch

The real 2025 season never changes, so the Python engine prices all of it
up front: the history (rounds 1-14) plus every tick of the ten "live"
weekends, in order. The page then replays those ticks in the browser with
the same timing and messages the dashboard server sends, and the trading
game is kept in the visitor's browser. No server needed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gridpulse import roster
from gridpulse.baseline import read_baselines
from gridpulse.config import ASSETS_DIR
from gridpulse.game import STARTING_CASH
from gridpulse.history import RealWeekend, historical_weekends, weekend_sessions
from gridpulse.market import MarketEngine, result_sort_key
from gridpulse.season import CALENDAR, HISTORICAL_ROUNDS
from gridpulse.server import public_tick

WEB = ROOT / "web"
OUT = WEB / "dist-static"
REPO_BASE = "/Grid-Pulse/"  # https://<user>.github.io/Grid-Pulse/


def market_data():
    baselines, problems = read_baselines()
    if problems:
        sys.exit("Baseline CSV problems: " + "; ".join(problems))
    engine = MarketEngine()
    engine.start_epoch(baselines, epoch=1)
    history = [r for w in historical_weekends("real") for _, rs in weekend_sessions(w) for r in rs]
    for r in sorted(history, key=result_sort_key):
        engine.apply(r)

    snapshot = {
        "mode": "static", "data": "real", "public": False, "ready": True, "epoch": 1,
        "roster": roster.roster_payload(),
        "calendar": [race.payload() for race in CALENDAR],
        "values": {c: engine.state_message(c) for c in engine.drivers},
        "ticks": [public_tick(t) for t in engine.ticks],
        "sim": {"running": False},
        "next_race": next(r.name for r in CALENDAR if r.round > HISTORICAL_ROUNDS),
        "game": {"starting_cash": STARTING_CASH},
    }

    live = []
    for race in CALENDAR:
        if race.round <= HISTORICAL_ROUNDS:
            continue
        weekend = RealWeekend(race)
        sessions = []
        for key, *_ in race.sessions:
            results = weekend.live_results(key)
            ticks = [public_tick(t) for t in (engine.apply(r, live=True) for r in results) if t]
            sessions.append({"session": key, "field": len(ticks), "ticks": ticks})
        live.append({"race": race.name, "round": race.round, "sessions": sessions})
    return {"snapshot": snapshot, "live": live}


def build():
    print("Pricing the 2025 season...")
    data = market_data()
    n_live = sum(len(s["ticks"]) for r in data["live"] for s in r["sessions"])
    print(f"  {len(data['snapshot']['ticks'])} historical and {n_live} live price moves")

    print("Building the web app...")
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    env = {**os.environ, "VITE_STATIC": "1"}
    subprocess.run([npm, "run", "build", "--", "--outDir", "dist-static", "--base", REPO_BASE],
                   cwd=WEB, env=env, check=True)

    with open(OUT / "market.json", "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"))
    shutil.copytree(ASSETS_DIR, OUT / "drivers", dirs_exist_ok=True)
    (OUT / ".nojekyll").write_text("")  # serve files as-is
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"Built {OUT.relative_to(ROOT)} ({size / 1e6:.1f} MB)")


def push():
    remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT, check=True,
                            capture_output=True, text=True).stdout.strip()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, check=True,
                            capture_output=True, text=True).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        site = Path(tmp) / "site"
        shutil.copytree(OUT, site)
        git = lambda *a: subprocess.run(["git", *a], cwd=site, check=True)  # noqa: E731
        git("init", "-q", "-b", "gh-pages")
        git("add", "-A")
        git("commit", "-q", "-m", f"Publish Grid-Pulse ({commit})")
        # gh-pages only ever holds the latest build, so it is replaced wholesale.
        git("push", "-f", remote, "gh-pages")
    print("Published to the gh-pages branch.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the GitHub Pages edition of Grid-Pulse")
    parser.add_argument("--push", action="store_true", help="publish to the gh-pages branch")
    args = parser.parse_args()
    build()
    if args.push:
        push()
