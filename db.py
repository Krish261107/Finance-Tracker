"""SQLite data layer for the Finance Dashboard."""
import sqlite3
import hashlib
import os
import secrets
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "finance.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income','expense')),
                UNIQUE(user_id, name),
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('income','expense')),
                category TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)")


# ---------- Auth ----------
def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def create_user(username: str, password: str) -> tuple[bool, str]:
    if not username or not password:
        return False, "Username and password required."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    salt = secrets.token_hex(16)
    pwd_hash = _hash(password, salt)
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO users (username, salt, password_hash, created_at) VALUES (?,?,?,?)",
                (username.strip(), salt, pwd_hash, datetime.now().isoformat()),
            )
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "Username already exists."


def verify_user(username: str, password: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username.strip(),)).fetchone()
    if not row:
        return None
    if _hash(password, row["salt"]) == row["password_hash"]:
        return dict(row)
    return None


def delete_user_and_data(user_id: int):
    """Deletes the user row and all owned transactions/categories."""
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM categories WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))


# ---------- Categories ----------
DEFAULT_CATEGORIES = [
    ("Salary", "income"), ("Freelance", "income"), ("Investment", "income"), ("Other Income", "income"),
    ("Food & Dining", "expense"), ("Groceries", "expense"), ("Transport", "expense"),
    ("Shopping", "expense"), ("Bills & Utilities", "expense"), ("Rent", "expense"),
    ("Entertainment", "expense"), ("Health", "expense"), ("Education", "expense"), ("Other", "expense"),
]


def ensure_default_categories(user_id: int):
    with get_conn() as conn:
        for name, ctype in DEFAULT_CATEGORIES:
            conn.execute(
                "INSERT OR IGNORE INTO categories (user_id, name, type) VALUES (?,?,?)",
                (user_id, name, ctype),
            )


def get_categories(user_id: int, ctype: str = None):
    q = "SELECT * FROM categories WHERE user_id=?"
    params = [user_id]
    if ctype:
        q += " AND type=?"
        params.append(ctype)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q + " ORDER BY name", params).fetchall()]


def add_category(user_id: int, name: str, ctype: str):
    with get_conn() as conn:
        try:
            conn.execute("INSERT INTO categories (user_id, name, type) VALUES (?,?,?)", (user_id, name, ctype))
            return True
        except sqlite3.IntegrityError:
            return False


def delete_category(user_id: int, cat_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM categories WHERE id=? AND user_id=?", (cat_id, user_id))


# ---------- Transactions ----------
def add_transaction(user_id, date, amount, ttype, category, description=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO transactions (user_id,date,amount,type,category,description,created_at) VALUES (?,?,?,?,?,?,?)",
            (user_id, date, float(amount), ttype, category, description, datetime.now().isoformat()),
        )


def bulk_add_transactions(user_id: int, rows: list[dict]):
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO transactions (user_id,date,amount,type,category,description,created_at) VALUES (?,?,?,?,?,?,?)",
            [(user_id, r["date"], float(r["amount"]), r["type"], r["category"], r.get("description", ""),
              datetime.now().isoformat()) for r in rows],
        )


def update_transaction(tx_id, user_id, date, amount, ttype, category, description):
    with get_conn() as conn:
        conn.execute(
            "UPDATE transactions SET date=?, amount=?, type=?, category=?, description=? WHERE id=? AND user_id=?",
            (date, float(amount), ttype, category, description, tx_id, user_id),
        )


def delete_transaction(tx_id, user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE id=? AND user_id=?", (tx_id, user_id))


def get_transactions_df(user_id: int):
    import pandas as pd
    with get_conn() as conn:
        df = pd.read_sql_query(
            "SELECT * FROM transactions WHERE user_id=? ORDER BY date DESC", conn, params=(user_id,)
        )
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def clear_all_transactions(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM transactions WHERE user_id=?", (user_id,))
