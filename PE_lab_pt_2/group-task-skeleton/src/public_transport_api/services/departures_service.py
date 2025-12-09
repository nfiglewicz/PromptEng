import sqlite3


def get_closest_departures():
    """
    FIXME this is a mock version. You need to implement the correct logic
    """
    conn = None
    try:
        conn = sqlite3.connect("trips.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops LIMIT 1;"
        cursor.execute(query)
        first_stop_row = cursor.fetchone()

        mock_departures = []

        if first_stop_row:
            mock_departure = {
                "trip_id": "mock_trip_001",
                "route_id": "mock_route_A",
                "trip_headsign": first_stop_row['stop_name'],
                "stop": {
                    "id": first_stop_row['stop_id'],
                    "name": first_stop_row['stop_name'],
                    "coordinates": {
                        "latitude": float(first_stop_row['stop_lat']),
                        "longitude": float(first_stop_row['stop_lon'])
                    },
                    "arrival_time": "10:00:00",
                    "departure_time": "10:00:30"
                },
                "distance_start_to_stop": 123.45,
                "debug_dist_stop_to_end": 543.21
            }
            mock_departures.append(mock_departure)

        return mock_departures

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []
    finally:
        if conn:
            conn.close()
