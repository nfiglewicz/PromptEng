import unittest
from unittest.mock import patch




class TestGetTripDetails(unittest.TestCase):
    # TODO replace with actual tests implementation
    @patch('public_transport_api.services.trips_service.sqlite3.connect')
    def test_get_trip_details_success(self, mock_connect):
        pass

if __name__ == '__main__':
    unittest.main()
