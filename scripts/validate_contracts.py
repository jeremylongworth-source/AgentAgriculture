"""Check AG-01 schemas, registries and synthetic contract examples offline."""

import hashlib
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agent_agriculture.contracts import Contracts, correction_conflicts, load_document


def main() -> int:
    contracts = Contracts(ROOT)
    failures = []
    checked = 0

    def check(name, document, label):
        nonlocal checked
        checked += 1
        for issue in contracts.validate(name, document):
            failures.append(f"{label}: {issue.code} {issue.path}")

    registry_paths = sorted((ROOT / "registries").glob("*.yaml"))
    if {path.stem for path in registry_paths} != {"sources", "coverage", "terminology", "workflows"}:
        failures.append("Expected the four AG-01 registries")
    for path in registry_paths:
        document = load_document(path)
        name = {
            "sources": "source-registry",
            "coverage": "coverage-registry",
            "terminology": "terminology-registry",
            "workflow_readiness": "workflow-registry",
        }[document["registry_type"]]
        check(name, document, path.relative_to(ROOT))

    for path in sorted((ROOT / "tests/fixtures/contracts").glob("*.json")):
        check(path.stem, load_document(path), path.relative_to(ROOT))

    folders = sorted((ROOT / "tests/fixtures/cases").iterdir())
    if {folder.name for folder in folders} != {"en-baseline", "fr-equivalent", "partial-export"}:
        failures.append("Expected the three specified reference cases")
    baseline_rows = {}
    for folder in folders:
        task = load_document(folder / "task.json")
        manifest = load_document(folder / "manifest.json")
        check("task-context", task, folder.name)
        check("input-manifest", manifest, folder.name)
        if task["task_id"] != manifest["task_id"]:
            failures.append(f"{folder.name}: task/manifest identity differs")
        if set(task["permission"]["selected_source_ids"]) != {s["source_id"] for s in manifest["inputs"]}:
            failures.append(f"{folder.name}: selected file authority differs")
        for source in manifest["inputs"]:
            path = (folder / source["path"]).resolve()
            if not path.is_relative_to(folder.resolve()):
                failures.append(f"{folder.name}: fixture path escapes case directory")
                continue
            if hashlib.sha256(path.read_bytes()).hexdigest() != source["sha256"]:
                failures.append(f"{folder.name}: fixture digest differs")
            with path.open(encoding=source["encoding"], newline="") as stream:
                reader = csv.DictReader(stream, delimiter=source["delimiter"])
                headers = reader.fieldnames or []
                if len(headers) != len(set(headers)) or any(
                    header not in headers for header in source["field_mapping"].values() if header is not None
                ):
                    failures.append(f"{folder.name}: fixture headers/mapping differ")
                rows = list(reader)
            if len(rows) != source["declared_record_count"]:
                failures.append(f"{folder.name}: fixture record count differs")
            if folder.name == "en-baseline":
                for row_number, row in enumerate(rows, 2):
                    baseline_rows[(source["source_id"], row_number)] = (source, row)
        corrections = load_document(folder / "corrections.json")
        for correction in corrections:
            check("correction", correction, folder.name)
            if correction["task_id"] != task["task_id"]:
                failures.append(f"{folder.name}: correction belongs to another task")
        for issue in correction_conflicts(corrections):
            failures.append(f"{folder.name}: {issue.code}")

    for name in ("original-record", "normalized-record", "calculation"):
        document = load_document(ROOT / f"tests/fixtures/contracts/{name}.json")
        entries = document["inputs"] if name == "calculation" else [document]
        for entry in entries:
            pointer = entry["source"]
            source, row = baseline_rows[(pointer["source_id"], pointer["row_number"])]
            if source["sha256"] != pointer["sha256"] or row[source["field_mapping"]["source_record_id"]] != pointer["source_record_id"]:
                failures.append(f"{name}: sample source pointer differs from original evidence")
            if "original_fields" in entry and entry["original_fields"] != row:
                failures.append(f"{name}: sample original values differ")
        if name == "normalized-record":
            baseline = ROOT / "tests/fixtures/cases/en-baseline"
            for issue in contracts.validate_in_context(
                document, load_document(baseline / "task.json"), load_document(baseline / "manifest.json")
            ):
                failures.append(f"{name}: {issue.code}")

    if failures:
        for failure in failures:
            print("FAIL", failure, file=sys.stderr)
        return 1
    print(f"PASS {len(contracts.schemas)} schemas and {checked} registry/fixture documents; local references only")
    print("Contract checks only; end-to-end pipeline and farmer evidence require separate verification.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError) as exc:
        print(f"FAIL contract inputs/configuration: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1)
