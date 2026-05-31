import pytest
import sqlite3
from database.db import DB_PATH

KNOWN_EXPENSES = [
    (450.00,  "Food",          "2026-05-02", "Lunch at office canteen"),
    (120.00,  "Transport",     "2026-05-05", "Auto-rickshaw to metro"),
    (2200.00, "Bills",         "2026-05-07", "Electricity bill May"),
    (800.00,  "Health",        "2026-05-10", "Pharmacy — vitamins"),
    (350.00,  "Entertainment", "2026-05-13", "Movie tickets"),
    (1500.00, "Shopping",      "2026-05-17", "New headphones"),
    (90.00,   "Transport",     "2026-05-20", "Cab to airport"),
    (600.00,  "Other",         "2026-05-24", "Gift for colleague"),
]


@pytest.fixture
def app():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    with flask_app.app_context():
        yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def controlled_user_id():
    """Fresh user with exactly 8 known expenses. Cleaned up after the test."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "test-controlled@spendly.com", "x"),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [(user_id, amt, cat, dt, desc) for amt, cat, dt, desc in KNOWN_EXPENSES],
    )
    conn.commit()
    conn.close()
    yield user_id
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


@pytest.fixture
def empty_user_id():
    """User with no expenses. Cleaned up after the test."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Empty User", "test-empty@spendly.com", "x"),
    )
    conn.commit()
    user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    yield user_id
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


@pytest.fixture
def seed_user_id():
    """Id of the seeded demo@spendly.com user (for route auth tests only)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?", ("demo@spendly.com",)
    ).fetchone()
    conn.close()
    return row["id"]
