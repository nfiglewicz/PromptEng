
# tests/test_trip_details.py
def test_trip_details_success(client):
    city = "Wroclaw"
    trip_id = "TRIP_002"
    url = f"/public_transport/city/{city}/trip/{trip_id}"
    resp = client.get(url)
    assert resp.status_code == 200

    data = resp.get_json()
    assert "metadata" in data and "trip_details" in data
    td = data["trip_details"]
    assert td["trip_id"] == trip_id
    assert "route_id" in td
    assert "trip_headsign" in td
    assert isinstance(td.get("stops"), list)
    assert len(td["stops"]) >= 1

    # Schema of each stop
    s0 = td["stops"][0]
    assert {"name", "coordinates", "arrival_time", "departure_time"} <= set(s0.keys())
    assert {"latitude", "longitude"} <= set(s0["coordinates"].keys())

    # Ordered by stop_sequence (if provided in response)
    sequences = [s.get("sequence", i) for i, s in enumerate(td["stops"], start=1)]
    assert sequences == sorted(sequences)

def test_trip_details_not_found(client):
    city = "Wroclaw"
    trip_id = "TRIP_NON_EXISTENT"
    resp = client.get(f"/public_transport/city/{city}/trip/{trip_id}")
    assert resp.status_code == 404
    payload    payload = resp.get_json()
