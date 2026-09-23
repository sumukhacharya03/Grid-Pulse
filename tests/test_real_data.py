"""The real 2025 season (fetched with FastF1) must match what actually happened."""
import time
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from gridpulse import roster
from gridpulse.config import REAL_DATA_DIR
from gridpulse.history import RealWeekend, historical_weekends, load_weekends, weekend_sessions
from gridpulse.market import MarketEngine, result_sort_key
from gridpulse.baseline import read_baselines
from gridpulse.season import BY_ROUND, CALENDAR
from gridpulse.server import create_app

pytestmark = pytest.mark.skipif(len(list(REAL_DATA_DIR.glob("*.json"))) < 24,
                                reason="real season not fetched (generator/real_data/fetch_real_results.py)")


def standings(weekends):
    points = Counter()
    for w in weekends:
        for key, results in weekend_sessions(w):
            if key in ("race", "sprint_race"):
                for r in results:
                    points[r["driverCode"]] += r["points"]
    return points


def test_every_round_and_session_is_present():
    weekends = load_weekends(REAL_DATA_DIR)
    assert [w["round"] for w in weekends] == list(range(1, 25))
    # Real absences: Stroll withdrew before the Spanish GP; Bortoleto has no
    # qualifying classification in Brazil.
    absent = {(9, "race"): {"STR"}, (21, "qualifying"): {"BOR"}}
    for race, weekend in zip(CALENDAR, weekends):
        sessions = dict(weekend_sessions(weekend))
        assert set(sessions) == {key for key, *_ in race.sessions}, race.name
        for key in ("qualifying", "race"):
            missing = {d["code"] for d in roster.drivers_for_round(race.round)} - {r["driverCode"] for r in sessions[key]}
            assert missing == absent.get((race.round, key), set()), (race.name, key, missing)


def test_final_2025_standings():
    top = standings(load_weekends(REAL_DATA_DIR)).most_common(4)
    assert top == [("NOR", 423), ("VER", 421), ("PIA", 410), ("RUS", 319)]


def test_history_stops_after_hungary():
    weekends = historical_weekends("real")
    assert weekends[-1]["raceName"] == "Hungarian Grand Prix"
    points = standings(weekends)
    assert points["PIA"] == 284 and points["NOR"] == 275


def test_known_results():
    china = RealWeekend(BY_ROUND[2])
    assert china.live_results("sprint_race")[0]["driverCode"] == "HAM"  # Hamilton's sprint win
    dsq = {r["driverCode"] for r in china.live_results("race") if r["status"] == "Disqualified"}
    assert dsq == {"HAM", "LEC", "GAS"}
    assert RealWeekend(BY_ROUND[15]).live_results("race")[0]["driverCode"] == "PIA"
    assert RealWeekend(BY_ROUND[24]).live_results("race")[0]["driverCode"] == "VER"


def test_real_retirements_are_priced_as_retirements():
    engine = MarketEngine()
    engine.start_epoch(read_baselines()[0], epoch=1)
    results = sorted((r for w in historical_weekends("real") for _, rs in weekend_sessions(w) for r in rs),
                     key=result_sort_key)
    ticks = [t for t in (engine.apply(r) for r in results) if t]
    labels = {m["label"].split(" on lap")[0] for t in ticks for m in t["moves"] if m["pct"] < -0.9}
    assert not any(label.startswith("Crashed") for label in labels)


def test_go_live_replays_the_real_weekend(tmp_path):
    with TestClient(create_app("demo", data="real", db_path=tmp_path / "real.db")) as c:
        assert c.get("/api/market").json()["next_race"] == "Dutch Grand Prix"
        c.post("/api/simulate", json={"speed": "instant"})
        deadline = time.time() + 30
        while c.get("/api/market").json()["sim"].get("running") and time.time() < deadline:
            time.sleep(0.1)
        ticks = c.get("/api/market").json()["ticks"]
        race = sorted((t for t in ticks if t["round"] == 15 and t["session"] == "race" and t["position"]),
                      key=lambda t: t["position"])
        assert [t["driver_code"] for t in race[:3]] == ["PIA", "VER", "HAD"]
