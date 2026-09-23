import time

import pytest
from fastapi.testclient import TestClient

from gridpulse.game import STARTING_CASH
from gridpulse.server import create_app


def make(tmp_path, **kwargs):
    return TestClient(create_app("demo", data="simulated", db_path=tmp_path / "game.db", **kwargs))


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def wait_idle(client, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not client.get("/api/market").json()["sim"].get("running"):
            return
        time.sleep(0.1)
    raise AssertionError("weekend did not finish")


def join(client, name="Lando Fan"):
    r = client.post("/api/game/join", json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Trading reopens a few seconds after the last live tick; skip the wait in tests.
    monkeypatch.setattr("gridpulse.server.LIVE_QUIET_SECONDS", 0)
    with make(tmp_path) as c:
        yield c


def test_join_and_starting_cash(client):
    token = join(client)
    me = client.get("/api/game/me", headers=auth(token)).json()
    assert me["cash"] == me["value"] == STARTING_CASH
    assert me["rank"] == 1 and me["players"] == 1


@pytest.mark.parametrize("name", ["", "ab", "x" * 30, "<script>", "  "])
def test_bad_names(client, name):
    assert client.post("/api/game/join", json={"name": name}).status_code in (400, 422)


def test_names_are_unique_case_insensitively(client):
    join(client, "Tifosi")
    assert client.post("/api/game/join", json={"name": "tifosi"}).status_code == 409


def test_requires_token(client):
    assert client.get("/api/game/me").status_code == 401
    assert client.get("/api/game/me", headers=auth("nope")).status_code == 401


def test_buy_and_sell(client):
    token = join(client)
    r = client.post("/api/game/trade", headers=auth(token), json={"driver": "NOR", "side": "buy", "amount": 25_000})
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["cash"] == 75_000
    assert me["holdings"][0]["driver_code"] == "NOR"
    assert me["holdings"][0]["value"] == pytest.approx(25_000)

    r = client.post("/api/game/trade", headers=auth(token), json={"driver": "NOR", "side": "sell", "amount": 5_000})
    assert r.json()["holdings"][0]["value"] == pytest.approx(20_000)
    r = client.post("/api/game/trade", headers=auth(token), json={"driver": "NOR", "side": "sell"})  # sell all
    me = r.json()
    assert me["holdings"] == [] and me["cash"] == pytest.approx(STARTING_CASH)


@pytest.mark.parametrize("payload, status", [
    ({"driver": "NOR", "side": "buy", "amount": 200_000}, 400),   # more than your cash
    ({"driver": "NOR", "side": "buy", "amount": 5}, 400),         # under the minimum
    ({"driver": "NOR", "side": "buy", "amount": -100}, 400),
    ({"driver": "XXX", "side": "buy", "amount": 1000}, 404),
    ({"driver": "NOR", "side": "sell", "amount": 1000}, 400),     # nothing to sell
    ({"driver": "DOO", "side": "buy", "amount": 1000}, 400),      # benched driver
    ({"driver": "NOR", "side": "hold", "amount": 1000}, 422),
])
def test_invalid_trades(client, payload, status):
    token = join(client)
    assert client.post("/api/game/trade", headers=auth(token), json=payload).status_code == status
    assert client.get("/api/game/me", headers=auth(token)).json()["cash"] == STARTING_CASH


def test_holdings_follow_the_market_and_rank_players(client):
    bull, bear = join(client, "Bull"), join(client, "Bear")
    client.post("/api/game/trade", headers=auth(bull), json={"driver": "PIA", "side": "buy", "amount": 100_000})
    client.post("/api/simulate", json={"speed": "instant"})
    wait_idle(client)
    market = client.get("/api/market").json()
    pia = [t for t in market["ticks"] if t["live"] and t["driver_code"] == "PIA"]
    growth = pia[-1]["value_after"] / pia[0]["value_before"]
    me = client.get("/api/game/me", headers=auth(bull)).json()
    assert me["value"] == pytest.approx(100_000 * growth, rel=1e-6)
    board = client.get("/api/game/leaderboard", headers=auth(bear)).json()
    assert board["players"] == 2
    assert {row["name"] for row in board["top"]} == {"Bull", "Bear"}
    assert board["me"] == (1 if growth < 1 else 2)


def test_trading_pauses_during_a_live_weekend(client):
    token = join(client)
    client.post("/api/simulate", json={"speed": "normal"})
    r = client.post("/api/game/trade", headers=auth(token), json={"driver": "NOR", "side": "buy", "amount": 1000})
    assert r.status_code == 423
    client.post("/api/simulate/stop")
    wait_idle(client)
    r = client.post("/api/game/trade", headers=auth(token), json={"driver": "NOR", "side": "buy", "amount": 1000})
    assert r.status_code == 200


def test_reset_starts_a_new_season(client):
    token = join(client)
    client.post("/api/game/trade", headers=auth(token), json={"driver": "NOR", "side": "buy", "amount": 50_000})
    client.post("/api/reset")
    me = client.get("/api/game/me", headers=auth(token)).json()
    assert me["cash"] == STARTING_CASH and me["holdings"] == []


def test_restart_resumes_market_and_portfolios(tmp_path):
    with make(tmp_path) as c:
        token = join(c)
        c.post("/api/game/trade", headers=auth(token), json={"driver": "VER", "side": "buy", "amount": 40_000})
        c.post("/api/simulate", json={"speed": "instant"})
        wait_idle(c)
        before = c.get("/api/market").json()
        value = c.get("/api/game/me", headers=auth(token)).json()["value"]
    with make(tmp_path) as c:  # e.g. a redeploy
        after = c.get("/api/market").json()
        assert after["epoch"] == before["epoch"]
        assert len(after["ticks"]) == len(before["ticks"])
        assert after["next_race"] == before["next_race"] == "Italian Grand Prix"
        assert c.get("/api/game/me", headers=auth(token)).json()["value"] == pytest.approx(value)


# ---- public hosting -------------------------------------------------------------

def test_public_mode_guards(tmp_path):
    with make(tmp_path, public=True, admin_token="s3cret") as c:
        assert c.post("/api/simulate", json={"speed": "instant"}).status_code == 400
        assert c.post("/api/reset").status_code == 403
        assert c.post("/api/simulate", json={"speed": "fast"}).status_code == 200
        assert c.post("/api/simulate/stop").status_code == 403
        assert c.post("/api/simulate/stop", headers={"X-Admin-Token": "s3cret"}).status_code == 200
        wait_idle(c)
        # A trading window opens between weekends.
        assert c.post("/api/simulate", json={"speed": "fast"}).status_code == 425
        assert c.get("/api/market").json()["sim"]["cooldown_until"] > time.time()
        assert c.post("/api/reset", headers={"X-Admin-Token": "s3cret"}).status_code == 200


def test_join_is_rate_limited(client):
    codes = [client.post("/api/game/join", json={"name": f"Player {i}"}).status_code for i in range(7)]
    assert codes[:5] == [200] * 5 and codes[5:] == [429, 429]
