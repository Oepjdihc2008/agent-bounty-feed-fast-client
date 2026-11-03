import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from abf import ABFClient, format_table


class TestABFClient(unittest.TestCase):
    def setUp(self):
        self.client = ABFClient(timeout=10)

    def test_earn_now(self):
        data = self.client.get_earn_now()
        self.assertIn("name", data)
        self.assertIn("items", data)
        self.assertIsInstance(data["items"], list)

    def test_mcp_list_bounties(self):
        res = self.client.list_bounties(limit=2)
        self.assertIn("items", res)
        self.assertIsInstance(res["items"], list)

    def test_mcp_feed_stats(self):
        res = self.client.get_feed_stats()
        self.assertIn("stats", res)
        self.assertIn("items", res["stats"])

    def test_format_table(self):
        headers = ["Col A", "Col B"]
        rows = [["Val1", "Val2"], ["LongerVal1", "V2"]]
        table = format_table(rows, headers)
        self.assertIn("Col A", table)
        self.assertIn("LongerVal1", table)


if __name__ == "__main__":
    unittest.main()
