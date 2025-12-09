import os
import sqlite3
from typing import List, Tuple, Dict, Any, Optional
from collections import defaultdict
import heapq

from .utils import (
    haversine_distance_m,
    extract_time_part_iso,
    combine_date_and_hms,
    gtfs_time_to_seconds,
    iso_day_start_and_seconds,
    day_start_plus_seconds_to_iso,
)


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

def compute_best_route(
    city: str,
    start: Tuple[float, float],
    dest: Tuple[float, float],
    start_time_iso: str,
    max_walk_m: float = 1000.0,
    walk_speed_m_s: float = 1.2,
) -> Optional[Dict[str, Any]]:
    """
    Compute an earliest-arrival route using GTFS data:
    - Walk from start coords to any stop within max_walk_m
    - Ride one or more trips (with transfers)
    - Walk from some stop to dest coords (within max_walk_m)
    Minimizes arrival time at destination.

    Returns a dict describing the route, or None if no route found.
    """
    conn = get_connection()
    cur = conn.cursor()

    start_lat, start_lon = start
    dest_lat, dest_lon = dest

    # 1. Load stops
    cur.execute("SELECT stop_id, stop_name, stop_lat, stop_lon FROM stops")
    stops_rows = cur.fetchall()
    if not stops_rows:
        return None

    stops: Dict[str, Dict[str, Any]] = {}
    for row in stops_rows:
        try:
            lat = float(row["stop_lat"])
            lon = float(row["stop_lon"])
        except (TypeError, ValueError):
            continue
        stops[row["stop_id"]] = {
            "stop_id": row["stop_id"],
            "name": row["stop_name"],
            "lat": lat,
            "lon": lon,
        }

    if not stops:
        return None

    # 2. Precompute walking candidates
    origin_candidates: List[Tuple[str, float]] = []  # (stop_id, dist_m)
    dest_walk: Dict[str, float] = {}  # stop_id -> dist_m

    for stop_id, info in stops.items():
        d_start = haversine_distance_m(start_lat, start_lon, info["lat"], info["lon"])
        if d_start <= max_walk_m:
            origin_candidates.append((stop_id, d_start))

        d_dest = haversine_distance_m(dest_lat, dest_lon, info["lat"], info["lon"])
        if d_dest <= max_walk_m:
            dest_walk[stop_id] = d_dest

    if not origin_candidates or not dest_walk:
        # Can't walk to/from any stop within max_walk_m
        return None

    # 3. Build transit edges: stop_id -> list of edges
    # Each edge: current stop -> next stop along a trip, with dep/arr times
    cur.execute(
        """
        SELECT trip_id,
               stop_id,
               stop_sequence,
               arrival_time,
               departure_time
        FROM stop_times
        ORDER BY trip_id, stop_sequence
        """
    )
    rows = cur.fetchall()
    edges_by_stop: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    prev_row = None
    for row in rows:
        if prev_row is None:
            prev_row = row
            continue

        if row["trip_id"] == prev_row["trip_id"]:
            # consecutive stops of the same trip
            from_stop_id = prev_row["stop_id"]
            to_stop_id = row["stop_id"]
            if from_stop_id not in stops or to_stop_id not in stops:
                prev_row = row
                continue

            try:
                dep_sec = gtfs_time_to_seconds(prev_row["departure_time"])
                arr_sec = gtfs_time_to_seconds(row["arrival_time"])
            except Exception:
                prev_row = row
                continue

            if arr_sec < dep_sec:
                # ignore weird backwards times
                prev_row = row
                continue

            edges_by_stop[from_stop_id].append(
                {
                    "trip_id": row["trip_id"],
                    "to_stop_id": to_stop_id,
                    "dep_sec": dep_sec,
                    "arr_sec": arr_sec,
                }
            )

        prev_row = row

    if not edges_by_stop:
        return None

    # 4. Earliest-arrival Dijkstra on stops
    day_start_dt, start_sec = iso_day_start_and_seconds(start_time_iso)

    INF = 10**15
    best_time: Dict[str, float] = {sid: INF for sid in stops.keys()}
    prev: Dict[str, Dict[str, Any]] = {}

    pq: List[Tuple[float, str]] = []

    # Initialize from walking to origin stops
    for stop_id, dist_m in origin_candidates:
        walk_sec = dist_m / walk_speed_m_s
        arrival_sec = start_sec + walk_sec
        if arrival_sec < best_time[stop_id]:
            best_time[stop_id] = arrival_sec
            prev[stop_id] = {
                "prev_stop_id": None,
                "trip_id": None,
                "dep_time_sec": start_sec,
                "arr_time_sec": arrival_sec,
                "mode": "walk_start",
                "walk_distance_m": dist_m,
            }
            heapq.heappush(pq, (arrival_sec, stop_id))

    best_dest_total_sec = INF
    best_dest_stop_id: Optional[str] = None

    while pq:
        current_time, stop_id = heapq.heappop(pq)
        if current_time > best_time[stop_id] + 1e-6:
            continue

        # Could this stop walk us to destination?
        if stop_id in dest_walk:
            walk_to_dest_sec = dest_walk[stop_id] / walk_speed_m_s
            total_arrival_sec = current_time + walk_to_dest_sec
            if total_arrival_sec < best_dest_total_sec:
                best_dest_total_sec = total_arrival_sec
                best_dest_stop_id = stop_id

        # Early stop: all remaining labels are later than best found destination
        if current_time > best_dest_total_sec:
            break

        # Transit edges
        for edge in edges_by_stop.get(stop_id, []):
            dep_sec = edge["dep_sec"]
            arr_sec = edge["arr_sec"]

            # Can only catch trips that depart after we arrive at the stop
            if dep_sec < current_time - 1e-6:
                continue

            if arr_sec < best_time[edge["to_stop_id"]]:
                best_time[edge["to_stop_id"]] = arr_sec
                prev[edge["to_stop_id"]] = {
                    "prev_stop_id": stop_id,
                    "trip_id": edge["trip_id"],
                    "dep_time_sec": dep_sec,
                    "arr_time_sec": arr_sec,
                    "mode": "ride",
                }
                heapq.heappush(pq, (arr_sec, edge["to_stop_id"]))

    if best_dest_stop_id is None or best_dest_total_sec >= INF:
        return None

    # 5. Reconstruct path (stops + trips)
    segments: List[Dict[str, Any]] = []
    cur_stop_id = best_dest_stop_id

    while True:
        step = prev.get(cur_stop_id)
        if not step:
            break

        seg = {
            "to_stop_id": cur_stop_id,
            **step,
        }
        segments.append(seg)

        if step["prev_stop_id"] is None:
            break
        cur_stop_id = step["prev_stop_id"]

    segments.reverse()
    if not segments:
        return None

    # 6. Group segments into legs (walk + rides with transfers)
    # Load trip metadata (route_id, headsign)
    cur.execute("SELECT trip_id, route_id, trip_headsign FROM trips")
    trip_meta_rows = cur.fetchall()
    trip_meta = {
        r["trip_id"]: {
            "route_id": r["route_id"],
            "trip_headsign": r["trip_headsign"],
        }
        for r in trip_meta_rows
    }

    legs: List[Dict[str, Any]] = []

    # First leg: walking from start coords?
    if segments[0]["mode"] == "walk_start":
        first_seg = segments[0]
        first_stop = stops[first_seg["to_stop_id"]]

        legs.append(
            {
                "type": "walk",
                "from": {
                    "coordinates": {
                        "latitude": start_lat,
                        "longitude": start_lon,
                    }
                },
                "to": {
                    "stop_id": first_stop["stop_id"],
                    "name": first_stop["name"],
                    "coordinates": {
                        "latitude": first_stop["lat"],
                        "longitude": first_stop["lon"],
                    },
                },
                "distance_m": round(first_seg["walk_distance_m"], 1),
                "start_time": day_start_plus_seconds_to_iso(day_start_dt, first_seg["dep_time_sec"]),
                "arrival_time": day_start_plus_seconds_to_iso(day_start_dt, first_seg["arr_time_sec"]),
            }
        )
        seg_index_start = 1
    else:
        seg_index_start = 0

    # Ride legs (group consecutive segments with same trip_id)
    current_leg = None
    for seg in segments[seg_index_start:]:
        if seg["mode"] != "ride":
            continue

        trip_id = seg["trip_id"]
        prev_stop_id = seg["prev_stop_id"]
        to_stop_id = seg["to_stop_id"]

        prev_stop = stops[prev_stop_id]
        to_stop = stops[to_stop_id]

        if current_leg and current_leg["trip_id"] == trip_id:
            # Extend existing leg
            current_leg["to"] = {
                "stop_id": to_stop["stop_id"],
                "name": to_stop["name"],
                "coordinates": {
                    "latitude": to_stop["lat"],
                    "longitude": to_stop["lon"],
                },
            }
            current_leg["arrival_time"] = day_start_plus_seconds_to_iso(
                day_start_dt, seg["arr_time_sec"]
            )
            current_leg["num_stops"] += 1
        else:
            # Start new ride leg
            meta = trip_meta.get(trip_id, {})
            new_leg = {
                "type": "ride",
                "trip_id": trip_id,
                "route_id": meta.get("route_id"),
                "trip_headsign": meta.get("trip_headsign"),
                "from": {
                    "stop_id": prev_stop["stop_id"],
                    "name": prev_stop["name"],
                    "coordinates": {
                        "latitude": prev_stop["lat"],
                        "longitude": prev_stop["lon"],
                    },
                },
                "to": {
                    "stop_id": to_stop["stop_id"],
                    "name": to_stop["name"],
                    "coordinates": {
                        "latitude": to_stop["lat"],
                        "longitude": to_stop["lon"],
                    },
                },
                "boarding_time": day_start_plus_seconds_to_iso(
                    day_start_dt, seg["dep_time_sec"]
                ),
                "arrival_time": day_start_plus_seconds_to_iso(
                    day_start_dt, seg["arr_time_sec"]
                ),
                "num_stops": 1,
            }
            legs.append(new_leg)
            current_leg = new_leg

    # Final walking leg from last stop to destination
    last_stop_id = best_dest_stop_id
    last_arrival_at_stop_sec = best_time[last_stop_id]
    last_stop = stops[last_stop_id]
    last_to_dest_m = dest_walk[last_stop_id]
    last_to_dest_sec = last_to_dest_m / walk_speed_m_s

    legs.append(
        {
            "type": "walk",
            "from": {
                "stop_id": last_stop["stop_id"],
                "name": last_stop["name"],
                "coordinates": {
                    "latitude": last_stop["lat"],
                    "longitude": last_stop["lon"],
                },
            },
            "to": {
                "coordinates": {
                    "latitude": dest_lat,
                    "longitude": dest_lon,
                }
            },
            "distance_m": round(last_to_dest_m, 1),
            "start_time": day_start_plus_seconds_to_iso(day_start_dt, last_arrival_at_stop_sec),
            "arrival_time": day_start_plus_seconds_to_iso(
                day_start_dt, best_dest_total_sec
            ),
        }
    )

    route = {
        "start_time": start_time_iso,
        "arrival_time": day_start_plus_seconds_to_iso(day_start_dt, best_dest_total_sec),
        "total_travel_time_sec": int(best_dest_total_sec - start_sec),
        "legs": legs,
    }
    return route
