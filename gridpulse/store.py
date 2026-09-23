"""SQLite storage: the trading game, plus the demo market's live weekends
(so a demo-mode restart or redeploy resumes the season instead of wiping it)."""
import json
import sqlite3
import threading

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS live_ticks (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    epoch INTEGER NOT NULL, id TEXT NOT NULL, tick TEXT NOT NULL,
    UNIQUE (epoch, id)
);
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    token_hash TEXT NOT NULL UNIQUE,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS portfolios (
    player_id INTEGER NOT NULL REFERENCES players(id),
    epoch INTEGER NOT NULL,
    cash REAL NOT NULL,
    PRIMARY KEY (player_id, epoch)
);
CREATE TABLE IF NOT EXISTS holdings (
    player_id INTEGER NOT NULL, epoch INTEGER NOT NULL, driver_code TEXT NOT NULL,
    units REAL NOT NULL, cost REAL NOT NULL,
    PRIMARY KEY (player_id, epoch, driver_code)
);
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL, epoch INTEGER NOT NULL, driver_code TEXT NOT NULL,
    side TEXT NOT NULL, units REAL NOT NULL, price REAL NOT NULL, amount REAL NOT NULL, ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS trades_by_player ON trades (player_id, epoch, id);
"""


class Store:
    def __init__(self, path):
        self.path = str(path)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        if self.path != ":memory:":
            self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def execute(self, sql, params=()):
        with self.lock:
            return self.conn.execute(sql, params)

    def query(self, sql, params=()):
        with self.lock:
            return self.conn.execute(sql, params).fetchall()

    def transaction(self):
        return _Transaction(self)

    # ---- meta ------------------------------------------------------------
    def get_meta(self, key):
        rows = self.query("SELECT value FROM meta WHERE key = ?", (key,))
        return rows[0]["value"] if rows else None

    def set_meta(self, key, value):
        self.execute("INSERT INTO meta (key, value) VALUES (?, ?) "
                     "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))

    # ---- demo market log ---------------------------------------------------
    def save_tick(self, tick):
        self.execute("INSERT OR IGNORE INTO live_ticks (epoch, id, tick) VALUES (?, ?, ?)",
                     (tick["epoch"], tick["id"], json.dumps(tick)))

    def live_ticks(self, epoch):
        return [json.loads(r["tick"]) for r in
                self.query("SELECT tick FROM live_ticks WHERE epoch = ? ORDER BY seq", (epoch,))]

    def close(self):
        with self.lock:
            self.conn.close()


class _Transaction:
    """BEGIN IMMEDIATE ... COMMIT, holding the store lock throughout."""

    def __init__(self, store):
        self.store = store

    def __enter__(self):
        self.store.lock.acquire()
        self.store.conn.execute("BEGIN IMMEDIATE")
        return self.store.conn

    def __exit__(self, exc_type, *_):
        try:
            self.store.conn.execute("ROLLBACK" if exc_type else "COMMIT")
        finally:
            self.store.lock.release()
        return False
