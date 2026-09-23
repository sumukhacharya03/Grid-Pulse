"""Download the real 2025 season with FastF1 and save it in the same format
as the simulated weekends, so the rest of the pipeline reads it unchanged.

    python generator/real_data/fetch_real_results.py            # all 24 rounds
    python generator/real_data/fetch_real_results.py --rounds 15 16 --force

Qualifying, sprints and races come from the official timing results;
practice has no official classification, so it is ranked by each driver's
fastest lap. Downloads are cached in .fastf1-cache/ so re-runs are quick.
Note: the timing data only says "Retired", not why, so real retirements
are priced as plain retirements (never as crashes).
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # repo root, for `gridpulse`

import fastf1
from fastf1.ergast import Ergast

from gridpulse import roster
from gridpulse.config import REAL_DATA_DIR, ROOT
from gridpulse.season import CALENDAR, SEASON, SESSION_KIND
from gridpulse.simulation import SESSION_RESULT_KEY

FASTF1_SESSION = {"practice1": "FP1", "practice2": "FP2", "practice3": "FP3",
                  "sprint_qualifying": "SQ", "qualifying": "Q", "sprint_race": "S", "race": "R"}
FINISHED = {"Finished", "Lapped"}


def fmt_lap(td):
    if td is None or (isinstance(td, float) and math.isnan(td)) or str(td) == "NaT":
        return None
    seconds = td.total_seconds()
    return f"{int(seconds // 60)}:{seconds % 60:06.3f}"


def team_for(code, round_number, fallback):
    return roster.team_for_round(code, round_number) if code in roster.DRIVERS else fallback


def num(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def load(round_number, session_key, laps=False):
    session = fastf1.get_session(SEASON, round_number, FASTF1_SESSION[session_key])
    session.load(laps=laps, telemetry=False, weather=False, messages=False)
    return session


def practice_results(round_number, session_key):
    laps = load(round_number, session_key, laps=True).laps
    if "Deleted" in laps.columns:
        laps = laps[laps["Deleted"] != True]  # noqa: E712 - pandas column compare
    laps = laps.dropna(subset=["LapTime"])
    best = laps.loc[laps.groupby("Driver")["LapTime"].idxmin()].sort_values("LapTime")
    return [
        {"position": i + 1, "driverCode": row.Driver, "team": team_for(row.Driver, round_number, row.Team),
         "fastest_time": fmt_lap(row.LapTime), "fastestLap": i == 0}
        for i, row in enumerate(best.itertuples())
    ]


def qualifying_results(round_number, session_key):
    results = load(round_number, session_key).results.sort_values("Position")
    out = []
    for row in results.itertuples():
        pos = num(row.Position)
        if pos is None:
            continue
        best = next((t for t in (row.Q3, row.Q2, row.Q1) if fmt_lap(t)), None)
        out.append({"position": int(pos), "driverCode": row.Abbreviation,
                    "team": team_for(row.Abbreviation, round_number, row.TeamName), "time": fmt_lap(best)})
    return out or grid_order(round_number, session_key)


def grid_order(round_number, session_key):
    """Fallback when the timing feed has no classification (2025 sprint
    qualifying): the race that session sets the grid for starts in its order."""
    race_key = "sprint_race" if session_key == "sprint_qualifying" else "race"
    results = load(round_number, race_key).results
    rows = [r for r in results.itertuples() if (num(r.GridPosition) or 0) > 0]
    rows.sort(key=lambda r: num(r.GridPosition))
    return [{"position": i + 1, "driverCode": r.Abbreviation,
             "team": team_for(r.Abbreviation, round_number, r.TeamName), "time": None}
            for i, r in enumerate(rows)]


def fastest_lap_driver(round_number):
    try:
        race = Ergast(result_type="pandas", auto_cast=True).get_race_results(SEASON, round_number).content[0]
        return race.loc[race["fastestLapRank"] == 1, "driverCode"].iloc[0]
    except Exception as e:  # Ergast is a nice-to-have here
        print(f"    (no fastest-lap data: {e})")
        return None


def race_results(round_number, session_key):
    results = load(round_number, session_key).results
    field = len(results)
    fastest = fastest_lap_driver(round_number) if session_key == "race" else None
    out = []
    for row in results.itertuples():
        code = row.Abbreviation
        grid = int(num(row.GridPosition) or 0) or field  # 0 = pit-lane start
        classified = str(row.ClassifiedPosition)
        finish = int(classified) if classified.isdigit() else None
        status = "Finished" if row.Status in FINISHED or str(row.Status).startswith("+") else str(row.Status)
        record = {
            "driverCode": code, "team": team_for(code, round_number, row.TeamName),
            "startingPosition": grid, "finishingPosition": finish,
            "overtakes": max(0, grid - finish) if finish else 0,
            "positionsLost": max(0, finish - grid) if finish else 0,
            "crashes": 0, "collisions": 0, "status": status,
            "fastestLap": code == fastest, "points": int(num(row.Points) or 0),
        }
        if finish is None and status not in ("Disqualified", "Did not start"):
            laps = num(row.Laps)
            record["dnf_lap"] = int(laps) + 1 if laps is not None else None
        out.append(record)
    out.sort(key=lambda r: (r["finishingPosition"] is None, r["finishingPosition"] or 0))
    return out


def fetch_weekend(race):
    weekend = {"season": SEASON, "round": race.round, "raceName": race.name, "source": "fastf1"}
    for session_key, name, kind, _, _ in race.sessions:
        print(f"  {name}...")
        if kind == "practice":
            results = practice_results(race.round, session_key)
        elif kind in ("qualifying", "sprint_qualifying"):
            results = qualifying_results(race.round, session_key)
        else:
            results = race_results(race.round, session_key)
        if not results:
            raise RuntimeError(f"no results for {race.name} {name}")
        unknown = sorted({r["driverCode"] for r in results} - set(roster.DRIVERS))
        if unknown and SESSION_KIND[session_key] != "practice":
            print(f"    note: not on the Grid-Pulse roster, will not be traded: {', '.join(unknown)}")
        weekend[SESSION_RESULT_KEY[session_key]] = results
    return weekend


def main():
    parser = argparse.ArgumentParser(description="Fetch the real 2025 season with FastF1")
    parser.add_argument("--rounds", type=int, nargs="*", help="only these rounds (default: all)")
    parser.add_argument("--force", action="store_true", help="re-download rounds that are already saved")
    args = parser.parse_args()

    fastf1.set_log_level("ERROR")
    cache = ROOT / ".fastf1-cache"
    cache.mkdir(exist_ok=True)
    fastf1.Cache.enable_cache(str(cache))
    REAL_DATA_DIR.mkdir(parents=True, exist_ok=True)

    failed = []
    for race in CALENDAR:
        if args.rounds and race.round not in args.rounds:
            continue
        path = REAL_DATA_DIR / f"{race.name.lower().replace(' ', '_')}.json"
        if path.exists() and not args.force:
            print(f"Round {race.round}: {race.name} already saved")
            continue
        print(f"Round {race.round}: {race.name}")
        try:
            weekend = fetch_weekend(race)
        except Exception as e:
            print(f"  FAILED: {e}")
            failed.append(race.name)
            continue
        with open(path, "w", encoding="utf-8") as f:
            json.dump(weekend, f, indent=2)
        print(f"  saved {path.relative_to(ROOT)}")

    if failed:
        sys.exit(f"\nCould not fetch: {', '.join(failed)}. Re-run to retry (downloads are cached).")
    print("\nReal season data is up to date.")


if __name__ == "__main__":
    main()
