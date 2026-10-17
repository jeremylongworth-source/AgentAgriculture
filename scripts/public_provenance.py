"""Narrow, deterministic public-source metadata export and reference checks."""
import json
from pathlib import PurePosixPath
import yaml

INDEX = "docs/release/public-provenance.json"
GUIDE = "docs/release/public-provenance.md"
EXPORT_ID = "public-provenance-v1"
HISTORICAL_REPORT = "docs/research/R04.md"
REGISTRY_SCHEMA = "schemas/v1/source-registry.schema.json"
TARGETS = {"registries/sources.yaml", "registries/coverage.yaml", "registries/workflows.yaml", REGISTRY_SCHEMA}


class UniqueSafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError("Duplicate YAML key in source metadata")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def load_yaml(raw):
    value = yaml.load(raw.decode("utf-8-sig"), Loader=UniqueSafeLoader)
    if not isinstance(value, dict):
        raise ValueError("Registry metadata must be an object")
    return value


def transform(name, raw, transform_id):
    if transform_id != EXPORT_ID or name not in TARGETS:
        raise ValueError("Unknown or inappropriate public export transform")
    if name == REGISTRY_SCHEMA:
        document = json.loads(raw)
        field = document["properties"]["sources"]["items"]["properties"]["evidence"]["properties"]["report"]
        if field not in ({"const": HISTORICAL_REPORT}, {"enum": [HISTORICAL_REPORT, INDEX]}):
            raise ValueError("Review changed source-registry provenance contract before export")
        field.clear()
        field["enum"] = [HISTORICAL_REPORT, INDEX]
        return (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    document = load_yaml(raw)
    if name == "registries/sources.yaml":
        for source in document["sources"]:
            if source["evidence"]["report"] not in {HISTORICAL_REPORT, INDEX}:
                raise ValueError("Unrecognized historical source provenance; do not invent a substitute")
            source["evidence"]["report"] = INDEX
    elif name == "registries/coverage.yaml":
        replacements = {"docs/research/R02.md": INDEX, "roadmap.md section 8; research mapping only": GUIDE}
        for entry in document["jurisdictions"]:
            entry["evidence"] = [replacements.get(value, value) for value in entry["evidence"]]
    else:
        replacements = {"docs/workflows/records-to-review.md": "docs/release/initial-preview.md",
                        "docs/validation/AG-03.md": "tests/test_pipeline.py",
                        "docs/validation/AG-04.md": "tests/test_preview.py"}
        for entry in document["workflows"]:
            entry["evidence"] = [replacements.get(value, value) for value in entry["evidence"]]
            if INDEX not in entry["evidence"]:
                entry["evidence"].append(INDEX)
    return yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100).encode("utf-8")


def _resolve(reference, members):
    if not isinstance(reference, str) or not reference or any(c in reference for c in ("\\", ":", "#")):
        raise ValueError("Structured evidence references must be portable selected file/directory paths")
    path = PurePosixPath(reference.rstrip("/"))
    if path.is_absolute() or ".." in path.parts or str(path) != reference.rstrip("/"):
        raise ValueError("Structured evidence reference escapes the draft")
    target = str(path)
    if target not in members and not any(name.startswith(target + "/") for name in members):
        raise ValueError("Structured evidence reference is outside selected draft: " + reference)


def validate_structured_references(payloads):
    documents, references = {}, []
    for name in sorted(TARGETS - {REGISTRY_SCHEMA}):
        if name not in payloads:
            continue
        document = load_yaml(payloads[name])
        documents[name] = document
        if name == "registries/sources.yaml":
            references.extend((name, source["evidence"]["report"]) for source in document["sources"])
        elif name == "registries/coverage.yaml":
            references.extend((name, value) for entry in document["jurisdictions"] for value in entry["evidence"])
        else:
            references.extend((name, value) for entry in document["workflows"] for value in entry["evidence"])
    for name, reference in references:
        try:
            _resolve(reference, payloads)
        except ValueError as exc:
            raise ValueError(name + ": " + str(exc)) from None
    index_counts = {}
    if INDEX in payloads:
        index = json.loads(payloads[INDEX])
        if index.get("index_version") != "1.0.0" or index.get("status") != "historical_and_synthetic_provenance_not_rights_clearance":
            raise ValueError("Public index must preserve its unresolved historical-evidence status")
        for name, key, id_key in [("registries/sources.yaml", "sources", "source_id"),
                                  ("registries/coverage.yaml", "jurisdictions", "jurisdiction"),
                                  ("registries/workflows.yaml", "workflows", "workflow_id")]:
            if name not in documents:
                raise ValueError("Public provenance index requires its corresponding selected registries")
            entries = index[key]
            indexed = {entry[id_key]: entry for entry in entries}
            actual = documents[name][key]
            if len(indexed) != len(entries) or set(indexed) != {entry[id_key] for entry in actual}:
                raise ValueError("Public provenance identities differ from selected registry: " + name)
            index_counts[key] = len(indexed)
            if key == "sources":
                for source in actual:
                    entry = indexed[source[id_key]]
                    if (entry["historical_state"] != source["evidence"]["state"] or
                        entry["historical_reference_ids"] != source["evidence"]["source_refs"] or
                        entry["historical_checked_at"] != source["evidence"]["checked_at"] or
                        entry["listed_route_url"] != source["acquisition_route"]["url"] or
                        entry["public_evidence_status"] != "historical_assertion_not_independently_reproduced"):
                        raise ValueError("Public source index changes historical evidence or implies new verification")
    return {"checked": len(references), "unresolved_local_paths": 0, "indexed_entries": index_counts,
            "meaning": "Path/identity closure only; historical evidence and rights may remain unresolved."}
