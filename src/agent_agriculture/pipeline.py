"""One selected local CSV task through to a portable, inspectable snapshot."""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .contracts import Contracts, load_document
from .errors import PipelineError
from .input_limits import policy as input_policy
from .language import issue_text, text
from .presentation import normalized_csv, record_review, safe_cell, summary
from .records import VERSION, apply_corrections, ingest, require_contract
from .reconciliation import reconcile
from .storage import digest, json_bytes, publish

ENGINE_VERSION = "0.1.0a3"


def _engine(contracts):
    source = {path.name: digest(path.read_bytes()) for path in sorted(Path(__file__).parent.glob("*.py"))}
    return {"version": ENGINE_VERSION, "implementation_sha256": digest(json_bytes({"modules": source, "schemas": contracts.schemas})),
            "input_limits": input_policy()}


def run(task_path: Path, manifest_path: Path, output: Path, corrections_path: Path | None = None, *, now=None, language=None):
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise PipelineError("time.offset", "Execution time must include an explicit timezone offset.")
    contracts = Contracts()
    task, manifest = load_document(task_path), load_document(manifest_path)
    if language is not None:
        task["language"] = language
    corrections = load_document(corrections_path) if corrections_path else []
    working, originals, input_paths = ingest(task, manifest, manifest_path.resolve().parent, contracts, now)
    for path in [task_path, manifest_path] + ([corrections_path] if corrections_path else []):
        input_paths.add(path.resolve())
    # No chosen control/evidence file can be replaced by an output selector/lock.
    if output.resolve() in input_paths or any(path == output.resolve() / name for path in input_paths for name in ("current.json", ".writer-lock")):
        raise PipelineError("output.input_collision", "Choose an output directory separate from selected input files.")
    history, correction_issues = apply_corrections(working, corrections, task, contracts, now)
    normalized = [record.normalized(task) for record in working]
    original_records = [record.original() for record in working]
    totals, calculations, exceptions = reconcile(working, normalized, task, manifest, correction_issues)
    for item in exceptions:
        item["message"] = issue_text(task["language"], item["code"])
    for record in original_records:
        require_contract(contracts, "original-record", record)
    for record in normalized:
        require_contract(contracts, "normalized-record", record)
    for calculation in calculations:
        require_contract(contracts, "calculation", calculation)
    portable_manifest = deepcopy(manifest)
    for source in portable_manifest["inputs"]:
        source["path"] = "originals/" + source["source_id"] + ".csv"
    engine = _engine(contracts)
    run_id = "run-" + digest(json_bytes({"task": task, "manifest": portable_manifest, "corrections": corrections, "engine": engine}))
    payloads, media = {}, {}

    def add_json(name, data):
        payloads[name], media[name] = json_bytes(data), "application/json"

    for name, data in {"task.json": task, "input-manifest.json": portable_manifest, "original-records.json": original_records,
                       "normalized-records.json": normalized, "corrections.json": corrections, "correction-history.json": history,
                       "exceptions.json": exceptions, "calculations.json": calculations, "totals.json": totals}.items():
        add_json(name, data)
    for source_id, raw in originals.items():
        name = "originals/" + source_id + ".csv"
        payloads[name], media[name] = raw, "text/csv"
    payloads["normalized-records.csv"], media["normalized-records.csv"] = normalized_csv(normalized, task["language"]), "text/csv"
    payloads["summary.md"], media["summary.md"] = summary(task, totals, exceptions, manifest), "text/markdown"
    payloads["record-review.md"], media["record-review.md"] = record_review(normalized, history, task["language"]), "text/markdown"
    completeness = "partial" if any(source["completeness"] == "partial" for source in manifest["inputs"]) else ("unknown" if any(source["completeness"] == "unknown" for source in manifest["inputs"]) else "complete")
    review = {"schema_version": VERSION, "package_id": "pkg-" + run_id[4:], "task_id": task["task_id"], "version": 1,
              "created_at": now.isoformat(), "language": task["language"], "question": task["question"],
              "scope": {"enterprise_id": task["enterprise_id"], "reporting_period": task["reporting_period"], "currency": task["currency"], "transaction_basis": task["transaction_basis"], "completeness": completeness},
              "status": totals["package_status"], "delivery_state": "saved_locally", "input_manifest_id": manifest["manifest_id"],
              "source_refs": [record["source"] for record in original_records],
              "checked_calculation_ids": [item["calculation_id"] for item in calculations if item["status"] == "checked"],
              "exception_ids": [item["exception_id"] for item in exceptions],
              "assumptions": [text(task["language"], key) for key in ("assumption.declared", "assumption.purchase", "assumption.local")],
              "omissions": [text for source in manifest["inputs"] for text in source["omitted_sections"]],
              "unresolved_questions": [item["exception_id"] + " (" + item["code"] + "): " + item["message"] for item in exceptions],
              "freshness_note": text(task["language"], "freshness"),
              "intended_recipient_scope": task["recipient_scope"],
              "export_manifest": [{"path": path, "media_type": media[path], "sha256": digest(raw)} for path, raw in sorted(payloads.items())]}
    require_contract(contracts, "review-package", review)
    add_json("review-package.json", review)
    return publish(output, run_id, payloads, media, engine, task["task_id"])
