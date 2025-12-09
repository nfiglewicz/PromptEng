from flask import Blueprint, jsonify

# Adjust import path based on your project structure
from public_transport_api.services.trips_service import get_trip_details

trips_bp = Blueprint('trips', __name__, url_prefix='/public_transport/city/<string:city>/trip')

@trips_bp.route("/<string:trip_id>", methods=["GET"])
def handle_trip_details(city, trip_id):
    """
    Retrieves details about a specific trip, including its route, headsign, and stop details.

    Endpoint:
        GET /public_transport/city/<city>/trip/<trip_id>

    Parameters:
        Path Parameters:
        - city (str): Specifies the city for which trip details are requested. Currently, only "wroclaw" is supported.
        - trip_id (str): The unique identifier of the trip whose details need to be retrieved.

    Returns:
        JSON response containing:
        - metadata: Information about the request, including the URL and query parameters.
        - trip_details: Details of the trip, including trip_id, route_id, trip_headsign, and a list of stops with their names, coordinates, arrival times, and departure times.

    Errors:
        - 400 Bad Request: If the city is not "wroclaw".
        - 404 Not Found: If the trip with the specified trip_id is not found.

    Example Response:
    {
        "metadata": {
            "self": "/public_transport/city/wroclaw/trip/3_14613060",
            "city": "wroclaw",
            "trip_id": "3_14613060"
        },
        "trip_details": {
            "trip_id": "3_14613060",
            "route_id": "A",
            "trip_headsign": "KRZYKI",
            "stops": [
                {
                    "name": "Plac Grunwaldzki",
                    "coordinates": {
                        "latitude": 51.1092,
                        "longitude": 17.0415
                    },
                    "arrival_time": "2025-04-02T08:34:00Z",
                    "departure_time": "2025-04-02T08:35:00Z"
                },
                {
                    "name": "Renoma",
                    "coordinates": {
                        "latitude": 51.1040,
                        "longitude": 17.0280
                    },
                    "arrival_time": "2025-04-02T08:39:00Z",
                    "departure_time": "2025-04-02T08:40:00Z"
                },
                {
                    "name": "Dominikański",
                    "coordinates": {
                        "latitude": 51.1099,
                        "longitude": 17.0335
                    },
                    "arrival_time": "2025-04-02T08:44:00Z",
                    "departure_time": "2025-04-02T08:45:00Z"
                }
            ]
        }
    """
    # TODO handle the city and the metadata. Add also error handling (i.e.: 404)
    return jsonify(get_trip_details(trip_id))