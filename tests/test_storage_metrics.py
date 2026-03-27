from __future__ import annotations

import sys
import types
import unittest

if "psycopg" not in sys.modules:
    psycopg_stub = types.ModuleType("psycopg")
    psycopg_stub.Connection = object
    psycopg_stub.Cursor = object
    psycopg_stub.connect = lambda *args, **kwargs: None

    psycopg_types = types.ModuleType("psycopg.types")
    psycopg_types_json = types.ModuleType("psycopg.types.json")

    class _Json:
        def __init__(self, value):
            self.value = value

    psycopg_types_json.Json = _Json
    sys.modules["psycopg"] = psycopg_stub
    sys.modules["psycopg.types"] = psycopg_types
    sys.modules["psycopg.types.json"] = psycopg_types_json

from app import storage


class _DummyCursor:
    def __init__(self, executed):
        self.executed = executed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params):
        self.executed.append((query, params))


class _DummyConn:
    def __init__(self):
        self.executed = []

    def cursor(self):
        return _DummyCursor(self.executed)


class StorageMetricsTests(unittest.TestCase):
    def test_extract_clan_games_points_reads_games_champion_achievement(self):
        player = {
            "achievements": [
                {"name": "Gold Grab", "value": 123},
                {"name": "Games Champion", "value": 4000},
            ]
        }

        self.assertEqual(storage.extract_clan_games_points(player), 4000)

    def test_player_snapshots_keep_distinct_clan_games_values_across_resets(self):
        conn = _DummyConn()
        active_month_player = {
            "tag": "#P1",
            "clan": {"tag": "#CLAN"},
            "townHallLevel": 16,
            "trophies": 5200,
            "warStars": 1000,
            "donations": 10,
            "donationsReceived": 5,
            "clanCapitalContributions": 9000,
            "achievements": [{"name": "Games Champion", "value": 4000}],
        }
        reset_month_player = {
            **active_month_player,
            "achievements": [{"name": "Games Champion", "value": 0}],
        }

        storage.insert_player_snapshot(conn, active_month_player)
        storage.insert_player_snapshot(conn, reset_month_player)

        self.assertEqual(len(conn.executed), 2)
        first_params = conn.executed[0][1]
        second_params = conn.executed[1][1]
        self.assertEqual(first_params[10], 4000)
        self.assertEqual(second_params[10], 0)


if __name__ == "__main__":
    unittest.main()
