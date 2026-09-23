import time

import pytest
from fastapi.testclient import TestClient

from gridpulse.server import create_app


@pytest.fixture()
def client(tmp_path):
    with TestClient(create_app("demo", data="simulated", db_path=tmp_path / "test.db")) as c:
        yield c


def wait_idle(client, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        market = client.get("/api/market").json()
        if not market["sim"].get("running"):
            return market
        time.sleep(0.1)
    raise AssertionError("simulation did not finish")


def test_snapshot(client):
    market = client.get("/api/market").json()
    assert market["ready"] and market["mode"] == "demo"
    assert len(market["values"]) == 21
    assert market["next_race"] == "Dutch Grand Prix"
    assert client.get("/drivers/VER.jpg").status_code == 200


def test_simulate_whole_weekend(client):
    before = len(client.get("/api/market").json()["ticks"])
    assert client.post("/api/simulate", json={"speed": "instant"}).status_code == 200
    market = wait_idle(client)
    live = [t for t in market["ticks"] if t["live"]]
    assert len(market["ticks"]) - before == len(live) == 100
    assert {t["round"] for t in live} == {15}
    assert market["next_race"] == "Italian Grand Prix"
    # Can't price the same weekend twice.
    assert client.post("/api/simulate", json={"race": "Dutch Grand Prix", "speed": "instant"}).status_code == 409


def test_second_simulation_is_rejected_while_running(client):
    assert client.post("/api/simulate", json={"speed": "normal"}).status_code == 200
    assert client.post("/api/simulate", json={"speed": "normal"}).status_code == 409
    client.post("/api/simulate/stop")
    wait_idle(client)


def test_stopped_weekend_resumes(client):
    client.post("/api/simulate", json={"speed": "fast"})
    time.sleep(2.5)
    client.post("/api/simulate/stop")
    market = wait_idle(client)
    done = {t["session"] for t in market["ticks"] if t["round"] == 15}
    assert done and "race" not in done
    assert market["next_race"] == "Dutch Grand Prix"  # not skipped

    client.post("/api/simulate", json={"speed": "instant"})
    market = wait_idle(client)
    sessions = {}
    for t in market["ticks"]:
        if t["round"] == 15:
            sessions.setdefault(t["session"], set()).add(t["driver_code"])
    assert set(sessions) == {"practice1", "practice2", "practice3", "qualifying", "race"}
    assert len(sessions["race"]) == 20


def test_bad_requests(client):
    assert client.post("/api/simulate", json={"race": "Moon Grand Prix"}).status_code == 404
    assert client.post("/api/simulate", json={"speed": "ludicrous"}).status_code == 400
    assert client.post("/api/simulate", json={"race": "Monaco Grand Prix", "speed": "instant"}).status_code == 409


def test_reset(client):
    client.post("/api/simulate", json={"speed": "instant"})
    wait_idle(client)
    assert client.post("/api/reset").status_code == 200
    market = client.get("/api/market").json()
    assert not any(t["live"] for t in market["ticks"])


def test_websocket_streams_snapshot_then_ticks(client):
    with client.websocket_connect("/ws") as ws:
        assert ws.receive_json()["type"] == "snapshot"
        client.post("/api/simulate", json={"speed": "instant"})
        kinds = set()
        while True:
            msg = ws.receive_json()
            kinds.add(msg["type"])
            if msg["type"] == "sim" and not msg["sim"]["running"] and msg["sim"].get("finished"):
                break
        assert kinds == {"sim", "tick"}
