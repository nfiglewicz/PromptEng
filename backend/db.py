import os
import sqlite3
from typing import List, Tuple, Dict, Any, Optional

from .utils import haversine_distance_m, extract_time_part_iso, combine_date_and_hms

# Path can be overridden via environment variable, to make tests easier
DEFAULT_DB_PATH = os.environ.get("GTFS_DB_PATH") or os.path.join(os.path.dirname(__file__), "..", "data", "gtfs.sqlite")


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DEFAULT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _fetch_candidate_stops(conn, start_lat: float, start_lon: float, radius_m: float):
    cur = conn.cursor()
    cur.execute("""SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops""")
    rows = cur.fetchall()
    candidates = []
    for row in rows:
        try:
            lat = float(row["stop_lat"])
            lon = float(row["stop_lon"])
        except (TypeError, ValueError):
            continue
        dist = haversine_distance_m(start_lat, start_lon, lat, lon)
        if dist <= radius_m:
            candidates.append({
                "stop_id": row["stop_id"],
                "name": row["stop_name"],
                "latitude": lat,
                "longitude": lon,
                "distance_m": dist,
            })
    candidates.sort(key=lambda x: x["distance_m"])
    return candidates


def _is_trip_towards_destination(conn, trip_id: str, current_stop_id: str, current_lat: float, current_lon: float,
                                 dest_lat: float, dest_lon: float) -> bool:
    """
    Approximate direction check: if the next stop in the trip is closer to the destination
    than the current stop, treat it as going in the right direction.
    """
    cur = conn.cursor()
    # Get sequence of current stop
    cur.execute(
        "SELECT stop_sequence FROM stop_times WHERE trip_id = ? AND stop_id = ? ORDER BY stop_sequence ASC LIMIT 1",
        (trip_id, current_stop_id),
    )
    row = cur.fetchone()
    if not row:
        return True  # can't determine, don't filter out
    seq = row["stop_sequence"]

    # Next stop
    cur.execute(
        """SELECT st.stop_id, s.stop_lat, s.stop_lon
               FROM stop_times st
               JOIN stops s ON s.stop_id = st.stop_id
               WHERE st.trip_id = ? AND st.stop_sequence > ?
               ORDER BY st.stop_sequence ASC
               LIMIT 1""",
        (trip_id, seq),
    )
    next_row = cur.fetchone()
    if not next_row:
        return True

    current_to_dest = haversine_distance_m(current_lat, current_lon, dest_lat, dest_lon)
    next_to_dest = haversine_distance_m(float(next_row["stop_lat"]), float(next_row["stop_lon"]), dest_lat, dest_lon)
    return next_to_dest <= current_to_dest


def query_closest_departures(city: str,
                             start: Tuple[float, float],
                             dest: Tuple[float, float],
                             start_time_iso: str,
                             limit: int,
                             radius_m: float) -> List[Dict[str, Any]]:
    conn = get_connection()
    start_lat, start_lon = start
    dest_lat, dest_lon = dest

    time_part = extract_time_part_iso(start_time_iso).strftime("%H:%M:%S")

    candidate_stops = _fetch_candidate_stops(conn, start_lat, start_lon, radius_m)
    results: List[Dict[str, Any]] = []
    cur = conn.cursor()

    for stop in candidate_stops:
        if len(results) >= limit:
            break

        cur.execute(
            """SELECT st.trip_id,
                          st.arrival_time,
                          st.departure_time,
                          st.stop_id,
                          st.stop_sequence,
                          t.route_id,
                          t.trip_headsign
                   FROM stop_times st
                   JOIN trips t ON t.trip_id = st.trip_id
                   WHERE st.stop_id = ?
                     AND st.departure_time >= ?
                   ORDER BY st.departure_time ASC
                   LIMIT 3""",
            (stop["stop_id"], time_part),
        )
        rows = cur.fetchall()
        for row in rows:
            if len(results) >= limit:
                break

            # Direction filter
            if not _is_trip_towards_destination(
                conn,
                row["trip_id"],
                row["stop_id"],
                stop["latitude"],
                stop["longitude"],
                dest_lat,
                dest_lon,
            ):
                continue

            arrival_iso = combine_date_and_hms(start_time_iso, row["arrival_time"])
            departure_iso = combine_date_and_hms(start_time_iso, row["departure_time"])

            results.append({
                "trip_id": row["trip_id"],
                "route_id": row["route_id"],
                "trip_headsign": row["trip_headsign"],
                "stop": {
                    "name": stop["name"],
                    "coordinates": {
                        "latitude": stop["latitude"],
                        "longitude": stop["longitude"],
                    },
                    "arrival_time": arrival_iso,
                    "departure_time": departure_iso,
                    "walking_distance_m": round(stop["distance_m"], 1),
                },
            })

    return results


def get_trip_details(city: str, trip_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT trip_id, route_id, trip_headsign FROM trips WHERE trip_id = ?", (trip_id,))
    trip_row = cur.fetchone()
    if not trip_row:
        return None

    cur.execute(
        """SELECT s.stop_name,
                      s.stop_lat,
                      s.stop_lon,
                      st.arrival_time,
                      st.departure_time
               FROM stop_times st
               JOIN stops s ON s.stop_id = st.stop_id
               WHERE st.trip_id = ?
               ORDER BY st.stop_sequence ASC""",
        (trip_id,),
    )
    stops = []
    rows = cur.fetchall()
    for row in rows:
        stops.append({
            "name": row["stop_name"],
            "coordinates": {
                "latitude": float(row["stop_lat"]),
                "longitude": float(row["stop_lon"]),
            },
            "arrival_time": row["arrival_time"],
            "departure_time": row["departure_time"],
        })

    return {
        "trip_id": trip_row["trip_id"],
        "route_id": trip_row["route_id"],
        "trip_headsign": trip_row["trip_headsign"],
        "stops": stops,
    }
