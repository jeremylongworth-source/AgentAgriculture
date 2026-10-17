"""Prepare operator-checked paper transcriptions without inventing paper checks."""

import csv
from datetime import datetime, timezone
import io
from pathlib import Path

from .contracts import Contracts
from .errors import PipelineError
from .input_limits import InputBudget
from .language import text
from .records import CANONICAL, VERSION, require_contract
from .storage import digest, json_bytes, write_new_directory

HEADERS = {
    "en": list(CANONICAL),
    "fr": ["identifiant_source", "référence", "date", "entreprise", "fournisseur", "quantité", "unité", "montant", "devise"],
}


def prepare(*, purchase, receiving=None, output, task_id, enterprise, jurisdiction, start, end,
            currency, language, question, recipient, current_tool, coverage, omissions=(),
            confirm_authority=False, confirm_mapping=False, confirm_transcription=False, now=None):
    if not (confirm_authority and confirm_mapping and confirm_transcription):
        raise PipelineError("capture.confirmations", "Explicit operator confirmations are required.")
    if (coverage == "partial" and not omissions) or (coverage == "complete" and omissions):
        raise PipelineError("capture.omission", "Coverage and omissions must agree.")
    output = Path(output).resolve()
    if output.exists():
        raise PipelineError("capture.exists", "Choose a new preparation directory.")
    now = now or datetime.now(timezone.utc)
    source_paths = [("purchases", "purchase", Path(purchase).resolve())]
    if receiving is not None:
        source_paths.append(("receiving", "receiving", Path(receiving).resolve()))
    task = {"schema_version": VERSION, "task_id": task_id, "purpose": text(language, "capture.purpose"), "question": question,
            "enterprise_id": enterprise, "activity_location": {"jurisdiction": jurisdiction, "description": None},
            "reporting_period": {"start": start, "end": end}, "language": language, "preferred_units": ["kg"],
            "currency": currency, "transaction_basis": "purchase_records", "roles": [{"role": "operator", "participant_alias": None}],
            "current_tools": [current_tool], "recipient_scope": recipient,
            "permission": {"authority_confirmed": True, "purpose": text(language, "capture.permission"), "allowed_operation": "local_read",
                           "selected_source_ids": [item[0] for item in source_paths], "destination": "local_review_package", "expires_at": None}}
    contracts = Contracts()
    require_contract(contracts, "task-context", task)
    evidence = {}
    manifest = {"schema_version": VERSION, "manifest_id": "manifest-" + task_id, "task_id": task_id, "version": 1, "inputs": []}
    budget = InputBudget()
    for source_id, kind, path in source_paths:
        raw = budget.read(path)
        try:
            reader = csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline=""), delimiter=";" if language == "fr" else ",", strict=True)
            headers = next(reader)
            if len(headers) != len(set(headers)) or headers[:len(CANONICAL)] != HEADERS[language]:
                raise PipelineError("capture.headers", "Use the declared capture-template headers.")
            count = 0
            for row in reader:
                if len(row) != len(headers):
                    raise PipelineError("input.row_width", "Row width differs from the capture template.")
                budget.count_record()
                count += 1
        except (UnicodeError, csv.Error, StopIteration):
            raise PipelineError("input.csv", "Use a UTF-8 capture CSV.") from None
        if count == 0:
            raise PipelineError("input.empty", "Fill and check the capture rows first.")
        filename = "inputs/" + source_id + ".csv"
        evidence[filename] = raw
        manifest["inputs"].append({"source_id": source_id, "path": filename, "sha256": digest(raw), "record_kind": kind,
                                   "format": "csv", "encoding": "utf-8", "delimiter": ";" if language == "fr" else ",",
                                   "decimal_separator": "," if language == "fr" else ".", "date_format": "iso8601",
                                   "field_mapping": dict(zip(CANONICAL, HEADERS[language])), "mapping_confirmed": True,
                                   "acquisition": "checked_manual_transcription", "transcription_checked": True,
                                   "declared_period": task["reporting_period"], "completeness": coverage, "filters": [],
                                   "included_sections": [text(language, "capture.included", kind=text(language, kind))],
                                   "omitted_sections": list(omissions), "declared_record_count": count, "received_at": now.isoformat()})
    require_contract(contracts, "input-manifest", manifest)
    if len({digest(raw) for raw in evidence.values()}) != len(evidence):
        raise PipelineError("input.repeated_evidence", "The same evidence cannot count as two source sets.")
    evidence["task.json"], evidence["manifest.json"] = json_bytes(task), json_bytes(manifest)
    write_new_directory(output, evidence, "capture.exists")
    return {"state": "prepared_inputs", "path": str(output), "task": str(output / "task.json"), "manifest": str(output / "manifest.json")}
