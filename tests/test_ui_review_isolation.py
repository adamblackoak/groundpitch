"""Exercise the actual Streamlit review widgets without any paid provider calls.

Streamlit AppTest uses the checked-in Nutrient fixture and no external APIs.
A review selection must be scoped to its originating run for both lanes.
"""
import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
CLAIM = "Process up to 10,000 invoices per hour."


def _start_offline_app(claim=CLAIM):
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20).run()
    assert not app.exception
    app.checkbox[0].set_value(True).run()  # Offline DWS fixture mode.
    app.text_area[0].set_value(claim).run()
    app.button[0].click().run()  # Ground the claims.
    assert not app.exception
    assert len(app.selectbox) >= 1
    return app


def _fake_live_scan():
    return {
        "query": "test fixture", "search_status": "Success",
        "checked_at_utc": "2026-10-18T00:00:00+00:00",
        "relevant_result_count": 1, "raw_result_count": 1,
        "subject": "AsterFlow", "results": [{
            "title": "Fixture notice", "domain": "example.test",
            "link": "https://example.test/notice",
            "snippet": "This is synthetic. No provider request was performed.",
        }],
    }


class UIIsolationTests(unittest.TestCase):
    def test_ui_source_approval_does_not_transfer_to_next_run(self):
        app = _start_offline_app()
        first = app.session_state["gp_run"]["run_id"]
        assert app.selectbox[0].value == "PENDING"
        app.selectbox[0].set_value("APPROVE").run()
        assert not app.exception
        assert app.selectbox[0].value == "APPROVE"

        # Same row, different claim: old position-based keys leaked APPROVE here.
        app.text_area[0].set_value("Manual review time fell by 37% in a controlled pilot.").run()
        app.button[0].click().run()
        assert not app.exception
        assert app.session_state["gp_run"]["run_id"] != first
        assert len(app.selectbox) >= 1
        assert app.selectbox[0].value == "PENDING"


    def test_ui_live_approval_does_not_transfer_between_runs(self):
        app = _start_offline_app()
        state = dict(app.session_state["gp_run"])
        state["live_scans"] = {CLAIM: _fake_live_scan()}
        app.session_state["gp_run"] = state
        app.run()
        assert not app.exception
        assert len(app.selectbox) == 2
        assert [w.value for w in app.selectbox] == ["PENDING", "PENDING"]

        app.selectbox[0].set_value("APPROVE").run()
        app.selectbox[1].set_value("APPROVE").run()
        assert not app.exception
        assert [w.value for w in app.selectbox] == ["APPROVE", "APPROVE"]

        next_run = dict(app.session_state["gp_run"])
        next_run["run_id"] = "different-run-id"
        app.session_state["gp_run"] = next_run
        app.run()
        assert not app.exception
        assert [w.value for w in app.selectbox] == ["PENDING", "PENDING"]
