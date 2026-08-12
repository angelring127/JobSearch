import unittest
from unittest.mock import MagicMock, Mock, patch

from db_direct import DirectDbClient


class DirectDbConnectionTests(unittest.TestCase):
    def test_write_client_declares_read_write_transactions(self):
        connection = Mock()
        with patch("db_direct.psycopg2.connect", return_value=connection) as connect:
            result = DirectDbClient("postgresql://example.test/jobs")._connect()

        self.assertIs(result, connection)
        connect.assert_called_once()
        connection.set_session.assert_called_once_with(readonly=False)

    def test_recent_source_item_ids_filters_invalid_external_ids(self):
        client = DirectDbClient.__new__(DirectDbClient)
        connection = MagicMock()
        managed_connection = connection.__enter__.return_value
        cursor = managed_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = [
            {"external_id": "405995"},
            {"external_id": "not-numeric"},
            {"external_id": None},
        ]
        client._connect = Mock(return_value=connection)

        result = client.get_recent_source_item_ids("ourvancouver", retention_days=14)

        self.assertEqual(result, {405995})
        query = " ".join(cursor.execute.call_args.args[0].split())
        self.assertIn("COALESCE(posted_at, created_at)", query)
        self.assertEqual(cursor.execute.call_args.args[1], ("ourvancouver", 14))

    def test_recent_source_item_ids_rejects_invalid_retention(self):
        client = DirectDbClient.__new__(DirectDbClient)

        with self.assertRaisesRegex(ValueError, "at least 1"):
            client.get_recent_source_item_ids("ourvancouver", retention_days=0)


if __name__ == "__main__":
    unittest.main()
