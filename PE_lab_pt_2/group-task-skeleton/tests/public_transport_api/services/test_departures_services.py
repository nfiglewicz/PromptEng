import unittest
from unittest.mock import patch


class TestDeparturesService(unittest.TestCase):

    # TODO replace with actual tests implementation
    @patch('public_transport_api.services.departures_service.sqlite3.connect')
    def test_get_closest_departures_success(self, mock_connect):
        pass

if __name__ == '__main__':
    unittest.main()
