import unittest
from unittest.mock import Mock, patch

from db_direct import DirectDbClient


class DirectDbConnectionTests(unittest.TestCase):
    def test_write_client_declares_read_write_transactions(self):
        connection = Mock()
        with patch("db_direct.psycopg2.connect", return_value=connection) as connect:
            result = DirectDbClient("postgresql://example.test/jobs")._connect()

        self.assertIs(result, connection)
        connect.assert_called_once()
        connection.set_session.assert_called_once_with(readonly=False)


if __name__ == "__main__":
    unittest.main()
