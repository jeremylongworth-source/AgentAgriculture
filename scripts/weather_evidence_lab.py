"""Synthetic-only weather evidence design lab; no provider parser or live feed."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json


def instant(value):
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError("Explicit time offset required")
    return parsed.astimezone(timezone.utc)


def assess_value(item, *, now, location_id, unit, max_age_seconds, window=None):
    """Check an invented normalized envelope; thresholds are simulation inputs."""
    if item.get("synthetic") is not True:
        raise ValueError("This lab accepts synthetic evidence only")
    if max_age_seconds < 0:
        raise ValueError("Nonnegative simulation age required")
    now = instant(now)
    kind = item["kind"]
    if kind not in {"observation", "forecast"}:
        raise ValueError("Observation and forecast must be explicit")
    issues = []
    if item.get("location_id") != location_id:
        issues.append("location_mismatch")
    if item.get("unit") != unit:
        issues.append("unit_mismatch")
    state = item.get("value_state")
    if state not in {"measured", "predicted", "estimated", "missing", "trace", "suppressed"}:
        raise ValueError("Explicit value state required")
    if kind == "forecast" and state == "measured":
        issues.append("forecast_is_not_measurement")
    if kind == "observation" and state == "predicted":
        issues.append("prediction_is_not_observation")
    if state in {"missing", "trace", "suppressed"}:
        issues.append("value_" + state)
        if item.get("value") is not None:
            issues.append("nonnumeric_state_has_numeric_value")
    else:
        if not isinstance(item.get("value"), str):
            issues.append("numeric_value_missing")
        else:
            try:
                if not Decimal(item["value"]).is_finite():
                    issues.append("numeric_value_nonfinite")
            except InvalidOperation:
                issues.append("numeric_value_invalid")
        if state == "estimated":
            issues.append("value_estimated")
    if item.get("quality") != "checked_for_fixture":
        issues.append("quality_unreviewed")
    time_field = "observed_at" if kind == "observation" else "issued_at"
    evidence_time = instant(item[time_field])
    retrieved = instant(item["retrieved_at"])
    if evidence_time > now or retrieved > now or evidence_time > retrieved:
        issues.append("time_order_invalid")
    age = int((now - evidence_time).total_seconds())
    if age > max_age_seconds:
        issues.append("evidence_stale")
    if kind == "forecast":
        start, end = instant(item["valid_start"]), instant(item["valid_end"])
        if start >= end:
            issues.append("valid_interval_invalid")
        if end <= now:
            issues.append("forecast_expired")
        if window is None:
            issues.append("task_window_missing")
        else:
            window_start, window_end = map(instant, window)
            if window_start >= window_end:
                raise ValueError("Positive simulation task window required")
            if not start <= window_start < window_end <= end:
                issues.append("task_window_not_covered")
    return {"synthetic": True, "kind": kind, "source_id": item["source_id"],
            "evidence_age_seconds": age, "value_state": state,
            "issues": sorted(set(issues)), "agronomic_permission": "not_established"}


def assess_alerts(messages, *, now, checked_at, feed_complete, max_age_seconds):
    """Finite invented lifecycle model, explicitly not a CAP consumer/alert service."""
    if type(feed_complete) is not bool or max_age_seconds < 0:
        raise ValueError("Explicit simulation completeness and age required")
    now, checked = instant(now), instant(checked_at)
    issues = set()
    if not feed_complete or checked > now or (now - checked).total_seconds() > max_age_seconds:
        issues.add("feed_unavailable_or_incomplete")
    by_key = {}
    for message in messages:
        if message.get("synthetic") is not True:
            raise ValueError("This lab accepts synthetic messages only")
        key = (message["sender"], message["identifier"], message["sent"])
        instant(message["sent"])
        if key in by_key and json.dumps(by_key[key], sort_keys=True) != json.dumps(message, sort_keys=True):
            issues.add("conflicting_duplicate")
        else:
            by_key[key] = message
    current, retained = {}, []
    for key, message in sorted(by_key.items(), key=lambda pair: (instant(pair[1]["sent"]), pair[0])):
        retained.append(message)  # Exact body/language content retained, never summarized.
        if message["status"] not in {"Actual", "Exercise", "System", "Test", "Draft"}:
            raise ValueError("Unknown message status")
        if message["status"] != "Actual":
            continue
        if message["scope"] != "Public":
            issues.add("unsupported_scope")
            continue
        if instant(message["sent"]) > checked:
            issues.add("message_after_feed_check")
            continue
        kind = message["msg_type"]
        references = [tuple(reference) for reference in message["references"]]
        if kind in {"Update", "Cancel"}:
            if not references or any(reference not in by_key for reference in references):
                issues.add("lifecycle_reference_missing")
            for reference in references:
                earlier = by_key.get(reference)
                if earlier and (instant(earlier["sent"]) >= instant(message["sent"]) or earlier["status"] != "Actual"):
                    issues.add("lifecycle_reference_invalid")
                current.pop(reference, None)
        if kind in {"Alert", "Update"}:
            current[key] = message
        elif kind != "Cancel":
            issues.add("unsupported_message_type")
    active = []
    for key, message in sorted(current.items()):
        if message.get("area_match") is None:
            issues.add("location_match_unknown")
        if message.get("area_match") is not True:
            continue
        if message.get("expires") is None:
            issues.add("expiry_unknown")
            continue
        effective = instant(message["effective"])
        expires = instant(message["expires"])
        if effective >= expires:
            issues.add("alert_interval_invalid")
        elif effective <= now < expires:
            active.append(message["identifier"])
    return {"synthetic": True, "alert_status": "current alert status unavailable" if issues else
            ("applicable_messages_in_fixture" if active else "no_applicable_messages_in_complete_fixture"),
            "active_fixture_ids": active, "issues": sorted(issues), "retained_messages": retained,
            "operational_alert_coverage": False, "agronomic_permission": "not_established"}
