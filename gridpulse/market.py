"""Event-sourced market state.

Every price change is a *tick* on the `market-ticks` topic, and each market
build starts with an *epoch* record carrying the baseline values. Replaying
the topic therefore rebuilds the exact market (values, history, which
results were already applied), which is how the real-time service and the
dashboard recover after a restart. Re-running the batch job starts a new
epoch, and consumers drop anything from older epochs.
"""
import time

from . import roster
from .pricing import price_moves
from .season import BY_NAME, BY_ROUND, SESSION_KIND, SESSION_NAME, SESSION_ORDER, normalize_session


def tick_id(round_number, session_key, driver_code):
    return f"{round_number}:{session_key}:{driver_code}"


def result_sort_key(result):
    """Chronological order for results: round, then session, then position."""
    session_key = normalize_session(result.get("session_type"))
    pos = result.get("position") or result.get("finishingPosition") or 99
    return (result.get("round", 0), SESSION_ORDER[session_key], pos)


class MarketEngine:
    def __init__(self):
        self.epoch = None
        self.drivers = {}
        self.ticks = []
        self.applied = set()

    # ---- building ------------------------------------------------------
    def start_epoch(self, baselines, epoch=None):
        """baselines: {code: (name, value)}. Returns the epoch record to publish."""
        self.epoch = epoch or int(time.time() * 1000)
        self.drivers = {}
        self.ticks = []
        self.applied = set()
        for code, (name, value) in baselines.items():
            self.drivers[code] = {
                "driver_code": code, "driver_name": name, "team": roster.current_team(code),
                "baseline_value": float(value), "current_value": float(value),
            }
        return {"type": "epoch", "epoch": self.epoch,
                "baselines": {c: {"name": n, "value": v} for c, (n, v) in baselines.items()}}

    def expected_position(self, code, round_number):
        """Where the market expects `code` to finish: its value rank among the
        drivers on the grid that round."""
        field = [c for c in self.drivers if c in roster.DRIVERS and roster.is_active(c, round_number)]
        field.sort(key=lambda c: self.drivers[c]["current_value"], reverse=True)
        return field.index(code) + 1 if code in field else len(field)

    def apply(self, result, live=False):
        """Price one driver's session result. Returns the tick, or None when
        the result is for an unknown driver or has already been applied."""
        code = result.get("driverCode")
        if code not in self.drivers:
            return None
        session_key = normalize_session(result.get("session_type"))
        race = BY_NAME.get(result.get("raceName")) or BY_ROUND.get(result.get("round"))
        if race is None:
            return None
        tid = tick_id(race.round, session_key, code)
        if tid in self.applied:
            return None

        expected = self.expected_position(code, race.round)
        moves = price_moves(result, session_key, expected)
        change = sum(pct for _, pct in moves)
        driver = self.drivers[code]
        before = driver["current_value"]
        # Rounded exactly as the tick records it, so a market rebuilt by
        # replaying the log is identical to the one that wrote it.
        after = round(before * (1 + change), 2)
        driver["current_value"] = after
        pos = result.get("position") or result.get("finishingPosition")

        tick = {
            "type": "tick", "epoch": self.epoch, "id": tid, "driver_code": code,
            "race": race.name, "round": race.round,
            "session": session_key, "session_name": SESSION_NAME[session_key],
            "kind": SESSION_KIND[session_key],
            "position": pos, "expected": expected, "grid": result.get("startingPosition"),
            "status": result.get("status"), "points": result.get("points", 0) or 0,
            "fastest_lap": bool(result.get("fastestLap")) and SESSION_KIND[session_key] == "race",
            "value_before": round(before, 2), "value_after": after,
            "change_pct": round(change * 100, 4),
            "moves": [{"label": label, "pct": round(pct * 100, 4)} for label, pct in moves],
            # Simulated session time (keeps charts on the real season timeline)
            # offset by classification so every tick is distinct.
            "ts": race.session_timestamp(session_key) + (pos or 20 + (result.get("startingPosition") or 0)) * 7,
            "live": live,
            "received_at": time.time(),
        }
        self._record(tick)
        return tick

    # ---- replaying -----------------------------------------------------
    def replay(self, record):
        """Feed a record from the market-ticks topic. Returns 'epoch', 'tick'
        or None (ignored: stale epoch, duplicate, or malformed)."""
        kind = record.get("type")
        if kind == "epoch":
            if self.epoch is not None and record["epoch"] < self.epoch:
                return None
            baselines = {c: (b["name"], b["value"]) for c, b in record["baselines"].items()}
            self.start_epoch(baselines, epoch=record["epoch"])
            return "epoch"
        if kind == "tick" and record.get("epoch") == self.epoch and record["id"] not in self.applied:
            driver = self.drivers.get(record["driver_code"])
            if driver is None:
                return None
            driver["current_value"] = record["value_after"]
            self._record(record)
            return "tick"
        return None

    def _record(self, tick):
        self.ticks.append(tick)
        self.applied.add(tick["id"])

    # ---- views ---------------------------------------------------------
    def state_message(self, code):
        """Value record for the `driver-stock-values` topic."""
        d = self.drivers[code]
        return {**d, "current_value": round(d["current_value"], 2), "epoch": self.epoch}

    def snapshot(self):
        return {
            "epoch": self.epoch,
            "values": {c: self.state_message(c) for c in self.drivers},
            "ticks": self.ticks,
        }
