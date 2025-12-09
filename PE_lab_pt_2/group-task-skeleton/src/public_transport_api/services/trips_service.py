import sqlite3


def get_trip_details(trip_id):
    # FIXME This is a mock implementation and should be replaced with actual database queries.
    conn = sqlite3.connect('trips.sqlite')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT route_id, trip_headsign FROM main.trips LIMIT 1
    """)
    first_trip_row = cursor.fetchone()

    conn.close()

    if not first_trip_row:
        return None

    route_id, trip_headsign = first_trip_row

    mocked_stop_details = [
        {
            "name": "Mock Stop A",
            "coordinates": {
                "latitude": 40.7128,
                "longitude": -74.0060
            },
            "arrival_time": "2025-04-02T08:00:00Z",
            "departure_time": "2025-04-02T08:05:00Z"
        },
        {
            "name": "Mock Stop B",
            "coordinates": {
                "latitude": 40.7580,
                "longitude": -73.9855
            },
            "arrival_time": "2025-04-02T08:15:00Z",
            "departure_time": "2025-04-02T08:20:00Z"
        },
        {
            "name": "Mock Stop C",
            "coordinates": {
                "latitude": 40.7850,
                "longitude": -73.9650
            },
            "arrival_time": "2025-04-02T08:30:00Z",
            "departure_time": "2025-04-02T08:35:00Z"
        }
    ]

    return {
        "trip_id": trip_id,
        "route_id": route_id,
        "trip_headsign": trip_headsign,
        "stops": mocked_stop_details
    }
