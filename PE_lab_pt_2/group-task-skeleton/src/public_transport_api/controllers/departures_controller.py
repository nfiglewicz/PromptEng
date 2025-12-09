from flask import Blueprint, jsonify

from public_transport_api.services.departures_service import get_closest_departures

departures_bp = Blueprint('departures', __name__, url_prefix='/public_transport/city/<string:city>/closest_departures')

@departures_bp.route("/", methods=["GET"])
def closest_departures(city):
    """
    The endpoint returns the closest departures of lines that bring the user closer to the destination.
	Lines that start in the opposite direction shall not be displayed.
	Departures are sorted by distance from start_coordinates in ascend-ing order (the closest first).
	The endpoint does not consider which line brings the user closer to the destination.

    Request Parameters:
        Path Parameters:
        - city (required): The city for the public transport search. Currently, on-ly "wroclaw" is supported.
        Query Parameters:
        - start_coordinates (required): The geolocation coordinates where the user wants to start the trip.
        - end_coordinates (required): The geolocation coordinates where the user wants to finish the trip.
        - start_time (optional, default: current time): The time at which the us-er starts the trip.
        - limit (optional, default: 5): The maximum number of departures to be returned.
    """
    # TODO handle request parameters and add the metadata. Include error handling.
    return jsonify(get_closest_departures())