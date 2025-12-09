
# tests/conftest.py
import os
import sqlite3
import pytest
from datetime import date

# Change this import to match your app module
# e.g., from server import app as flask_app
from app import app as flask_app  # <-- adjust if needed

DB_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS stops (
    stop_id TEXT PRIMARY KEY,
    stop_name TEXT NOT NULL,
    stop_lat REAL NOT NULL,
    stop_lon REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS trips (
    trip_id TEXT PRIMARY KEY,
    route_id TEXT NOT NULL,
    trip_headsign TEXT
);

CREATE TABLE IF NOT EXISTS stop_times (
    trip_id TEXT NOT NULL,
    arrival_time TEXT NOT NULL,       -- HH:MM:SS
    departure_time TEXT NOT NULL,     -- HH:MM:SS
    stop_id TEXT NOT NULL,
    stop_sequence INTEGER NOT NULL,
    FOREIGN KEY (trip_id) REFERENCES trips(trip_id),
    FOREIGN KEY (stop_id) REFERENCES stops(stop_id)
);

CREATE INDEX IF NOT EXISTS idx_stop_times_trip ON stop_times(trip_id);
CREATE INDEX IF NOT EXISTS idx_stop_times_stop ON stop_times(stop_id);
"""

def seed_demo_data(conn):
    cur = conn.cursor()
    # Stops around central Wrocław
    stops = [
        ("WR-1001", "Dworzec Główny", 51.0987, 17.0362),
        ("WR-1002", "Arkady (Capitol)", 51.0999, 17.0289),
        ("WR-2001", "Rynek", 51.1090, 17.0326),
    ]
    cur.executemany(
        "INSERT INTO stops(stop_id, stop_name, stop_lat, stop_lon) VALUES (?,?,?,?)", stops
    )

    # Trips (line labels via route_id)
    trips = [
        ("TRIP_002", "2", "Biskupin"),
        ("TRIP_031", "31", "Kromera"),
        ("TRIP_X", "D", "Dworzec Nadodrze"),
    ]
    cur.executemany(
        "INSERT INTO trips(trip_id, route_id, trip_headsign) VALUES (?,?,?)", trips
    )

    # Stop times (ordered sequences)
    # Simplified: times on same day; your app converts to ISO when building response.
    stop_times = [
        # TRIP_002 across two central stops
        ("TRIP_002", "08:35:00", "08:37:00", "WR-1001", 1),
        ("TRIP_002", "08:39:00", "08:40:00", "WR-2001", 2),
        # TRIP_031 at Arkady
        ("TRIP_031", "08:37:00", "08:39:00", "WR-1002", 1),
        # TRIP_X at Dworzec Główny
        ("TRIP_X", "08:41:00", "08:42:00", "WR-1001", 1),
    ]
    cur.executemany(
        """INSERT INTO stop_times(trip_id, arrival_time, departure_time, stop_id, stop_sequence)
           VALUES (?,?,?,?,?)""",
        stop_times,
    )
    conn.commit()

@pytest.fixture(scope="session")
def test_db_path(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "wroclaw_gtfs.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(DB_TABLES_SQL)
        seed_demo_data(conn)
    finally:
        conn.close()
    return str(db_path)

@pytest.fixture(scope="session")
def app(test_db_path, monkeypatch):
    # Monkeypatch module variable `DB_PATH` used by the app
    import app as app_module  # adjust if your app module is different
    monkeypatch.setattr(app_module, "DB_PATH", test_db_path, raising=False)

    # Optional: restrict supported cities during tests
    if hasattr(app_module, "SUPPORTED_CITIES"):
        monkeypatch.setattr(app_module, "SUPPORTED_CITIES", {"Wroclaw"}, raising=False)

    yield flask_app

@pytest.fixture()
def client(app):
    app.config.update(TESTING=True)
    return app.test_client()

@pytest.fixture()
def today_iso():
    return date.today().
