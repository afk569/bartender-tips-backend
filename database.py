import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "tips.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS workers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            supplement  REAL NOT NULL DEFAULT 0,
            min_hourly  REAL NOT NULL DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            date         TEXT NOT NULL,
            total_amount REAL NOT NULL,
            total_hours  REAL NOT NULL,
            hourly_rate  REAL NOT NULL,
            workers_json TEXT NOT NULL
        )
    """)

    # Add min_hourly column if upgrading from old database
    try:
        conn.execute("ALTER TABLE workers ADD COLUMN min_hourly REAL NOT NULL DEFAULT 0")
    except Exception:
        pass  # Column already exists, ignore

    conn.commit()
    conn.close()


# ── Workers ───────────────────────────────────────────────────────────────────

def get_all_workers() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM workers ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_worker(name: str, supplement: float, min_hourly: float) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO workers (name, supplement, min_hourly) VALUES (?, ?, ?)",
        (name, supplement, min_hourly)
    )
    conn.commit()
    worker_id = cur.lastrowid
    conn.close()
    return worker_id


def update_worker(worker_id: int, name: str, supplement: float, min_hourly: float) -> bool:
    conn = get_connection()
    cur = conn.execute(
        "UPDATE workers SET name=?, supplement=?, min_hourly=? WHERE id=?",
        (name, supplement, min_hourly, worker_id)
    )
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def delete_worker(worker_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM workers WHERE id=?", (worker_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def get_worker_data(name: str) -> dict:
    """Return supplement and min_hourly for a worker by name."""
    conn = get_connection()
    row = conn.execute(
        "SELECT supplement, min_hourly FROM workers WHERE name=?", (name,)
    ).fetchone()
    conn.close()
    if row:
        return {"supplement": row["supplement"], "min_hourly": row["min_hourly"]}
    return {"supplement": 0.0, "min_hourly": 0.0}


# ── Shifts ────────────────────────────────────────────────────────────────────

def save_shift(date: str, total_amount: float, total_hours: float,
               hourly_rate: float, workers: list) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO shifts (date, total_amount, total_hours, hourly_rate, workers_json)
           VALUES (?, ?, ?, ?, ?)""",
        (date, total_amount, total_hours, hourly_rate, json.dumps(workers))
    )
    conn.commit()
    shift_id = cur.lastrowid
    conn.close()
    return shift_id


def get_all_shifts() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM shifts ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_shift_by_id(shift_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM shifts WHERE id=?", (shift_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_shift(shift_id: int) -> bool:
    conn = get_connection()
    cur = conn.execute("DELETE FROM shifts WHERE id=?", (shift_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0
