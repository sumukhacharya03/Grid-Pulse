"""Loading race weekends from either data source (real or simulated)."""
import json
import random

from .config import DATA_SOURCES, HISTORICAL_DIR, REAL_DATA_DIR
from .season import HISTORICAL_ROUNDS, SESSION_NAME, SESSION_ORDER
from .simulation import SESSION_RESULT_KEY, WeekendSimulator

SOURCE_DIRS = {"real": REAL_DATA_DIR, "simulated": HISTORICAL_DIR}


def check_source(source):
    if source not in DATA_SOURCES:
        raise ValueError(f"Unknown data source '{source}' (use one of: {', '.join(DATA_SOURCES)})")
    if not any(SOURCE_DIRS[source].glob("*.json")):
        hint = ("python generator/real_data/fetch_real_results.py" if source == "real"
                else "python generator/historical/generator_historical.py")
        raise FileNotFoundError(f"No {source} race data in {SOURCE_DIRS[source]}. Create it with: {hint}")
    return source


def weekend_filename(race_name):
    return f"{race_name.lower().replace(' ', '_')}.json"


def load_weekends(directory=HISTORICAL_DIR, max_round=None):
    """Weekend files in round order (sorting by filename put Australia before
    Austria before Bahrain...)."""
    weekends = []
    for path in directory.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            weekend = json.load(f)
        if max_round is None or weekend["round"] <= max_round:
            weekends.append(weekend)
    return sorted(weekends, key=lambda w: w["round"])


def historical_weekends(source):
    """The part of the season that is already priced in: rounds 1-14."""
    return load_weekends(SOURCE_DIRS[check_source(source)], max_round=HISTORICAL_ROUNDS)


def weekend_sessions(weekend):
    """Yield (session_key, results) in running order, each result tagged with
    the race, round and session it belongs to."""
    for session_key in sorted(SESSION_RESULT_KEY, key=SESSION_ORDER.get):
        results = weekend.get(SESSION_RESULT_KEY[session_key])
        if not results:
            continue
        yield session_key, [
            {**r, "raceName": weekend["raceName"], "season": weekend.get("season", 2025),
             "round": weekend["round"], "session_type": session_key}
            for r in results
        ]


class RealWeekend:
    """Replays a real weekend session by session, with the same interface as
    WeekendSimulator so the live pipeline can't tell them apart."""

    def __init__(self, race):
        path = REAL_DATA_DIR / weekend_filename(race.name)
        if not path.exists():
            raise FileNotFoundError(f"No real results saved for {race.name}. "
                                    f"Run: python generator/real_data/fetch_real_results.py --rounds {race.round}")
        with open(path, encoding="utf-8") as f:
            self.sessions = dict(weekend_sessions(json.load(f)))
        self.race = race
        self.grids = {}

    def live_results(self, session_key):
        return [{**r, "session_name": SESSION_NAME[session_key]} for r in self.sessions.get(session_key, [])]


def live_weekend(race, source, rng=None, grids=None):
    """What 'Go live' runs for `race`: the real weekend or a fresh simulation."""
    if source == "real":
        return RealWeekend(race)
    return WeekendSimulator(race, rng or random.Random(), grids=grids)
