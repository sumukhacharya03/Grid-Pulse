"""Dashboard backend: serves the web UI, streams the market over a WebSocket
and runs the trading game.

Two sources feed the same MarketEngine:
  * kafka - tails `market-ticks`, so the UI reflects the real pipeline
  * demo  - builds the market in-process from the CSV + historical JSON, for
            running (or hosting) the dashboard without a Kafka broker
Either way "Go live" runs the next race weekend (the real results replayed,
or a simulation): in kafka mode the results go onto the real-time topics for
realtime_service.py to price; in demo mode they are priced directly.

Public mode (for hosting) keeps strangers from spoiling it for each other:
no instant replays, a trading window between weekends, and only an admin
can stop a weekend or reset the market before the season is over.
"""
import asyncio
import hashlib
import inspect
import json
import random
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request, WebSocket
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import pricing, roster
from .baseline import read_baselines
from .config import ASSETS_DIR, DATA_SOURCE, ROOT, WEB_DIST_DIR
from .game import STARTING_CASH, Game, GameError
from .history import historical_weekends, live_weekend, weekend_sessions
from .market import MarketEngine, result_sort_key
from .season import CALENDAR, HISTORICAL_ROUNDS, SESSION_KIND, SESSION_NAME, race_by_name
from .store import Store

# Seconds between results / before each session, per replay speed.
SPEEDS = {"normal": (1.1, 3.0), "fast": (0.3, 1.2), "instant": (0.0, 0.0)}
PUBLIC_SPEEDS = ("normal", "fast")
PUBLIC_COOLDOWN = 60  # trading window between weekends when hosted publicly
LIVE_QUIET_SECONDS = 8  # trading reopens this long after the last live tick
PUBLIC_TICK_FIELDS = ("id", "driver_code", "race", "round", "session", "session_name", "kind", "position",
                      "expected", "grid", "status", "points", "fastest_lap", "value_before", "value_after",
                      "change_pct", "moves", "ts", "live")
DEFAULT_DB = ROOT / "gridpulse.db"


def public_tick(tick):
    return {k: tick.get(k) for k in PUBLIC_TICK_FIELDS}


class RateLimiter:
    """At most `limit` events per `window` seconds per key."""

    def __init__(self, limit, window):
        self.limit, self.window = limit, window
        self.events = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key):
        now = time.monotonic()
        with self.lock:
            q = self.events[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                raise HTTPException(429, "Slow down a little and try again in a moment.")
            q.append(now)


class MarketHub:
    """Owns the market shown on the dashboard and fans updates out to clients."""

    def __init__(self, mode, data=DATA_SOURCE, public=False, store=None):
        self.mode = mode
        self.data = data
        self.public = public
        self.store = store
        self.game = Game(store)
        self.engine = MarketEngine()
        self.lock = threading.RLock()
        self.ready = False
        self.loop = None
        self.clients = set()
        self.sim = {"running": False}
        self.sim_stop = threading.Event()
        self.sim_lock = threading.Lock()
        self.sim_thread = None
        self.last_live_tick = 0.0
        self.cooldown_until = 0.0
        self.stop = threading.Event()

    # ---- fan-out -------------------------------------------------------
    def broadcast(self, message):
        if self.loop is None:
            return
        payload = json.dumps(message)

        def deliver():
            for queue in list(self.clients):
                if queue.qsize() > 2000:  # a stalled tab; drop it rather than grow forever
                    self.clients.discard(queue)
                    continue
                queue.put_nowait(payload)

        self.loop.call_soon_threadsafe(deliver)

    def snapshot(self):
        with self.lock:
            return {
                "mode": self.mode,
                "data": self.data,
                "public": self.public,
                "ready": self.ready,
                "epoch": self.engine.epoch,
                "roster": roster.roster_payload(),
                "calendar": [r.payload() for r in CALENDAR],
                "values": {c: self.engine.state_message(c) for c in self.engine.drivers},
                "ticks": [public_tick(t) for t in self.engine.ticks],
                "sim": {**self.sim, "cooldown_until": self.cooldown_until},
                "next_race": self.next_race(),
                "game": {"starting_cash": STARTING_CASH},
            }

    def on_tick(self, tick):
        if tick.get("live"):
            self.last_live_tick = time.time()
        self.broadcast({"type": "tick", "tick": public_tick(tick)})

    def set_sim(self, **status):
        self.sim = status
        self.broadcast({"type": "sim", "sim": {**status, "cooldown_until": self.cooldown_until},
                        "next_race": self.next_race()})

    # ---- market state for the game -------------------------------------------
    def market_open(self):
        return not self.sim.get("running") and time.time() - self.last_live_tick > LIVE_QUIET_SECONDS

    def prices(self):
        with self.lock:
            return {c: d["current_value"] for c, d in self.engine.drivers.items()}

    def tradable(self):
        with self.lock:
            return {c for c in self.engine.drivers if c in roster.DRIVERS and roster.is_active(c, roster.FINAL_ROUND)}

    # ---- season --------------------------------------------------------
    def priced_sessions(self, round_number):
        """{session_key: [driver codes in classification order]} already in the market."""
        sessions = {}
        with self.lock:
            for t in self.engine.ticks:
                if t["round"] == round_number:
                    sessions.setdefault(t["session"], []).append((t["position"] or 99, t["driver_code"]))
        return {k: [code for _, code in sorted(v)] for k, v in sessions.items()}

    def next_race(self):
        """First live-season race with sessions left to run (a weekend stopped
        halfway is resumed rather than skipped)."""
        for race in CALENDAR:
            if race.round <= HISTORICAL_ROUNDS:
                continue
            priced = self.priced_sessions(race.round)
            if any(key not in priced for key, *_ in race.sessions):
                return race.name
        return None

    # ---- sources -------------------------------------------------------
    def _demo_epoch_key(self, baselines, weekends):
        """Same data + same pricing model => same epoch, so a restart resumes
        the season (and everyone's portfolios). Change either and a new
        season starts on its own."""
        digest = hashlib.sha256()
        digest.update(json.dumps(sorted(baselines.items())).encode())
        digest.update(json.dumps(weekends, sort_keys=True).encode())
        digest.update(inspect.getsource(pricing).encode())
        return f"demo_epoch:{self.data}:{digest.hexdigest()[:16]}"

    def build_demo_market(self, new_epoch=False):
        baselines, problems = read_baselines()
        for p in problems:
            print(f"Baseline CSV: {p}")
        weekends = historical_weekends(self.data)
        key = self._demo_epoch_key(baselines, weekends)
        epoch = None if new_epoch else self.store.get_meta(key)
        if epoch is None:
            epoch = int(time.time() * 1000)
            self.store.set_meta(key, epoch)
        epoch = int(epoch)

        results = [r for w in weekends for _, rs in weekend_sessions(w) for r in rs]
        with self.lock:
            self.engine.start_epoch(baselines, epoch=epoch)
            for r in sorted(results, key=result_sort_key):
                self.engine.apply(r)
            resumed = sum(self.engine.replay(t) == "tick" for t in self.store.live_ticks(epoch))
            self.ready = True
        print(f"Demo market built from {self.data} data: {len(self.engine.drivers)} drivers, "
              f"{len(self.engine.ticks)} price moves ({resumed} live moves resumed).")

    def run_kafka_source(self):
        from .config import TOPIC_MARKET_TICKS
        from .kafka_io import ensure_topics, follow

        ensure_topics()

        def caught_up():
            with self.lock:
                self.ready = True
            print(f"Dashboard caught up with Kafka: epoch {self.engine.epoch}, {len(self.engine.ticks)} price moves.")
            self.broadcast({"type": "snapshot", "data": self.snapshot()})

        for message in follow([TOPIC_MARKET_TICKS], on_caught_up=caught_up, stop=self.stop):
            with self.lock:
                outcome = self.engine.replay(message.value)
                ready = self.ready
            if not ready:
                continue
            if outcome == "epoch":
                self.broadcast({"type": "snapshot", "data": self.snapshot()})
            elif outcome == "tick":
                self.on_tick(message.value)

    # ---- live weekends -------------------------------------------------
    def start_simulation(self, race_name, speed):
        with self.sim_lock:
            if self.sim.get("running"):
                raise HTTPException(409, "A weekend is already running")
            if self.public:
                if speed not in PUBLIC_SPEEDS:
                    raise HTTPException(400, f"Pick one of: {', '.join(PUBLIC_SPEEDS)}")
                wait = self.cooldown_until - time.time()
                if wait > 0:
                    raise HTTPException(425, f"Trading window open: the next weekend can start in {int(wait) + 1}s")
            race = self._pick_race(race_name, speed)
            try:
                weekend = self._weekend_for(race)
            except FileNotFoundError as e:
                raise HTTPException(409, str(e))
            self.sim = {"running": True, "race": race.name, "round": race.round, "phase": "starting"}
        self.sim_stop.clear()
        self.sim_thread = threading.Thread(target=self._run_weekend, args=(race, weekend, speed), daemon=True)
        self.sim_thread.start()

    def _pick_race(self, race_name, speed):
        race_name = race_name or self.next_race()
        if not race_name:
            raise HTTPException(400, "The season is complete. Reset the market to race again.")
        try:
            race = race_by_name(race_name)
        except KeyError as e:
            raise HTTPException(404, str(e))
        priced = self.priced_sessions(race.round)
        if all(key in priced for key, *_ in race.sessions):
            raise HTTPException(409, f"{race.name} has already been priced into the market")
        if speed not in SPEEDS:
            raise HTTPException(400, f"speed must be one of {', '.join(SPEEDS)}")
        return race

    def _weekend_for(self, race):
        priced = self.priced_sessions(race.round)
        # Resuming a simulated weekend: races start from the qualifying order already priced.
        grids = {k: codes for k, codes in priced.items() if SESSION_KIND[k] in ("qualifying", "sprint_qualifying")}
        return live_weekend(race, self.data, random.Random(), grids=grids)

    def _run_weekend(self, race, weekend, speed):
        result_gap, session_gap = SPEEDS[speed]
        sessions = [s[0] for s in race.sessions]
        priced = self.priced_sessions(race.round)
        producer = None
        if self.mode == "kafka":
            from .kafka_io import make_producer
            producer = make_producer()
        status = {"running": True, "race": race.name, "round": race.round, "speed": speed, "data": self.data,
                  "total_sessions": len(sessions), "warning": None}
        try:
            for index, session_key in enumerate(sessions):
                if self.sim_stop.is_set():
                    break
                if session_key in priced:
                    continue
                self.set_sim(**status, session=session_key, session_name=SESSION_NAME[session_key],
                             kind=SESSION_KIND[session_key], session_index=index, phase="starting", sent=0)
                self.sim_stop.wait(session_gap)
                results = weekend.live_results(session_key)
                sent_at = time.time()
                for n, result in enumerate(results, 1):
                    if self.sim_stop.is_set():
                        break
                    if producer is not None:
                        self._send_to_kafka(producer, result)
                    else:
                        with self.lock:
                            tick = self.engine.apply(result, live=True)
                        if tick:
                            self.store.save_tick(tick)
                            self.on_tick(tick)
                    if producer is not None and n >= 6:
                        # Results are flowing to Kafka; is anything pricing them?
                        stalled = self.last_live_tick < sent_at
                        status["warning"] = "No price updates yet. Is realtime_service.py running?" if stalled else None
                    self.set_sim(**status, session=session_key, session_name=SESSION_NAME[session_key],
                                 kind=SESSION_KIND[session_key], session_index=index, phase="live",
                                 sent=n, field=len(results))
                    self.sim_stop.wait(result_gap * random.uniform(0.6, 1.4))
            if producer is not None:
                producer.flush()
        finally:
            if producer is not None:
                producer.close()
            if self.public:
                self.cooldown_until = time.time() + PUBLIC_COOLDOWN
            self.set_sim(running=False, finished=race.name, stopped=self.sim_stop.is_set(),
                         warning=status["warning"])

    @staticmethod
    def _send_to_kafka(producer, result):
        from .config import TOPIC_LIVE_PRACTICE, TOPIC_LIVE_QUALIFYING, TOPIC_LIVE_RACE
        kind = SESSION_KIND[result["session_type"]]
        topic = {"practice": TOPIC_LIVE_PRACTICE, "qualifying": TOPIC_LIVE_QUALIFYING,
                 "sprint_qualifying": TOPIC_LIVE_QUALIFYING}.get(kind, TOPIC_LIVE_RACE)
        producer.send(topic, key=result["driverCode"], value=result)
        producer.flush()

    def stop_simulation(self):
        self.sim_stop.set()

    def reset_demo(self):
        """Start a new season: fresh market, and a fresh $100k for every player."""
        if self.mode != "demo":
            raise HTTPException(400, "In Kafka mode, reset by re-running calculation_service.py")
        if self.sim.get("running"):
            self.stop_simulation()
            if self.sim_thread:
                self.sim_thread.join(timeout=5)
        self.build_demo_market(new_epoch=True)
        self.sim = {"running": False}
        self.cooldown_until = 0.0
        self.broadcast({"type": "snapshot", "data": self.snapshot()})


class SimulateRequest(BaseModel):
    race: str | None = Field(default=None, max_length=60)
    speed: str = Field(default="fast", max_length=10)


class JoinRequest(BaseModel):
    name: str = Field(max_length=40)


class TradeRequest(BaseModel):
    driver: str = Field(max_length=5)
    side: Literal["buy", "sell"]
    amount: float | None = None  # dollars; None on a sell = sell everything


def create_app(mode="demo", data=DATA_SOURCE, public=False, db_path=None, admin_token=None):
    store = Store(db_path or DEFAULT_DB)
    hub = MarketHub(mode, data=data, public=public, store=store)
    join_limit = RateLimiter(5, 3600)
    trade_limit = RateLimiter(40, 60)

    @asynccontextmanager
    async def lifespan(app):
        hub.loop = asyncio.get_running_loop()
        if mode == "demo":
            hub.build_demo_market()
        else:
            threading.Thread(target=hub.run_kafka_source, daemon=True, name="kafka-source").start()
        yield
        hub.stop.set()
        hub.sim_stop.set()
        store.close()

    app = FastAPI(title="Grid-Pulse", lifespan=lifespan)
    app.state.hub = hub
    app.add_middleware(GZipMiddleware, minimum_size=2048)

    @app.exception_handler(GameError)
    async def game_error(_: Request, exc: GameError):
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    def is_admin(token):
        return bool(admin_token) and token == admin_token

    # ---- market ----------------------------------------------------------
    @app.get("/api/health")
    def health():
        if not hub.ready:
            raise HTTPException(503, "starting")
        return {"ok": True, "mode": hub.mode, "data": hub.data}

    @app.get("/api/market")
    def market():
        return hub.snapshot()

    @app.post("/api/simulate")
    def simulate(req: SimulateRequest):
        hub.start_simulation(req.race, req.speed)
        return {"ok": True}

    @app.post("/api/simulate/stop")
    def stop(x_admin_token: str | None = Header(default=None)):
        if hub.public and not is_admin(x_admin_token):
            raise HTTPException(403, "Only the host can stop a live weekend")
        hub.stop_simulation()
        return {"ok": True}

    @app.post("/api/reset")
    def reset(x_admin_token: str | None = Header(default=None)):
        if hub.public and not is_admin(x_admin_token) and hub.next_race() is not None:
            raise HTTPException(403, "The market can be reset once the season is over")
        hub.reset_demo()
        return {"ok": True}

    # ---- game ----------------------------------------------------------------
    def epoch():
        if not hub.ready or hub.engine.epoch is None:
            raise HTTPException(503, "The market isn't open yet")
        return hub.engine.epoch

    def player(authorization):
        token = (authorization or "").removeprefix("Bearer ").strip()
        found = hub.game.player_for(token)
        if found is None:
            raise HTTPException(401, "Join the game first")
        return found

    @app.post("/api/game/join")
    def join(req: JoinRequest, request: Request):
        current = epoch()  # before creating the player, so a 503 can't strand a new account
        join_limit.check(request.client.host if request.client else "?")
        token, who = hub.game.join(req.name)
        hub.broadcast({"type": "game"})
        return {"token": token, "portfolio": hub.game.portfolio(who, current, hub.prices())}

    @app.get("/api/game/me")
    def me(authorization: str | None = Header(default=None)):
        return hub.game.portfolio(player(authorization), epoch(), hub.prices())

    @app.post("/api/game/trade")
    def trade(req: TradeRequest, authorization: str | None = Header(default=None)):
        who = player(authorization)
        trade_limit.check(who["id"])
        if not hub.market_open():
            raise HTTPException(423, "Trading is paused while a session is live")
        result = hub.game.trade(who, epoch(), req.driver.upper(), req.side, req.amount, hub.prices(), hub.tradable())
        hub.broadcast({"type": "game"})
        return result

    @app.get("/api/game/leaderboard")
    def leaderboard(authorization: str | None = Header(default=None)):
        who = hub.game.player_for((authorization or "").removeprefix("Bearer ").strip())
        return hub.game.leaderboard(epoch(), hub.prices(), limit=10, me=who["id"] if who else None)

    # ---- stream --------------------------------------------------------------
    @app.websocket("/ws")
    async def ws(websocket: WebSocket):
        await websocket.accept()
        queue = asyncio.Queue()
        hub.clients.add(queue)
        try:
            await websocket.send_text(json.dumps({"type": "snapshot", "data": hub.snapshot()}))
            while True:
                await websocket.send_text(await queue.get())
        except Exception:  # disconnects surface as several exception types
            pass
        finally:
            hub.clients.discard(queue)

    app.mount("/drivers", StaticFiles(directory=ASSETS_DIR), name="drivers")
    if (WEB_DIST_DIR / "index.html").exists():
        app.mount("/", StaticFiles(directory=WEB_DIST_DIR, html=True), name="web")
    else:
        @app.get("/", response_class=HTMLResponse)
        def not_built():
            return ("<body style='background:#07080b;color:#e8edf3;font-family:system-ui;padding:40px'>"
                    "<h1>Grid-Pulse</h1><p>The web UI has not been built yet. Run:</p>"
                    "<pre>cd web\nnpm install\nnpm run build</pre>"
                    "<p>or use <code>npm run dev</code> for live reload.</p></body>")

    return app
