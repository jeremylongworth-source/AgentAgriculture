"""Read selected evidence and apply explicit local review decisions separately."""

from collections import Counter, defaultdict
from copy import deepcopy
import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
import hashlib
import io
from pathlib import Path
import re

from .contracts import Contracts, correction_conflicts
from .errors import PipelineError
from .input_limits import InputBudget
from .language import text as localized_text

VERSION = "1.0.0"
CANONICAL = ("source_record_id", "reference", "date", "enterprise_id", "supplier", "quantity", "unit", "amount", "currency")


def require_contract(contracts, name, document):
    issues = contracts.validate(name, document)
    if issues:
        raise PipelineError("contract." + name, issues[0].code + " at " + issues[0].path)


def decimal_value(raw, separator):
    """No grouping, exponent notation, suppressed-to-zero or inferred locale."""
    if raw is None or not raw.strip() or raw.strip() == "[missing]":
        return None, "missing"
    value = raw.strip()
    if value == "[suppressed]":
        return None, "suppressed"
    estimated = value.startswith("~")
    if estimated:
        value = value[1:]
    if not re.fullmatch(r"-?[0-9]+(?:" + re.escape(separator) + r"[0-9]+)?", value):
        return None, "unresolved"
    parsed = Decimal(value.replace(separator, "."))
    return format(parsed, "f"), "estimated" if estimated else "confirmed"


def _date(raw, format_name):
    if raw is None or not raw.strip():
        return None, "missing"
    if format_name != "iso8601" or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return None, "unresolved"
    try:
        date.fromisoformat(raw)
    except ValueError:
        return None, "unresolved"
    return raw, "confirmed"


@dataclass
class WorkingRecord:
    record_id: str
    kind: str
    source: dict
    original_fields: dict
    original_values: dict
    values: dict
    spec: dict
    version: int = 1
    correction_ids: list = field(default_factory=list)
    changed_fields: set = field(default_factory=set)
    exclusion_reason: str | None = None
    extra_issues: list = field(default_factory=list)

    def original(self):
        event_date, status = _date(self.original_values["date"], self.spec["date_format"])
        return {
            "schema_version": VERSION, "record_id": self.record_id, "version": 1,
            "kind": self.kind, "source": self.source, "entity_type": "enterprise",
            "entity_id": self.original_values["enterprise_id"] or None,
            "event_time": {"original": self.original_values["date"], "date": event_date, "timezone": None, "status": status},
            "measurement_method": "checked_transcription" if self.spec["acquisition"] == "checked_manual_transcription" else "csv_export",
            "observer": None, "recorder": None, "attachment_refs": [], "review_status": "unchecked",
            "original_fields": self.original_fields,
        }

    def normalized(self, task):
        issues = list(self.extra_issues)

        def basis(field_name):
            if field_name in self.changed_fields:
                return localized_text(task["language"], "corrected", ids=", ".join(self.correction_ids))
            return localized_text(task["language"], "mapping")

        def text(field_name):
            raw = self.values[field_name]
            status = "confirmed" if raw is not None and raw.strip() else "missing"
            return {"original": self.original_values[field_name], "value": raw if status == "confirmed" else None, "status": status, "mapping_basis": basis(field_name) if status == "confirmed" else None}

        enterprise, reference = text("enterprise_id"), text("reference")
        date_format = "iso8601" if "date" in self.changed_fields else self.spec["date_format"]
        event_date, date_status = _date(self.values["date"], date_format)
        date_state = {"original": self.original_values["date"], "value": event_date, "status": date_status, "mapping_basis": basis("date") if date_status == "confirmed" else None}
        if enterprise["status"] != "confirmed":
            issues.append("enterprise.missing")
        elif enterprise["value"] != task["enterprise_id"]:
            issues.append("enterprise.wrong_scope")
        if reference["status"] != "confirmed":
            issues.append("identity.reference_missing")
        if date_status != "confirmed":
            issues.append("date.ambiguous" if date_status == "unresolved" else "date.missing")
        elif not task["reporting_period"]["start"] <= event_date <= task["reporting_period"]["end"]:
            issues.append("date.wrong_period")

        def numeric(field_name, unit_name):
            separator = "." if field_name in self.changed_fields else self.spec["decimal_separator"]
            value, status = decimal_value(self.values[field_name], separator)
            unit = self.values[unit_name] or None
            if field_name == "quantity" and status == "confirmed" and unit != "kg":
                status = "unresolved" if unit is None else "unsupported"
                issues.append("quantity.unit_missing" if unit is None else "quantity.unsupported_unit")
            if field_name == "amount" and status == "confirmed" and (unit is None or not re.fullmatch("[A-Z]{3}", unit)):
                status = "unresolved"
                issues.append("amount.currency_missing")
            if field_name == "amount" and status == "confirmed" and unit != task["currency"]:
                issues.append("amount.wrong_currency")
            if status != "confirmed" and not (field_name == "quantity" and status in {"unresolved", "unsupported"} and unit != "kg"):
                issues.append(field_name + "." + status)
            key = "unit" if unit_name == "unit" else "currency"
            return {"original_value": self.original_values[field_name], "original_" + key: self.original_values[unit_name], "value": value, key: unit, "status": status,
                    "mapping_basis": basis(field_name) + ("; " + basis(unit_name) if unit_name in self.changed_fields else "") if status in {"confirmed", "estimated"} else None}

        quantity = numeric("quantity", "unit")
        if self.kind == "purchase":
            amount = numeric("amount", "currency")
        else:
            amount = {"original_value": self.original_values["amount"], "original_currency": self.original_values["currency"], "value": None, "currency": None, "status": "missing", "mapping_basis": None}
            if self.values["amount"] and self.values["amount"].strip():
                issues.append("receiving.amount_not_purchase")
        if self.spec["declared_period"] != task["reporting_period"]:
            issues.append("export.period_mismatch")
        issues = sorted(set(issues))
        disposition = "excluded" if self.exclusion_reason else ("unresolved" if issues else "accepted")
        return {"schema_version": VERSION, "record_id": self.record_id, "version": self.version, "kind": self.kind,
                "source": self.source, "original_fields": self.original_fields, "enterprise": enterprise, "reference": reference, "date": date_state,
                "quantity": quantity, "amount": amount, "disposition": disposition, "issue_codes": issues,
                "correction_ids": self.correction_ids.copy(), "exclusion_reason": self.exclusion_reason}


def ingest(task, manifest, manifest_dir: Path, contracts: Contracts, now):
    require_contract(contracts, "task-context", task)
    require_contract(contracts, "input-manifest", manifest)
    if task["task_id"] != manifest["task_id"] or set(task["permission"]["selected_source_ids"]) != {s["source_id"] for s in manifest["inputs"]}:
        raise PipelineError("permission.scope", "Task, manifest and selected read scope must agree.")
    expiry = task["permission"]["expires_at"]
    if expiry is not None and now >= datetime.fromisoformat(expiry):
        raise PipelineError("permission.expired", "Selected read authority has expired.")
    records, evidence, paths, digests = [], {}, set(), set()
    budget = InputBudget()
    for source in manifest["inputs"]:
        path = (manifest_dir / source["path"]).resolve()
        if path in paths:
            raise PipelineError("input.repeated_file", "The same selected file cannot count as two sources.")
        raw = budget.read(path)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != source["sha256"]:
            raise PipelineError("input.digest_mismatch", "Selected evidence changed; confirm a new manifest before reading records.")
        if digest in digests:
            raise PipelineError("input.repeated_evidence", "Identical source bytes cannot silently count twice.")
        paths.add(path)
        digests.add(digest)
        evidence[source["source_id"]] = raw
        try:
            reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), delimiter=source["delimiter"], strict=True)
            headers = next(reader)
            mapping = source["field_mapping"]
            if len(headers) != len(set(headers)) or any(header not in headers for header in mapping.values() if header is not None):
                raise PipelineError("input.headers", "Headers must be unique and match the confirmed field mapping.")
            parsed = []
            while True:
                row_number = reader.line_num + 1
                try:
                    row = next(reader)
                except StopIteration:
                    break
                if len(row) != len(headers):
                    raise PipelineError("input.row_width", "Every CSV row must have the declared column count.")
                budget.count_record()
                original = dict(zip(headers, row))
                values = {key: original[mapping[key]] if mapping[key] is not None else None for key in CANONICAL}
                parsed.append((row_number, original, values))
        except (UnicodeError, csv.Error, StopIteration):
            raise PipelineError("input.csv", "Selected file is not a supported UTF-8 CSV.") from None
        if source["declared_record_count"] is not None and len(parsed) != source["declared_record_count"]:
            raise PipelineError("input.record_count", "Actual records differ from the declared export count.")
        counts = Counter(values["source_record_id"] for _, _, values in parsed)
        used = set(counts)
        for row_number, original, values in parsed:
            original_id = values["source_record_id"]
            provisional = not original_id or not original_id.strip() or counts[original_id] != 1
            key = original_id
            if provisional:
                key = f"__row_{row_number}"
                while key in used:
                    key += "_"
            used.add(key)
            pointer = {"source_id": source["source_id"], "source_record_id": key, "row_number": row_number, "sha256": digest}
            if provisional:
                pointer["identity_status"] = "provisional"
            record = WorkingRecord(source["source_id"] + ":" + key, source["record_kind"], pointer, original, values.copy(), values.copy(), source)
            if provisional:
                record.extra_issues.append("identity.source_id_ambiguous" if original_id else "identity.source_id_missing")
            records.append(record)
    if not records:
        raise PipelineError("input.empty", "No records were supplied; confirm export scope before creating a review package.")
    return records, evidence, paths


def apply_corrections(records, corrections, task, contracts, now):
    if not isinstance(corrections, list):
        raise PipelineError("correction.format", "Corrections must be a list of explicit decisions.")
    for decision in corrections:
        require_contract(contracts, "correction", decision)
        if decision["task_id"] != task["task_id"]:
            raise PipelineError("correction.task", "A correction belongs to another task.")
    history, global_issues = [], []
    by_id = {record.record_id: record for record in records}
    grouped = defaultdict(list)
    for decision in corrections:
        grouped[decision["record_id"]].append(decision)
    duplicate_ids = Counter(decision["correction_id"] for decision in corrections)
    for record_id, decisions in grouped.items():
        record = by_id.get(record_id)
        failure = None
        if record is None:
            failure = "correction.target_missing"
        elif correction_conflicts(decisions) or any(duplicate_ids[d["correction_id"]] > 1 for d in decisions):
            failure = "correction.conflict"
        candidate = deepcopy(record) if record else None
        for decision in decisions:
            if failure:
                break
            if datetime.fromisoformat(decision["confirmed_at"]) > now:
                failure = "correction.future_decision"
                break
            if candidate.version != decision["base_version"]:
                failure = "correction.stale_version"
                break
            operation, field_name = decision["operation"], decision["field"]
            key = "enterprise_id" if field_name == "enterprise" else field_name
            key = "reference" if field_name == "identity" else key
            previous = ("excluded" if candidate.exclusion_reason else candidate.normalized(task)["disposition"]) if field_name == "disposition" else candidate.values.get(key)
            if previous != decision["previous_value"]:
                failure = "correction.previous_value"
                break
            if operation == "confirm_duplicate":
                target = by_id.get(decision["duplicate_of"])
                match_fields = ("enterprise_id", "date", "quantity", "unit", "amount", "currency")
                if target is None or target.kind != candidate.kind or target.exclusion_reason or target.source.get("identity_status") == "provisional" or any(
                    target.values[field] != candidate.values[field] for field in match_fields
                ) or decision["value"] != target.values["reference"]:
                    failure = "correction.duplicate_mismatch"
                    break
                candidate.values["reference"] = decision["value"]
                candidate.changed_fields.add("reference")
                candidate.exclusion_reason = decision["reason"]
            elif operation in {"exclude", "include"}:
                if field_name != "disposition" or decision["value"] != ("excluded" if operation == "exclude" else "included"):
                    failure = "correction.operation"
                    break
                candidate.exclusion_reason = decision["reason"] if operation == "exclude" else None
            elif field_name in {"enterprise", "reference", "date", "quantity", "unit", "amount", "currency"}:
                if field_name == "unit" and candidate.values["unit"] not in {None, "", "kg"}:
                    failure = "correction.unsupported_conversion"
                    break
                if field_name == "currency" and candidate.values["currency"] not in {None, "", task["currency"]}:
                    failure = "correction.unsupported_conversion"
                    break
                candidate.values[key] = decision["value"]
                candidate.changed_fields.add(key)
            else:
                failure = "correction.operation"
                break
            candidate.version = decision["new_version"]
            candidate.correction_ids.append(decision["correction_id"])
        if failure:
            if record:
                record.extra_issues.append(failure)
            else:
                global_issues.append({"code": failure, "record_ids": [], "correction_ids": [d["correction_id"] for d in decisions]})
        else:
            record.__dict__.update(candidate.__dict__)
        history.extend({"correction_id": d["correction_id"], "record_id": record_id, "status": "not_applied" if failure else "applied", "issue_code": failure} for d in decisions)
    # A later exclusion must not silently invalidate a duplicate's retained target.
    for decision in corrections:
        if decision["operation"] == "confirm_duplicate" and any(h["correction_id"] == decision["correction_id"] and h["status"] == "applied" for h in history):
            if by_id[decision["duplicate_of"]].exclusion_reason:
                raise PipelineError("correction.duplicate_target_excluded", "A confirmed duplicate must retain an included canonical record.")
    return history, global_issues
