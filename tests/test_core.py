import random

import pytest

from gridpulse import roster
from gridpulse.baseline import parse_money, read_baselines
from gridpulse.history import load_weekends, weekend_sessions
from gridpulse.market import MarketEngine, result_sort_key
from gridpulse.pricing import price_moves
from gridpulse.season import BY_ROUND, CALENDAR, HISTORICAL_ROUNDS, normalize_session, race_by_name, race_on_date
from gridpulse.simulation import WeekendSimulator, simulate_race


def baselines():
    b, problems = read_baselines()
    assert not problems
    return b


def historical_results():
    return sorted((r for w in load_weekends() for _, rs in weekend_sessions(w) for r in rs), key=result_sort_key)


# ---- baseline ---------------------------------------------------------------

@pytest.mark.parametrize("text, value", [("$78 M", 78e6), ("$0.375 M", 375e3), ("$27.5 M", 27.5e6),
                                         ("1,500,000", 1.5e6), ("$2B", 2e9), ("$750K", 750e3)])
def test_parse_money(text, value):
    assert parse_money(text) == pytest.approx(value)


def test_every_driver_has_a_baseline():
    # The CSV used to spell Ocon "Esteben", which silently dropped him from the market.
    assert set(baselines()) == set(roster.DRIVERS)
    assert baselines()["ALO"][1] == 27.5e6  # was truncated to 27M


def test_name_aliases():
    assert roster.code_for_name("Esteben Ocon") == "OCO"
    assert roster.code_for_name("Nobody") is None


# ---- season / roster ------------------------------------------------------

def test_calendar_is_complete_and_ordered():
    assert [r.round for r in CALENDAR] == list(range(1, 25))
    assert race_on_date("2025-08-02")[0].name == "Hungarian Grand Prix"
    assert race_on_date("2025-08-30") == (race_by_name("Dutch Grand Prix"), 1)
    assert race_on_date("2026-01-01") == (None, None)


@pytest.mark.parametrize("label, key", [("Practice 1", "practice1"), ("practice2", "practice2"), ("Sprint", "sprint_race"),
                                        ("Sprint Qualifying", "sprint_qualifying"), ("Race", "race")])
def test_normalize_session(label, key):
    assert normalize_session(label) == key


def test_mid_season_lineup_changes():
    r1 = {d["code"]: d["team"] for d in roster.drivers_for_round(1)}
    r7 = {d["code"]: d["team"] for d in roster.drivers_for_round(7)}
    assert r1["TSU"] == "RB" and r7["TSU"] == "Red Bull"
    assert "DOO" in r1 and "COL" not in r1
    assert "COL" in r7 and "DOO" not in r7
    assert len(r1) == len(r7) == 20


# ---- simulation -----------------------------------------------------------

@pytest.mark.parametrize("round_number", [15, 19])  # standard and sprint weekends
def test_weekend_simulation_invariants(round_number):
    race = BY_ROUND[round_number]
    weekend = WeekendSimulator(race, random.Random(1)).run_weekend()
    for key in ("qualifyingResults", "raceResults"):
        assert len(weekend[key]) == 20
    if race.sprint:
        # "Sprint" sessions used to generate nothing at all.
        assert len(weekend["sprintRaceResults"]) == 20
        assert max(r["points"] for r in weekend["sprintRaceResults"]) == 8
    race_results = weekend["raceResults"]
    finishers = [r for r in race_results if r["finishingPosition"]]
    assert [r["finishingPosition"] for r in finishers] == list(range(1, len(finishers) + 1))
    # No fastest-lap bonus point in 2025: the maximum is exactly 25.
    assert max(r["points"] for r in race_results) == 25
    assert sum(r["fastestLap"] for r in race_results) == 1
    # The race starts in qualifying order.
    quali_order = [r["driverCode"] for r in weekend["qualifyingResults"]]
    grid = sorted(race_results, key=lambda r: r["startingPosition"])
    assert [r["driverCode"] for r in grid] == quali_order


def test_incomplete_grid_still_races_everyone():
    drivers = roster.drivers_for_round(15)
    results, _ = simulate_race(["VER", "NOR"], drivers, 50, False, random.Random(3))
    assert len(results) == 20


# ---- pricing ----------------------------------------------------------------

def test_pricing_is_relative_to_expectation():
    win = dict(finishingPosition=1, points=25, status="Finished", overtakes=2)
    assert sum(p for _, p in price_moves(win, "race", expected=10)) > sum(p for _, p in price_moves(win, "race", expected=1))
    under = dict(finishingPosition=12, points=0, status="Finished")
    assert sum(p for _, p in price_moves(under, "race", expected=3)) < 0


def test_crash_costs_more_than_mechanical():
    crash = sum(p for _, p in price_moves(dict(status="Crashed", crashes=1), "race", 5))
    mech = sum(p for _, p in price_moves(dict(status="Mechanical Failure"), "race", 5))
    assert crash < mech < 0


def test_sprint_counts_less_than_race():
    r = dict(finishingPosition=1, points=8, status="Finished")
    assert sum(p for _, p in price_moves(r, "sprint_race", 5)) < sum(p for _, p in price_moves(r, "race", 5))


# ---- market engine ------------------------------------------------------------

def build_market():
    engine = MarketEngine()
    epoch = engine.start_epoch(baselines(), epoch=1)
    ticks = [t for t in (engine.apply(r) for r in historical_results()) if t]
    return engine, epoch, ticks


def test_every_historical_result_is_priced_once():
    engine, _, ticks = build_market()
    assert len(ticks) == len(historical_results())
    # Re-applying the same results (a producer run twice) changes nothing.
    values = {c: d["current_value"] for c, d in engine.drivers.items()}
    assert all(engine.apply(r) is None for r in historical_results())
    assert values == {c: d["current_value"] for c, d in engine.drivers.items()}


def test_market_moves_both_ways():
    engine, _, _ = build_market()
    changes = [d["current_value"] / d["baseline_value"] - 1 for d in engine.drivers.values()]
    assert min(changes) < -0.02 and max(changes) > 0.02


def test_replay_rebuilds_identical_state():
    engine, epoch, ticks = build_market()
    replica = MarketEngine()
    for record in [epoch, *ticks, *ticks]:  # duplicates on the log are ignored
        replica.replay(record)
    assert replica.applied == engine.applied
    for code, d in engine.drivers.items():
        assert replica.drivers[code]["current_value"] == d["current_value"]


def test_new_epoch_resets_and_stale_epoch_is_ignored():
    _, epoch, ticks = build_market()
    replica = MarketEngine()
    replica.replay(epoch)
    replica.replay(ticks[0])
    newer = {**epoch, "epoch": 2}
    assert replica.replay(newer) == "epoch"
    assert replica.ticks == [] and replica.applied == set()
    assert replica.replay(epoch) is None            # older epoch
    assert replica.replay(ticks[0]) is None          # tick from the older epoch


def test_ticks_are_chronological():
    _, _, ticks = build_market()
    rounds = [t["round"] for t in ticks]
    assert rounds == sorted(rounds)
    assert {t["round"] for t in ticks} == set(range(1, HISTORICAL_ROUNDS + 1))
