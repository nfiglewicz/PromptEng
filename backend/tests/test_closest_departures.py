
# tests/test_closest_departures.py
from urllib.parse import urlencode

BASE = "/public_transport/city/{city}/closest_departures"

def test_closest_departures_success(client, today_iso):
    city = "Wroclaw"
    params = {
        "start_coordinates": "51.1079,17.0385",  # near Rynek
        "end_coordinates": "51.1141,17.0301",    # toward Nadodrze direction-ish
        "start_time": f"{today_iso}T08:30:00Z",
        "limit": 5,
    }
    url = BASE.format(city=city) + "?" + urlencode(params)
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "metadata" in data and "departures" in data

    deps = data["departures"]
    assert isinstance(deps, list)
    assert 1 <= len(deps) <= 5

    first = deps[0]
    # Basic schema checks
    assert {"trip_id", "route_id", "trip_headsign", "stop", "arrival_time", "departure_time"} <= set(first.keys())
    assert {"name", "coordinates"} <= set(first["stop"].keys())
    assert {"latitude", "longitude"} <= set(first["stop"]["coordinates"].keys())

def test_closest_departures_limit_respected(client, today_iso):
    city = "Wroclaw"
    params = {
        "start_coordinates": "51.1079,17.0385",
        "end_coordinates": "51.1141,17.0301",
        "start_time": f"{today_iso}T08:30:00Z",
        "limit": 1,
    }
    resp = client.get(BASE.format(city=city), query_string=params)
    assert resp.status_code == 200
    deps = resp.get_json()["departures"]
    assert len(deps) == 1

def test_closest_departures_missing_params(client):
    city = "Wroclaw"
    # Missing end_coordinates
    params = { "start_coordinates": "51.1079,17.0385" }
    resp = client.get(BASE.format(city=city), query_string=params)
    assert resp.status_code == 400
    payload = resp.get_json()
    assert payload.get("error") == "Bad Request"

def test_closest_departures_invalid_coords(client, today_iso):
    city = "Wroclaw"
    params = {
        "start_coordinates": "INVALID",
        "end_coordinates": "51.1141,17.0301",
        "start_time": f"{today_iso}T08:30:00Z",
    }
    resp = client.get(BASE.format(city=city), query_string=params)
    assert resp.status_code == 400

def test_closest_departures_unsupported_city(client, today_iso):
    city = "Paris"
    params = {
        "start_coordinates": "51.1079,17.0385",
        "end_coordinates": "51.1141,17.0301",
        "start_time": f"{today_iso}T08:30:00Z",
    }
    resp = client.get(BASE.format(city=city), query_string=params)
    assert resp.status_code    assert resp.status_code == 404
    payload = resp.get_json()
