import os
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_from_directory

from .db import query_closest_departures, get_trip_details

# static_folder points to ../frontend
app = Flask(
    __name__,
    static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"),
    static_url_path=""
)

@app.route("/")
def index():
    # Serve frontend/index.html
    return send_from_directory(app.static_folder, "index.html")


def _parse_coordinates(value: str):
    if not value:
        return None
    try:
        lat_s, lon_s = value.split(",")
        return float(lat_s.strip()), float(lon_s.strip())
    except Exception:
        return None


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/public_transport/city/<city>/closest_departures")
def closest_departures(city):
    if city.lower() != "wroclaw":
        return jsonify({"error": "City not supported"}), 404

    start_coordinates = request.args.get("start_coordinates")
    end_coordinates = request.args.get("end_coordinates")
    start_time = request.args.get("start_time")
    limit = request.args.get("limit", "5")
    radius_m = request.args.get("radius_m", "1000")

    start = _parse_coordinates(start_coordinates)
    end = _parse_coordinates(end_coordinates)

    if not start or not end:
        return (
            jsonify(
                {
                    "error": "start_coordinates and end_coordinates are required in 'lat,lon' format",
                    "example": "51.1079,17.0385",
                }
            ),
            400,
        )

    try:
        limit = int(limit)
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    try:
        radius_m = float(radius_m)
    except ValueError:
        return jsonify({"error": "radius_m must be a number (meters)"}), 400

    if start_time is None:
        start_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    departures = query_closest_departures(city, start, end, start_time, limit, radius_m)

    metadata = {
        "self": request.path + "?" + request.query_string.decode("utf-8"),
        "city": city,
        "query_parameters": {
            "start_coordinates": start_coordinates,
            "end_coordinates": end_coordinates,
            "start_time": start_time,
            "limit": limit,
            "radius_m": radius_m,
        },
    }

    return jsonify({"metadata": metadata, "departures": departures})


@app.route("/public_transport/city/<city>/trip/<trip_id>")
def trip_details(city, trip_id):
    if city.lower() != "wroclaw":
        return jsonify({"error": "City not supported"}), 404

    details = get_trip_details(city, trip_id)
    if details is None:
        return jsonify({"error": "Trip not found"}), 404

    metadata = {
        "self": request.path,
        "city": city,
        "query_parameters": {
            "trip_id": trip_id,
        },
    }

    return jsonify({"metadata": metadata, "trip_details": details})


if __name__ == "__main__":
    app.run(debug=True)
