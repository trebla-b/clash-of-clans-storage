from __future__ import annotations

import sys
import types
import unittest

if "flask" not in sys.modules:
    flask_stub = types.ModuleType("flask")

    class _Flask:
        def __init__(self, name):
            self.name = name

        def get(self, _path):
            def decorator(fn):
                return fn

            return decorator

    flask_stub.Flask = _Flask
    flask_stub.abort = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("abort should not be called"))
    flask_stub.jsonify = lambda value: value
    flask_stub.request = types.SimpleNamespace(args={})
    sys.modules["flask"] = flask_stub

if "psycopg" not in sys.modules:
    psycopg_stub = types.ModuleType("psycopg")
    psycopg_stub.Connection = object
    psycopg_stub.Cursor = object
    psycopg_stub.connect = lambda *args, **kwargs: None
    sys.modules["psycopg"] = psycopg_stub

if "psycopg.rows" not in sys.modules:
    psycopg_rows_stub = types.ModuleType("psycopg.rows")
    psycopg_rows_stub.dict_row = object()
    sys.modules["psycopg.rows"] = psycopg_rows_stub

if "psycopg.types" not in sys.modules:
    sys.modules["psycopg.types"] = types.ModuleType("psycopg.types")

if "psycopg.types.json" not in sys.modules:
    psycopg_types_json = types.ModuleType("psycopg.types.json")

    class _Json:
        def __init__(self, value):
            self.value = value

    psycopg_types_json.Json = _Json
    sys.modules["psycopg.types.json"] = psycopg_types_json

if "waitress" not in sys.modules:
    waitress_stub = types.ModuleType("waitress")
    waitress_stub.serve = lambda *args, **kwargs: None
    sys.modules["waitress"] = waitress_stub

if "yaml" not in sys.modules:
    yaml_stub = types.ModuleType("yaml")
    yaml_stub.safe_load = lambda value: {}
    sys.modules["yaml"] = yaml_stub

from dashboard.server import _compute_monthly_progress


class DashboardMetricsTests(unittest.TestCase):
    def test_monthly_progress_uses_previous_month_when_available(self):
        self.assertEqual(_compute_monthly_progress(4000, previous_total=2500, month_floor_total=1000), 1500)

    def test_monthly_progress_falls_back_to_current_month_floor(self):
        self.assertEqual(_compute_monthly_progress(4000, previous_total=None, month_floor_total=1250), 2750)

    def test_monthly_progress_never_goes_negative(self):
        self.assertEqual(_compute_monthly_progress(1250, previous_total=None, month_floor_total=4000), 0)


if __name__ == "__main__":
    unittest.main()
