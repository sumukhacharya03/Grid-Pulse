"""Race weekend simulator shared by the historical and real-time generators.

Output formats are unchanged from the original generators, so the
producers and the pricing model read historical and live data identically."""
import random

from . import roster
from .season import SESSION_KIND, SESSION_NAME

SESSION_RESULT_KEY = {
    "practice1": "practice1Results",
    "practice2": "practice2Results",
    "practice3": "practice3Results",
    "sprint_qualifying": "sprintQualifyingResults",
    "sprint_race": "sprintRaceResults",
    "qualifying": "qualifyingResults",
    "race": "raceResults",
}
SESSION_EVENTS_KEY = {"sprint_race": "sprintRaceEvents", "race": "raceEvents"}
# Which timed session sets the grid for each race.
GRID_SOURCE = {"sprint_race": "sprint_qualifying", "race": "qualifying"}

RACE_POINTS = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
SPRINT_POINTS = [8, 7, 6, 5, 4, 3, 2, 1]


def format_lap(seconds):
    return f"{int(seconds // 60)}:{seconds % 60:06.3f}"


def simulate_timed_session(drivers, base_lap, session_key, rng):
    """Practice / qualifying classification with plausible lap times.

    A driver's pace is their tier plus noise, so a midfielder can occasionally
    out-qualify a front-runner (the old version sorted strictly by tier)."""
    practice = SESSION_KIND[session_key] == "practice"
    noise = 0.7 if practice else 0.45
    pace = {d["code"]: d["tier"] + rng.gauss(0, noise) for d in drivers}
    order = sorted(drivers, key=lambda d: pace[d["code"]])

    lap = base_lap
    if practice:
        lap += rng.uniform(1.0, 2.0)
    elif session_key == "sprint_qualifying":
        lap += 0.250

    time_key = "fastest_time" if practice else "time"
    results = []
    for i, d in enumerate(order):
        if i:
            gap = pace[d["code"]] - pace[order[i - 1]["code"]]
            lap += rng.uniform(0.020, 0.250) + gap * 0.30
        result = {"position": i + 1, "driverCode": d["code"], "team": d["team"], time_key: format_lap(lap)}
        if practice:
            result["fastestLap"] = i == 0
        results.append(result)
    return results


def simulate_race(grid, drivers, laps, is_sprint, rng):
    """Race story: DNFs, on-track battles, points, pit stops, fastest lap."""
    driver_map = {d["code"]: d for d in drivers}
    grid = [code for code in grid if code in driver_map]
    # Anyone without a grid slot (e.g. qualifying was cut short) starts at the back.
    grid += [d["code"] for d in drivers if d["code"] not in grid]
    race_data = {
        code: {
            "driverCode": code, "team": driver_map[code]["team"],
            "startingPosition": i + 1, "finishingPosition": None,
            "overtakes": 0, "positionsLost": 0, "overtakesWithDRS": 0, "overtakesWithoutDRS": 0,
            "crashes": 0, "collisions": 0, "pitstops": [], "status": "Finished",
            "fastestLap": False, "points": 0,
        }
        for i, code in enumerate(grid)
    }

    running = list(grid)
    for _ in range(rng.randint(0, 2) if is_sprint else rng.randint(1, 4)):
        if len(running) < 3:
            break
        dnf_type = rng.choice(["Collision", "Crash", "Mechanical"])
        dnf_lap = rng.randint(1, max(1, laps - 5))
        if dnf_type == "Collision":
            idx = rng.randint(0, len(running) - 2)
            a, b = running[idx], running[idx + 1]
            for me, other in ((a, b), (b, a)):
                race_data[me].update(status=f"Collision with {other}", collisions=1, dnf_lap=dnf_lap)
                running.remove(me)
        else:
            code = rng.choice(running)
            race_data[code].update(
                status="Crashed" if dnf_type == "Crash" else "Mechanical Failure",
                crashes=1 if dnf_type == "Crash" else 0,
                dnf_lap=dnf_lap,
            )
            running.remove(code)

    for _ in range(25 if is_sprint else 70):
        if len(running) < 2:
            break
        attacker = rng.randint(1, len(running) - 1)
        a_tier = driver_map[running[attacker]]["tier"]
        d_tier = driver_map[running[attacker - 1]]["tier"]
        chance = 0.60 if a_tier < d_tier else (0.30 if a_tier == d_tier else 0.05)
        if rng.random() < chance:
            running[attacker], running[attacker - 1] = running[attacker - 1], running[attacker]

    points_table = SPRINT_POINTS if is_sprint else RACE_POINTS
    for i, code in enumerate(running):
        rd = race_data[code]
        rd["finishingPosition"] = i + 1
        rd["points"] = points_table[i] if i < len(points_table) else 0
        change = rd["startingPosition"] - rd["finishingPosition"]
        if change > 0:
            drs = round(change * rng.uniform(0.6, 0.8))
            rd.update(overtakes=change, overtakesWithDRS=drs, overtakesWithoutDRS=change - drs)
        else:
            rd["positionsLost"] = -change

    safety_cars = 0 if is_sprint else rng.randint(0, 2)
    if not is_sprint:
        for code in running:
            if rng.random() < 0.8 + safety_cars * 0.1:
                race_data[code]["pitstops"] = [round(rng.uniform(2.1, 4.5), 2) for _ in range(rng.randint(1, 2))]
    if running:
        # The fastest-lap bonus point was scrapped for 2025, but it still
        # counts as a (small) market-moving achievement.
        race_data[rng.choice(running[:10])]["fastestLap"] = True

    finishers = sorted((r for r in race_data.values() if r["finishingPosition"]),
                       key=lambda r: r["finishingPosition"])
    retirements = [r for r in race_data.values() if not r["finishingPosition"]]
    events = {"yellow_flags": rng.randint(2, 6), "safety_cars": safety_cars,
              "red_flags": 1 if rng.random() < 0.1 else 0}
    return finishers + retirements, events


class WeekendSimulator:
    """Runs one weekend a session at a time, carrying qualifying grids forward
    so the race starts in the order qualifying actually produced."""

    def __init__(self, race, rng=None, grids=None):
        self.race = race
        self.rng = rng or random.Random()
        self.drivers = roster.drivers_for_round(race.round)
        self.grids = dict(grids or {})

    def run(self, session_key):
        kind = SESSION_KIND[session_key]
        if kind in ("practice", "qualifying", "sprint_qualifying"):
            results = simulate_timed_session(self.drivers, self.race.base_lap, session_key, self.rng)
            if kind != "practice":
                self.grids[session_key] = [r["driverCode"] for r in results]
            return results, None

        grid_key = GRID_SOURCE[session_key]
        if grid_key not in self.grids:
            # e.g. the race-day cron job ran without the Saturday state file.
            print(f"No {grid_key} grid for {self.race.name}; simulating one to set the grid.")
            self.run(grid_key)
        return simulate_race(self.grids[grid_key], self.drivers, self.race.laps,
                             is_sprint=kind == "sprint", rng=self.rng)

    def live_results(self, session_key):
        """One session's results tagged the way the real-time pipeline expects."""
        results, _ = self.run(session_key)
        return [{**r, "raceName": self.race.name, "round": self.race.round, "season": 2025,
                 "session_type": session_key, "session_name": SESSION_NAME[session_key]}
                for r in results]

    def run_weekend(self):
        weekend = {"season": 2025, "round": self.race.round, "raceName": self.race.name}
        for key, *_ in self.race.sessions:
            results, events = self.run(key)
            weekend[SESSION_RESULT_KEY[key]] = results
            if events is not None:
                weekend[SESSION_EVENTS_KEY[key]] = events
        return weekend
