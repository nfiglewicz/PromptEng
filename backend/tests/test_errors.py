
# tests/test_errors.py
import app as app_module  # change if your module name differs

def test_closest_departures_internal_error(client, monkeypatch):
    # Monkeypatch get_db to raise
    def boom():
        raise RuntimeError("boom")
    monkeypatch.setattr(app_module, "get_db", boom, raising=True)

    city = "Wroclaw"
    url = f"/public_transport/city/{city}/closest_departures"
    resp = client.get(url, query_string={
        "start_coordinates": "51.1079,17.0385",
        "end_coordinates": "51.1141,17.0301",
        "start_time": "2025-04-02T08:30:00Z",
        "limit": 3,
    })

    assert resp.status_code == 500
    payload = resp.get_json()
    assert payload.get("error") == "Internal Server Error"

def test_trip_details_internal_error(client, monkeypatch):
    def boom():
        raise RuntimeError("boom")
    monkeypatch.setattr(app_module, "get_db", boom, raising=True)

    city = "Wroclaw"
    resp = client.get(f"/public_transport/city/{city}/trip/TRIP_002")
    assert resp.status_code == 500
