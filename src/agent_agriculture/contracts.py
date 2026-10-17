"""Offline contract validation; never interpret imported prose as instructions."""

from dataclasses import dataclass
from datetime import date, datetime
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
import yaml


ROOT = Path(__file__).resolve().parents[2]
JURISDICTIONS = frozenset(
    f"CA-{code}" for code in "BC AB SK MB ON QC NB NS PE NL YT NT NU".split()
)


@dataclass(frozen=True)
class Issue:
    code: str
    path: str
    message: str


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate mapping key")
        result[key] = value
    return result


class _StrictLoader(yaml.SafeLoader):
    """Safe YAML with duplicate-key rejection and textual dates/identifiers."""


def _yaml_mapping(loader, node):
    loader.flatten_mapping(node)
    return _unique_pairs(loader.construct_pairs(node, deep=True))


# BaseLoader-style scalars would turn booleans into strings. Instead remove only
# implicit timestamp conversion; unquoted numeric IDs are rejected by the schema.
_StrictLoader.yaml_implicit_resolvers = {
    key: [pair for pair in values if pair[0] != "tag:yaml.org,2002:timestamp"]
    for key, values in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_StrictLoader.add_constructor("tag:yaml.org,2002:map", _yaml_mapping)


def load_document(path: Path):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.load(text, Loader=_StrictLoader)
    return json.loads(text, object_pairs_hook=_unique_pairs)


def _offline_only(uri):
    raise NoSuchResource(ref=uri)


def _format_checker():
    checker = FormatChecker()

    @checker.checks("date-time", raises=ValueError)
    def timestamp(value):
        if not isinstance(value, str):
            return True
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})", value):
            return False
        parsed = datetime.fromisoformat(value)
        return parsed.utcoffset() is not None

    return checker


class Contracts:
    def __init__(self, root: Path | None = None):
        self.root = root or ROOT
        bundled = Path(__file__).resolve().parent / "schemas/v1"
        schema_dir = root / "schemas/v1" if root else (bundled if bundled.is_dir() else ROOT / "schemas/v1")
        self.schemas = {}
        resources = []
        for path in sorted(schema_dir.glob("*.schema.json")):
            schema = load_document(path)
            Draft202012Validator.check_schema(schema)
            name = path.name.removesuffix(".schema.json")
            self.schemas[name] = schema
            resources.append((schema["$id"], Resource.from_contents(schema)))
        if not resources:
            raise ValueError("No local schemas found")
        self.registry = Registry(retrieve=_offline_only).with_resources(resources)
        self.validators = {
            name: Draft202012Validator(
                schema, registry=self.registry, format_checker=_format_checker()
            )
            for name, schema in self.schemas.items()
        }

    def validate(self, name: str, instance) -> list[Issue]:
        issues = [
            Issue(
                "schema." + str(error.validator),
                "/" + "/".join(str(part) for part in error.absolute_path),
                "Contract constraint failed; inspect the local field and schema.",
            )
            for error in self.validators[name].iter_errors(instance)
        ]
        if issues:
            return issues
        return self._semantic(name, instance)

    def validate_in_context(self, record, task, manifest) -> list[Issue]:
        """Validate normalized evidence against the declared task without changing it."""
        issues = (
            self.validate("normalized-record", record)
            + self.validate("task-context", task)
            + self.validate("input-manifest", manifest)
        )
        if issues:
            return issues

        def fail(code, path, message):
            issues.append(Issue(code, path, message))

        sources = {source["source_id"]: source for source in manifest["inputs"]}
        pointer = record["source"]
        source = sources.get(pointer["source_id"])
        if manifest["task_id"] != task["task_id"]:
            fail("context.task_mismatch", "/task_id", "Manifest belongs to a different task.")
        if set(sources) != set(task["permission"]["selected_source_ids"]):
            fail("context.source_authority", "/permission", "Manifest sources differ from selected read authority.")
        if source is None or pointer["source_id"] not in task["permission"]["selected_source_ids"]:
            fail("context.unselected_source", "/source", "Record is outside the selected source scope.")
        elif source["sha256"] != pointer["sha256"] or source["record_kind"] != record["kind"]:
            fail("context.source_mismatch", "/source", "Source version/kind differs from the manifest.")
        if source is not None and source["declared_period"] != task["reporting_period"]:
            fail("context.manifest_period", "/source", "Source coverage differs from the selected task period.")
        if record["record_id"] != pointer["source_id"] + ":" + pointer["source_record_id"]:
            fail("context.record_identity", "/record_id", "Record identity must retain the exact source identifier.")
        if record["enterprise"]["status"] == "confirmed" and record["enterprise"]["value"] != task["enterprise_id"]:
            fail("context.wrong_enterprise", "/enterprise", "Record belongs to a different enterprise.")
        if record["date"]["status"] == "confirmed":
            period = task["reporting_period"]
            if not period["start"] <= record["date"]["value"] <= period["end"]:
                fail("context.wrong_period", "/date", "Record date is outside the selected period.")
        if record["amount"]["status"] == "confirmed" and record["amount"]["currency"] != task["currency"]:
            fail("context.mixed_currency", "/amount", "No cross-currency total is authorized by this task.")
        return issues

    @staticmethod
    def _semantic(name, doc):
        issues = []

        def fail(code, path, message):
            issues.append(Issue(code, path, message))

        def check_period(period, path):
            if date.fromisoformat(period["start"]) > date.fromisoformat(period["end"]):
                fail("period.reversed", path, "Reporting period ends before it starts.")

        if name == "task-context":
            check_period(doc["reporting_period"], "/reporting_period")
            if not doc["permission"]["authority_confirmed"]:
                fail("permission.unconfirmed", "/permission", "Local read authority is not confirmed.")
            ids = doc["permission"]["selected_source_ids"]
            if len(ids) != len(set(ids)):
                fail("permission.duplicate_source", "/permission", "Selected source identities must be unique.")

        elif name == "input-manifest":
            ids = [entry["source_id"] for entry in doc["inputs"]]
            if len(ids) != len(set(ids)):
                fail("manifest.duplicate_source", "/inputs", "Source identities must be unique.")
            for index, source in enumerate(doc["inputs"]):
                path = f"/inputs/{index}"
                check_period(source["declared_period"], path + "/declared_period")
                if not source["mapping_confirmed"]:
                    fail("mapping.unconfirmed", path, "Confirm field mapping before admitting records.")
                mapped = [value for value in source["field_mapping"].values() if value is not None]
                if len(mapped) != len(set(mapped)):
                    fail("mapping.duplicate_header", path, "One column cannot silently supply two fields.")
                if source["delimiter"] == source["decimal_separator"]:
                    fail("format.ambiguous_separator", path, "Use distinct column and decimal separators.")
                if source["completeness"] == "complete" and source["omitted_sections"]:
                    fail("manifest.false_complete", path, "A complete declaration cannot list omissions.")

        elif name == "original-record":
            event = doc["event_time"]
            if event["status"] == "confirmed" and event["date"] is None:
                fail("event.unconfirmed_date", "/event_time", "A confirmed event needs a valid date.")
            if event["status"] != "confirmed" and event["date"] is not None:
                fail("event.invented_date", "/event_time", "An unresolved date cannot have a confirmed value.")

        elif name == "normalized-record":
            if doc["date"]["status"] == "confirmed":
                try:
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", doc["date"]["value"]):
                        raise ValueError("Not an ISO calendar date")
                    date.fromisoformat(doc["date"]["value"])
                except ValueError:
                    fail("record.invalid_date", "/date", "Confirmed dates use valid ISO calendar dates.")
            fields = ("enterprise", "reference", "date", "quantity")
            if doc["kind"] == "purchase":
                fields += ("amount",)
            unresolved = any(doc[field]["status"] != "confirmed" for field in fields)
            if doc["disposition"] == "accepted" and (unresolved or doc["issue_codes"]):
                fail("record.false_acceptance", "/disposition", "Unresolved fields/issues cannot be accepted silently.")
            if doc["source"].get("identity_status") == "provisional" and doc["disposition"] == "accepted":
                fail("record.provisional_identity", "/source", "A physical-row surrogate is not confirmed business identity.")
            if doc["disposition"] == "unresolved" and not doc["issue_codes"]:
                fail("record.missing_explanation", "/issue_codes", "Explain each unresolved record.")
            if doc["disposition"] == "excluded" and (
                not doc["exclusion_reason"] or not doc["correction_ids"]
            ):
                fail("record.unjustified_exclusion", "/disposition", "Exclusion needs a reason and correction reference.")
            if doc["kind"] == "receiving" and doc["amount"]["status"] != "missing":
                fail("record.receiving_amount", "/amount", "Receiving evidence is not a second purchase.")
            money = doc["amount"]
            if money["status"] == "confirmed" and money["original_currency"] != money["currency"]:
                if money["original_currency"] not in {None, ""} or not doc["correction_ids"]:
                    fail("record.unsupported_currency_conversion", "/amount", "This contract does not support currency conversion.")
            quantity = doc["quantity"]
            if quantity["status"] == "confirmed" and quantity["original_unit"] != "kg":
                if quantity["original_unit"] not in {None, ""} or not doc["correction_ids"]:
                    fail("record.unsupported_unit_conversion", "/quantity", "A missing unit needs explicit review; incompatible units cannot be converted.")

        elif name == "correction":
            if doc["new_version"] != doc["base_version"] + 1:
                fail("correction.version", "/new_version", "A correction advances exactly one record version.")
            if doc["duplicate_of"] == doc["record_id"]:
                fail("correction.self_duplicate", "/duplicate_of", "A record cannot duplicate itself.")
            if doc["operation"] != "confirm_duplicate" and doc["duplicate_of"] is not None:
                fail("correction.unexpected_duplicate", "/duplicate_of", "Duplicate identity belongs to explicit duplicate confirmation.")

        elif name == "calculation":
            references = [(item["record_id"], item["record_version"], item["field"]) for item in doc["inputs"]]
            if len(references) != len(set(references)):
                fail("calculation.duplicate_input", "/inputs", "A source value cannot silently enter the same total twice.")
            if len({entry["unit"] for entry in doc["inputs"]} | {doc["result"]["unit"]}) != 1:
                fail("calculation.incompatible_units", "/inputs", "A calculation cannot mix units or currencies.")
            for item in doc["inputs"]:
                if (item["field"] == "quantity" and item["unit"] != "kg") or (
                    item["field"] == "amount" and not re.fullmatch("[A-Z]{3}", item["unit"])
                ):
                    fail("calculation.unsupported_basis", "/inputs", "Input fields need supported quantity units or explicit currency codes.")
            if doc["method"]["name"] == "receiving_minus_purchase" and len(doc["inputs"]) != 2:
                fail("calculation.arity", "/inputs", "A difference requires receiving and purchase inputs.")
            if doc["method"]["name"] == "paired_quantity_difference" and (
                {item.get("role") for item in doc["inputs"]} != {"receiving", "purchase"}
                or any(item["field"] != "quantity" for item in doc["inputs"])
            ):
                fail("calculation.roles", "/inputs", "Paired quantity differences require explicit receiving/purchase roles.")
            if doc["status"] == "checked" and not doc["dependent_output_refs"]:
                fail("calculation.unlinked_result", "/dependent_output_refs", "Checked results identify dependent outputs.")

        elif name == "review-package":
            check_period(doc["scope"]["reporting_period"], "/scope/reporting_period")
            for index, output in enumerate(doc["export_manifest"]):
                path = output["path"]
                if path.startswith("/") or "\\" in path or ":" in path or ".." in path.split("/"):
                    fail("package.nonportable_path", f"/export_manifest/{index}", "Export paths must remain relative to the portable package.")

        elif name == "coverage-registry":
            ids = [entry["jurisdiction"] for entry in doc["jurisdictions"]]
            if set(ids) != JURISDICTIONS or len(ids) != len(set(ids)):
                fail("coverage.jurisdictions", "/jurisdictions", "Map all 13 jurisdictions exactly once.")

        elif name == "source-registry":
            ids = [entry["source_id"] for entry in doc["sources"]]
            if len(ids) != len(set(ids)):
                fail("source.duplicate_id", "/sources", "Each acquisition route needs its own identity.")
            for index, source in enumerate(doc["sources"]):
                if source["evidence"]["state"] == "O" or source["workflow_operationally_validated"]:
                    fail("source.unsupported_operational_claim", f"/sources/{index}", "R04 establishes no O-level route or operational workflow.")

        elif name in {"terminology-registry", "workflow-registry"}:
            field, key = ("terms", "term_id") if name == "terminology-registry" else ("workflows", "workflow_id")
            ids = [item[key] for item in doc[field]]
            if len(ids) != len(set(ids)):
                fail("registry.duplicate_id", "/" + field, "Registry identities must be unique.")

        return issues


def correction_conflicts(corrections: list[dict]) -> list[Issue]:
    """Detect competing decisions and invalid history without applying changes."""
    seen_ids = set()
    latest = {}
    issues = []
    for correction in corrections:
        key = correction["record_id"]
        previous = latest.get(key)
        if correction["correction_id"] in seen_ids:
            issues.append(Issue("correction.duplicate_id", key, "Correction identities must be unique."))
        if previous is None and correction["supersedes"] is not None:
            issues.append(Issue("correction.missing_parent", key, "A superseded decision is absent from this history."))
        if previous is not None and (
            correction["supersedes"] != previous["correction_id"]
            or correction["base_version"] != previous["new_version"]
        ):
            issues.append(Issue("correction.conflict", key, "Competing/stale decisions require explicit resolution."))
        latest[key] = correction
        seen_ids.add(correction["correction_id"])
    return issues
