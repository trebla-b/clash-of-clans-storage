from __future__ import annotations

import os
import sys
from types import SimpleNamespace
import types
import unittest
from unittest.mock import call, patch

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")

    class _RequestsSession:
        def __init__(self):
            self.headers = {}

        def get(self, *args, **kwargs):
            raise RuntimeError("requests.Session.get should not be called in this test")

    requests_stub.Session = _RequestsSession
    sys.modules["requests"] = requests_stub

if "psycopg" not in sys.modules:
    psycopg_stub = types.ModuleType("psycopg")
    psycopg_stub.Connection = object
    psycopg_stub.Cursor = object

    def _connect(*args, **kwargs):
        raise RuntimeError("psycopg.connect should not be called in this test")

    psycopg_stub.connect = _connect

    psycopg_types = types.ModuleType("psycopg.types")
    psycopg_types_json = types.ModuleType("psycopg.types.json")

    class _Json:
        def __init__(self, value):
            self.value = value

    psycopg_types_json.Json = _Json
    sys.modules["psycopg"] = psycopg_stub
    sys.modules["psycopg.types"] = psycopg_types
    sys.modules["psycopg.types.json"] = psycopg_types_json

if "yaml" not in sys.modules:
    yaml_stub = types.ModuleType("yaml")
    yaml_stub.safe_load = lambda value: {}
    sys.modules["yaml"] = yaml_stub

from app import fetch_once


class _DummyConn:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def commit(self) -> None:
        return None

    def transaction(self):
        return self


class FetchOnceMainTests(unittest.TestCase):
    @patch.dict(os.environ, {"API_KEY": "test-api-key"}, clear=False)
    @patch("app.fetch_once.storage")
    @patch("app.fetch_once.load_config")
    @patch("app.fetch_once.ClashOfClansClient")
    def test_main_keeps_raid_loot_in_capital_tables_only(self, client_cls, load_config, storage):
        config = SimpleNamespace(
            api_base_url="https://api.example.test/v1",
            request_timeout_seconds=20,
            clan_id="#CLAN",
            db_url="postgresql://example",
        )
        load_config.return_value = config

        client = client_cls.return_value
        clan = {
            "tag": "#CLAN",
            "memberList": [
                {"tag": "#P1"},
                {"tag": "#P2"},
            ],
        }
        players = [
            {"tag": "#P1", "name": "Alpha", "clan": {"tag": "#CLAN"}},
            {"tag": "#P2", "name": "Beta", "clan": {"tag": "#CLAN"}},
        ]
        capital_raid_payload = {
            "items": [
                {
                    "startTime": "20260313T070000.000Z",
                    "members": [
                        {"tag": "#P1", "capitalResourcesLooted": 32100},
                        {"tag": "#P2", "capitalResourcesLooted": 28750},
                    ],
                }
            ]
        }

        client.get_clan.return_value = clan
        client.get_player.side_effect = players
        client.get_current_war.return_value = None
        client.get_current_league_group.return_value = None
        client.get_capital_raid_seasons.return_value = capital_raid_payload

        conn = _DummyConn()
        storage.connect.return_value = conn
        storage.get_finalized_war_ids.return_value = set()

        result = fetch_once.main()

        self.assertEqual(result, 0)
        self.assertEqual(
            storage.insert_player_snapshot.call_args_list,
            [call(conn, players[0]), call(conn, players[1])],
        )
        storage.upsert_capital_raid_seasons.assert_called_once_with(
            conn,
            clan_tag="#CLAN",
            payload=capital_raid_payload,
        )


if __name__ == "__main__":
    unittest.main()
