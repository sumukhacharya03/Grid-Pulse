"""The Grid-Pulse pricing model.

The market "prices in" an expectation: a driver whose stock is the Nth most
valuable on the grid is expected to finish Nth. Beating that expectation
lifts the price, falling short drops it, and headline moments (poles, wins,
podiums, crashes) add shocks on top. Each move is returned with a label so
the dashboard can explain every tick.
"""
from .season import SESSION_KIND, SESSION_NAME

# Per place above/below expectation, and the cap on that component.
PRACTICE_PER_PLACE, PRACTICE_CAP = 0.0004, 0.004
QUALI_PER_PLACE, QUALI_CAP = 0.0012, 0.012
RACE_PER_PLACE, RACE_CAP = 0.0025, 0.030

PRACTICE_TOP_BONUS = 0.001
POLE_BONUS = 0.006
QUALI_TOP3_BONUS = 0.002
POINTS_RATE = 0.0006
WIN_BONUS = 0.010
PODIUM_BONUS = 0.004
OVERTAKE_RATE = 0.0004
FASTEST_LAP_BONUS = 0.002
CRASH_PENALTY = -0.025
COLLISION_PENALTY = -0.015
MECHANICAL_PENALTY = -0.010

# Sprint sessions count for less than their Sunday equivalents.
KIND_WEIGHT = {"practice": 1.0, "sprint_qualifying": 0.5, "qualifying": 1.0, "sprint": 0.4, "race": 1.0}


def _clamp(x, cap):
    return max(-cap, min(cap, x))


def _position(result):
    return result.get("position") or result.get("finishingPosition")


def price_moves(result, session_key, expected):
    """Return [(label, pct)] for one driver's result in one session."""
    kind = SESSION_KIND[session_key]
    session = SESSION_NAME[session_key]
    weight = KIND_WEIGHT[kind]
    pos = _position(result)
    moves = []

    if kind == "practice":
        if pos:
            moves.append((f"P{pos} in {session} (exp. P{expected})",
                          _clamp((expected - pos) * PRACTICE_PER_PLACE, PRACTICE_CAP)))
            if pos == 1:
                moves.append((f"Fastest in {session}", PRACTICE_TOP_BONUS))

    elif kind in ("qualifying", "sprint_qualifying"):
        if pos:
            moves.append((f"Qualified P{pos} (exp. P{expected})",
                          _clamp((expected - pos) * QUALI_PER_PLACE, QUALI_CAP)))
            if pos == 1:
                moves.append(("Pole position" if kind == "qualifying" else "Sprint pole", POLE_BONUS))
            elif pos <= 3:
                moves.append(("Top-3 grid slot", QUALI_TOP3_BONUS))

    else:  # race / sprint
        status = result.get("status", "Finished")
        label = "Sprint" if kind == "sprint" else "Race"
        if pos:
            moves.append((f"{label} P{pos} (exp. P{expected})",
                          _clamp((expected - pos) * RACE_PER_PLACE, RACE_CAP)))
            points = result.get("points", 0) or 0
            if points:
                moves.append((f"+{points} championship points", points * POINTS_RATE))
            if pos == 1:
                moves.append(("Sprint win" if kind == "sprint" else "Victory", WIN_BONUS))
            elif pos <= 3:
                moves.append(("Podium", PODIUM_BONUS))
            overtakes = result.get("overtakes", 0) or 0
            if overtakes:
                moves.append((f"Gained {overtakes} place{'s' if overtakes != 1 else ''}", overtakes * OVERTAKE_RATE))
            if result.get("fastestLap") and kind == "race":
                moves.append(("Fastest lap", FASTEST_LAP_BONUS))
        else:
            lap = result.get("dnf_lap")
            on_lap = f" on lap {lap}" if lap else ""
            if result.get("crashes"):
                moves.append((f"Crashed out{on_lap}", CRASH_PENALTY))
            elif result.get("collisions"):
                moves.append((f"{status}{on_lap}", COLLISION_PENALTY))
            else:
                moves.append((f"{status if status != 'Finished' else 'Retired'}{on_lap}", MECHANICAL_PENALTY))

    return [(label, round(pct * weight, 6)) for label, pct in moves if pct]
