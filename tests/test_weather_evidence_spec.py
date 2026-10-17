"""Executable synthetic weather design cases; no network, geography or XML parser."""

from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from weather_evidence_lab import assess_alerts, assess_value

NOW = "2026-10-16T12:00:00+00:00"


def observation(**changes):
    return {"synthetic": True, "kind": "observation", "source_id": "SYN-STATION-01",
            "location_id": "SYN-AREA-A", "unit": "mm", "value": "0", "value_state": "measured",
            "quality": "checked_for_fixture", "observed_at": "2026-10-16T11:30:00+00:00",
            "retrieved_at": "2026-10-16T11:59:00+00:00", **changes}


def message(identifier="A", **changes):
    return {"synthetic": True, "sender": "SYNTHETIC-ISSUER", "identifier": identifier,
            "sent": "2026-10-16T10:00:00-00:00", "effective": "2026-10-16T10:00:00-00:00",
            "expires": "2026-10-16T13:00:00-00:00", "status": "Actual", "scope": "Public",
            "msg_type": "Alert", "references": [], "area_match": True,
            "body": {"en-CA": "SYNTHETIC MESSAGE - no real warning", "fr-CA": "MESSAGE SYNTHÉTIQUE - aucun avertissement réel"}, **changes}


def reference(item):
    return [item["sender"], item["identifier"], item["sent"]]


class WeatherEvidenceSpecTests(unittest.TestCase):
    def value(self, item, **changes):
        return assess_value(item, **{"now": NOW, "location_id": "SYN-AREA-A", "unit": "mm", "max_age_seconds": 3600, **changes})

    def alerts(self, items, **changes):
        return assess_alerts(items, **{"now": NOW, "checked_at": "2026-10-16T11:59:00+00:00",
                                     "feed_complete": True, "max_age_seconds": 300, **changes})

    def test_recent_download_does_not_refresh_old_observation(self):
        result = self.value(observation(observed_at="2026-10-15T11:30:00+00:00"))
        self.assertEqual(result["evidence_age_seconds"], 88200)
        self.assertEqual(result["issues"], ["evidence_stale"])

    def test_explicit_offsets_are_equivalent_and_naive_time_is_refused(self):
        self.assertEqual(self.value(observation())["evidence_age_seconds"],
                         self.value(observation(observed_at="2026-10-16T07:30:00-04:00"))["evidence_age_seconds"])
        with self.assertRaises(ValueError):
            self.value(observation(observed_at="2026-10-16T11:30:00"))
        self.assertIn("time_order_invalid", self.value(observation(observed_at="2026-10-17T11:30:00+00:00"))["issues"])

    def test_zero_missing_trace_suppressed_and_estimated_are_distinct(self):
        for state, value in (("measured", "0"), ("missing", None), ("trace", None), ("suppressed", None), ("estimated", "0")):
            with self.subTest(state=state):
                result = self.value(observation(value_state=state, value=value))
                self.assertEqual(result["value_state"], state)
                self.assertEqual(result["issues"], [] if state == "measured" else ["value_" + state])
                self.assertEqual(result["agronomic_permission"], "not_established")

    def test_location_units_quality_and_numeric_special_values_cannot_silently_pass(self):
        result = self.value(observation(location_id="SYN-AREA-B", unit="inch", quality="unknown", value="NaN"))
        self.assertEqual(result["issues"], ["location_mismatch", "numeric_value_nonfinite", "quality_unreviewed", "unit_mismatch"])

    def test_forecast_issue_validity_and_task_window_are_separate(self):
        forecast = observation(kind="forecast", value_state="predicted", issued_at="2026-10-16T11:00:00+00:00",
                               valid_start="2026-10-16T12:00:00+00:00", valid_end="2026-10-16T18:00:00+00:00")
        del forecast["observed_at"]
        good = self.value(forecast, window=(NOW, "2026-10-16T15:00:00+00:00"))
        self.assertEqual(good["issues"], [])
        self.assertIn("task_window_not_covered", self.value(forecast, window=(NOW, "2026-10-16T19:00:00+00:00"))["issues"])
        forecast.update(valid_start="2026-10-16T10:00:00+00:00", valid_end=NOW)
        self.assertIn("forecast_expired", self.value(forecast, window=(NOW, "2026-10-16T13:00:00+00:00"))["issues"])

    def test_duplicate_messages_preserve_bilingual_body_without_double_counting(self):
        alert = message()
        result = self.alerts([alert, deepcopy(alert)])
        self.assertEqual(result["active_fixture_ids"], ["A"])
        self.assertEqual(result["retained_messages"], [alert])
        conflict = deepcopy(alert)
        conflict["body"]["en-CA"] = "DIFFERENT SYNTHETIC BODY"
        self.assertIn("conflicting_duplicate", self.alerts([alert, conflict])["issues"])

    def test_reordered_update_and_cancel_do_not_resurrect_old_messages(self):
        alert = message()
        update = message("B", sent="2026-10-16T10:30:00-00:00", msg_type="Update", references=[reference(alert)])
        cancel = message("C", sent="2026-10-16T11:00:00-00:00", msg_type="Cancel", references=[reference(update)])
        self.assertEqual(self.alerts([update, alert])["active_fixture_ids"], ["B"])
        result = self.alerts([cancel, alert, update, alert])
        self.assertEqual(result["active_fixture_ids"], [])
        self.assertEqual(result["alert_status"], "no_applicable_messages_in_complete_fixture")

    def test_missing_references_expiry_or_location_make_status_unavailable(self):
        for alert, expected in ((message("B", msg_type="Update", references=[["SYNTHETIC-ISSUER", "MISSING", "2026-10-16T09:00:00-00:00"]]), "lifecycle_reference_missing"),
                                (message(expires=None), "expiry_unknown"), (message(area_match=None), "location_match_unknown")):
            with self.subTest(expected=expected):
                result = self.alerts([alert])
                self.assertIn(expected, result["issues"])
                self.assertEqual(result["alert_status"], "current alert status unavailable")

    def test_failed_incomplete_or_stale_feed_never_means_no_alerts(self):
        for changes in ({"feed_complete": False}, {"checked_at": "2026-10-16T10:00:00+00:00"}):
            result = self.alerts([], **changes)
            self.assertEqual(result["alert_status"], "current alert status unavailable")
            self.assertFalse(result["operational_alert_coverage"])

    def test_expiry_boundary_future_effective_and_test_status_are_not_active(self):
        for alert in (message(expires=NOW), message(effective="2026-10-16T12:30:00+00:00"), message(status="Test"), message(area_match=False)):
            self.assertEqual(self.alerts([alert])["active_fixture_ids"], [])

    def test_real_evidence_marker_is_refused_and_simulation_threshold_is_not_a_provider_rule(self):
        with self.assertRaises(ValueError):
            self.value(observation(synthetic=False))
        with self.assertRaises(ValueError):
            self.alerts([message(synthetic=False)])
        self.assertEqual(self.value(observation())["issues"], [])
        self.assertIn("evidence_stale", self.value(observation(), max_age_seconds=60)["issues"])


if __name__ == "__main__":
    unittest.main()
