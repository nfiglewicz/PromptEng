import os
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest

# Ensure we import the local package correctly
from backend.app import app as flask_app
from backend.db import DEFAULT_DB_PATH


@pytest.fixture(scope="module")
def test_db_path():
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite")
    tmp.close()
    conn = sqlite3.connect(tmp.name)
    cur = conn.cursor()

    # Minimal schema for tests
    cur.executescript(
        """            CREATE TABLE stops (
            stop_id TEXT PRIMARY KEY,
            stop_name TEXT,
            stop_lat REAL,
            stop_lon REAL
        );
        CREATE TABLE trips (
            trip_id TEXT PRIMARY KEY,
            route_id TEXT,
            trip_headsign TEXT
        );
        CREATE TABLE stop_times (
            trip_id TEXT,
            arrival_time TEXT,
            departure_time TEXT,
            stop_id TEXT,
            stop_sequence INTEGER
        );
        """
    )

    # Test data: simple two-stop trip
    cur.execute(
        "INSERT INTO stops(stop_id, stop_name, stop_lat, stop_lon) VALUES (?,?,?,?)",
        ("STOP_A", "Stop A", 51.1079, 17.0385),
    )
    cur.execute(
        "INSERT INTO stops(stop_id, stop_name, stop_lat, stop_lon) VALUES (?,?,?,?)",
        ("STOP_B", "Stop B", 51.11, 17.05),
    )

    cur.execute(
        "INSERT INTO trips(trip_id, route_id, trip_headsign) VALUES (?,?,?)",
        ("TRIP_1", "A", "To B"),
    )

    cur.execute(
        "INSERT INTO stop_times(trip_id, arrival_time, departure_time, stop_id, stop_sequence) VALUES (?,?,?,?,?)",
        ("TRIP_1", "08:00:00", "08:01:00", "STOP_A", 1),
    )
    cur.execute(
        "INSERT INTO stop_times(trip_id, arrival_time, departure_time, stop_id, stop_sequence) VALUES (?,?,?,?,?)",
        ("TRIP_1", "08:10:00", "08:11:00", "STOP_B", 2),
    )

    conn.commit()
    conn.close()

    # Point the backend to this DB
    os.environ["GTFS_DB_PATH"] = tmp.name
    return tmp.name


@pytest.fixture()
def client(test_db_path):
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json["status"] == "ok"


def test_closest_departures_basic(client):
    now_iso = datetime(2025, 4, 2, 7, 59, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    resp = client.get(
        "/public_transport/city/Wroclaw/closest_departures",
        query_string={
            "start_coordinates": "51.1079,17.0385",
            "end_coordinates": "51.11,17.05",
            "start_time": now_iso,
            "limit": 1,
            "radius_m": 1000,
        },
    )
    assert resp.status_code == 200
    data = resp.json
    assert "departures" in data
    assert len(data["departures"]) == 1
    dep = data["departures"][0]
    assert dep["trip_id"] == "TRIP_1"
    assert dep["route_id"] == "A"
    assert dep["stop"]["name"] == "Stop A"


def test_trip_details(client):
    resp = client.get("/public_transport/city/Wroclaw/trip/TRIP_1")
    assert resp.status_code == 200
    data = resp.json
    details = data["trip_details"]
    assert details["trip_id"] == "TRIP_1"
    assert len(details["stops"]) == 2
    assert details["stops"][0]["name"] == "Stop A"
