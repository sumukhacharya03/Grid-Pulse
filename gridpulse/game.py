"""The trading game: every player gets $100,000 of pretend money per market
epoch (a "season") to invest in drivers. A holding moves with its driver's
price, so buying $10,000 of a driver who then rises 5% makes it $10,500."""
import hashlib
import re
import secrets
import sqlite3
import time

STARTING_CASH = 100_000.0
MIN_TRADE = 100.0
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{1,18}[A-Za-z0-9]$")


class GameError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class Game:
    def __init__(self, store):
        self.store = store

    # ---- players -----------------------------------------------------------
    def join(self, name):
        name = " ".join((name or "").split())
        if not NAME_RE.match(name):
            raise GameError(400, "Pick a name of 3-20 letters, numbers, spaces, dots, dashes or underscores.")
        token = secrets.token_urlsafe(24)
        try:
            cur = self.store.execute("INSERT INTO players (name, token_hash, created_at) VALUES (?, ?, ?)",
                                     (name, _hash(token), time.time()))
        except sqlite3.IntegrityError:
            raise GameError(409, f"The name “{name}” is taken.")
        return token, {"id": cur.lastrowid, "name": name}

    def player_for(self, token):
        if not token:
            return None
        rows = self.store.query("SELECT id, name FROM players WHERE token_hash = ?", (_hash(token),))
        return dict(rows[0]) if rows else None

    # ---- portfolio -----------------------------------------------------------
    def _cash(self, conn, player_id, epoch):
        row = conn.execute("SELECT cash FROM portfolios WHERE player_id = ? AND epoch = ?",
                           (player_id, epoch)).fetchone()
        if row is None:
            conn.execute("INSERT INTO portfolios (player_id, epoch, cash) VALUES (?, ?, ?)",
                         (player_id, epoch, STARTING_CASH))
            return STARTING_CASH
        return row["cash"]

    def portfolio(self, player, epoch, prices):
        with self.store.transaction() as conn:
            cash = self._cash(conn, player["id"], epoch)
            holdings = conn.execute("SELECT driver_code, units, cost FROM holdings WHERE player_id = ? AND epoch = ?",
                                    (player["id"], epoch)).fetchall()
            trades = conn.execute("SELECT driver_code, side, amount, price, ts FROM trades "
                                  "WHERE player_id = ? AND epoch = ? ORDER BY id DESC LIMIT 15",
                                  (player["id"], epoch)).fetchall()
        items = []
        for h in holdings:
            value = h["units"] * prices.get(h["driver_code"], 0)
            items.append({"driver_code": h["driver_code"], "units": h["units"], "cost": round(h["cost"], 2),
                          "value": round(value, 2), "pnl_pct": round((value / h["cost"] - 1) * 100, 3) if h["cost"] else 0})
        items.sort(key=lambda i: -i["value"])
        total = cash + sum(i["value"] for i in items)
        board = self.leaderboard(epoch, prices, limit=0, me=player["id"])
        return {
            "player": player, "epoch": epoch, "starting_cash": STARTING_CASH,
            "cash": round(cash, 2), "holdings": items, "value": round(total, 2),
            "return_pct": round((total / STARTING_CASH - 1) * 100, 3),
            "rank": board["me"], "players": board["players"],
            "trades": [dict(t) for t in trades],
        }

    def trade(self, player, epoch, code, side, amount, prices, tradable):
        """Buy or sell `amount` dollars of `code` at the current price.
        amount=None on a sell means "sell everything"."""
        if side not in ("buy", "sell"):
            raise GameError(400, "side must be 'buy' or 'sell'")
        price = prices.get(code)
        if not price:
            raise GameError(404, f"Unknown driver {code}")
        if amount is not None and not (amount == amount and 0 < amount < 1e12):  # rejects NaN / inf / <= 0
            raise GameError(400, "Enter a positive amount")

        with self.store.transaction() as conn:
            cash = self._cash(conn, player["id"], epoch)
            row = conn.execute("SELECT units, cost FROM holdings WHERE player_id = ? AND epoch = ? AND driver_code = ?",
                               (player["id"], epoch, code)).fetchone()
            units, cost = (row["units"], row["cost"]) if row else (0.0, 0.0)

            if side == "buy":
                if code not in tradable:
                    raise GameError(400, f"{code} is not on the grid anymore; the stock can only be sold.")
                if amount is None or amount < MIN_TRADE:
                    raise GameError(400, f"The minimum trade is ${MIN_TRADE:,.0f}")
                if amount > cash + 0.005:
                    raise GameError(400, f"Not enough cash (you have ${cash:,.2f})")
                amount = min(amount, cash)
                delta_units = amount / price
                units, cost, cash = units + delta_units, cost + amount, cash - amount
            else:
                held = units * price
                if units <= 0:
                    raise GameError(400, f"You don't own any {code}")
                if amount is None or amount >= held - 0.01:  # sell it all, leave no dust
                    amount, delta_units = held, units
                else:
                    if amount < MIN_TRADE:
                        raise GameError(400, f"The minimum trade is ${MIN_TRADE:,.0f}")
                    delta_units = amount / price
                cost -= cost * (delta_units / units)
                units -= delta_units
                cash += amount

            conn.execute("UPDATE portfolios SET cash = ? WHERE player_id = ? AND epoch = ?",
                         (round(cash, 2), player["id"], epoch))
            if units <= 1e-12:
                conn.execute("DELETE FROM holdings WHERE player_id = ? AND epoch = ? AND driver_code = ?",
                             (player["id"], epoch, code))
            else:
                conn.execute("INSERT INTO holdings (player_id, epoch, driver_code, units, cost) VALUES (?, ?, ?, ?, ?) "
                             "ON CONFLICT(player_id, epoch, driver_code) DO UPDATE SET units = excluded.units, cost = excluded.cost",
                             (player["id"], epoch, code, units, cost))
            conn.execute("INSERT INTO trades (player_id, epoch, driver_code, side, units, price, amount, ts) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (player["id"], epoch, code, side, delta_units, price, round(amount, 2), time.time()))
        return self.portfolio(player, epoch, prices)

    # ---- leaderboard -----------------------------------------------------------
    def leaderboard(self, epoch, prices, limit=10, me=None):
        portfolios = self.store.query(
            "SELECT p.player_id, p.cash, pl.name FROM portfolios p JOIN players pl ON pl.id = p.player_id "
            "WHERE p.epoch = ?", (epoch,))
        values = {r["player_id"]: {"name": r["name"], "value": r["cash"], "top": None, "top_value": 0.0}
                  for r in portfolios}
        for h in self.store.query("SELECT player_id, driver_code, units FROM holdings WHERE epoch = ?", (epoch,)):
            entry = values.get(h["player_id"])
            if entry is None:
                continue
            v = h["units"] * prices.get(h["driver_code"], 0)
            entry["value"] += v
            if v > entry["top_value"]:
                entry["top"], entry["top_value"] = h["driver_code"], v
        ranked = sorted(values.items(), key=lambda kv: -kv[1]["value"])
        rank_of = {pid: i + 1 for i, (pid, _) in enumerate(ranked)}
        return {
            "players": len(ranked),
            "me": rank_of.get(me),
            "starting_cash": STARTING_CASH,
            "top": [
                {"rank": i + 1, "id": pid, "name": e["name"], "value": round(e["value"], 2),
                 "return_pct": round((e["value"] / STARTING_CASH - 1) * 100, 3), "top_holding": e["top"]}
                for i, (pid, e) in enumerate(ranked[:limit])
            ],
        }
