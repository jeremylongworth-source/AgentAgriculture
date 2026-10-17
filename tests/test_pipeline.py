"""End-to-end references, data integrity, correction and recovery evidence."""

from copy import deepcopy
import csv
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from datetime import datetime, timezone
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_agriculture.cli import main
from agent_agriculture.contracts import Contracts, load_document
from agent_agriculture.errors import PipelineError
from agent_agriculture.pipeline import run
from agent_agriculture.storage import _writer_lock, digest, json_bytes, verify_snapshot
from agent_agriculture import storage

NOW = datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="ag02-test-", dir=ROOT / "outputs")
        self.folder = Path(self.temporary.name).resolve()
        self.assertTrue(self.folder.is_relative_to(ROOT / "outputs"))
        self.case = self.folder / "case"
        shutil.copytree(ROOT / "tests/fixtures/cases/en-baseline", self.case)
        self.output = self.folder / "results"

    def tearDown(self):
        # Validate the absolute, self-created recursive cleanup target first.
        self.assertTrue(self.folder.is_relative_to((ROOT / "outputs").resolve()))
        self.assertTrue(self.folder.name.startswith("ag02-test-"))
        self.temporary.cleanup()

    def execute(self, reviewed=True, case=None, output=None):
        case = case or self.case
        return run(case / "task.json", case / "manifest.json", output or self.output,
                   case / "corrections.json" if reviewed else None, now=NOW)

    def read(self, result, name):
        return load_document(Path(result["path"]) / name)

    def edit_document(self, filename, edit):
        path = self.case / filename
        doc = load_document(path)
        edit(doc)
        path.write_bytes(json_bytes(doc))

    def edit_csv(self, source_id, edit):
        manifest = load_document(self.case / "manifest.json")
        source = next(s for s in manifest["inputs"] if s["source_id"] == source_id)
        path = self.case / source["path"]
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter=source["delimiter"])
            headers, rows = reader.fieldnames, list(reader)
        edit(rows)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, headers, delimiter=source["delimiter"], lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        source["sha256"] = digest(path.read_bytes())
        (self.case / "manifest.json").write_bytes(json_bytes(manifest))

    def decision(self, record_id, field, previous, value, key="FIX-001"):
        original = load_document(self.case / "corrections.json")[0]
        original.update(correction_id=key, record_id=record_id, operation="set_field", field=field,
                        previous_value=previous, value=value, duplicate_of=None, reason="Explicit synthetic correction")
        return original

    def test_all_three_cases_match_independent_expectations_and_preserve_sources(self):
        for name in ("en-baseline", "fr-equivalent", "partial-export"):
            with self.subTest(case=name):
                case = ROOT / "tests/fixtures/cases" / name
                expected = load_document(case / "expected.json")
                result = self.execute(case=case, output=self.folder / name)
                totals = self.read(result, "totals.json")
                self.assertEqual(totals["raw_purchase_amount_sum"], expected["raw_purchase_amount_sum"])
                self.assertEqual(result["package_status"], "incomplete")
                self.assertEqual(result["delivery_state"], "saved_locally")
                verify_snapshot(Path(result["path"]))
                if expected["reviewed_variant"]:
                    variant = expected["reviewed_variant"]
                    for key in ("included_purchase_amount", "comparable_purchase_kg", "comparable_receiving_kg", "difference_receiving_minus_purchase_kg", "unallocated_quantity_records"):
                        self.assertEqual(totals[key], variant[key])
                    self.assertEqual(totals["excluded_purchase_amount"], variant["excluded_duplicate_amount"])
                else:
                    self.assertIsNone(totals["included_purchase_amount"])
                    codes = {item["code"] for item in self.read(result, "exceptions.json")}
                    self.assertTrue(set(expected["pre_review"]["unresolved_codes"]) <= codes)
                manifest = load_document(case / "manifest.json")
                for source in manifest["inputs"]:
                    raw = (case / source["path"]).read_bytes()
                    self.assertEqual((Path(result["path"]) / "originals" / (source["source_id"] + ".csv")).read_bytes(), raw)
                    self.assertEqual(digest(raw), source["sha256"])
                for record in self.read(result, "normalized-records.json"):
                    self.assertFalse(Contracts().validate("normalized-record", record))
                for calculation in self.read(result, "calculations.json"):
                    self.assertFalse(Contracts().validate("calculation", calculation))

    def test_possible_duplicate_is_visible_without_automatic_merge(self):
        result = self.execute(reviewed=False)
        totals = self.read(result, "totals.json")
        self.assertEqual(totals["raw_purchase_amount_sum"], "665.00")
        self.assertIsNone(totals["included_purchase_amount"])
        rows = self.read(result, "normalized-records.json")
        self.assertEqual(len(rows), 9)
        self.assertFalse(any(row["disposition"] == "excluded" for row in rows))
        self.assertTrue(any(item["code"] == "identity.possible_duplicate" for item in self.read(result, "exceptions.json")))

    def test_unrelated_duplicate_does_not_hide_checked_matched_quantity_subset(self):
        result = self.execute(reviewed=False)
        totals = self.read(result, "totals.json")
        ledger = {item["calculation_id"]: item for item in self.read(result, "calculations.json")}
        for field, expected in (("comparable_purchase_kg", "125"), ("comparable_receiving_kg", "125"),
                                ("difference_receiving_minus_purchase_kg", "0")):
            with self.subTest(field=field):
                self.assertEqual(totals[field], expected)
                calculation = ledger[totals["calculation_refs"][field]]
                self.assertEqual(calculation["result"]["value"], expected)
                self.assertEqual(calculation["status"], "checked")
                self.assertFalse({"purchases:A-02", "purchases:A-03"} & {item["record_id"] for item in calculation["inputs"]})
        self.assertIsNone(totals["included_purchase_amount"])
        self.assertEqual(totals["package_status"], "incomplete")
        summary = (Path(result["path"]) / "summary.md").read_text(encoding="utf-8")
        self.assertIn("ambiguous groups", summary)
        self.assertIn("| 125 |", summary)

    def test_material_results_recompute_from_versioned_ledger_and_source_rows(self):
        result = self.execute()
        normalized = {record["record_id"]: record for record in self.read(result, "normalized-records.json")}
        originals = {record["record_id"]: record for record in self.read(result, "original-records.json")}
        ledger = {item["calculation_id"]: item for item in self.read(result, "calculations.json")}
        for calculation in ledger.values():
            with self.subTest(calculation=calculation["calculation_id"]):
                values = []
                for item in calculation["inputs"]:
                    record = originals[item["record_id"]] if calculation["calculation_id"].startswith("raw-") else normalized[item["record_id"]]
                    self.assertEqual(item["record_version"], record["version"])
                    self.assertEqual(item["source"], record["source"])
                    evidence_value = record["original_fields"][item["field"]] if "status" not in record.get(item["field"], {}) else record[item["field"]]["value"]
                    self.assertEqual(Decimal(item["value"]), Decimal(evidence_value))
                    values.append(Decimal(item["value"]))
                method = calculation["method"]["name"]
                with localcontext() as context:
                    context.prec = 80
                    if method == "sum":
                        answer = sum(values, Decimal(0))
                    elif method == "receiving_minus_purchase":
                        answer = values[0] - values[1]
                    else:
                        receipts = [value for value, item in zip(values, calculation["inputs"]) if item["role"] == "receiving"]
                        purchases = [value for value, item in zip(values, calculation["inputs"]) if item["role"] == "purchase"]
                        answer = sum(receipts, Decimal(0)) - sum(purchases, Decimal(0))
                    answer = answer.quantize(Decimal(1).scaleb(-calculation["precision"]), rounding=ROUND_HALF_EVEN)
                    self.assertEqual(answer, Decimal(calculation["result"]["value"]))
        totals = self.read(result, "totals.json")
        for field, reference in totals["calculation_refs"].items():
            if field != "raw_amount_sums_by_currency" and reference is not None:
                self.assertEqual(totals[field], ledger[reference]["result"]["value"])

    def test_identical_run_reuses_snapshot_without_changing_bytes_or_revision(self):
        first = self.execute()
        folder = Path(first["path"])
        before = {p.relative_to(folder): (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()}
        second = self.execute()
        self.assertTrue(second["reused"])
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertEqual(second["revision"], 1)
        self.assertEqual(before, {p.relative_to(folder): (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.rglob("*") if p.is_file()})

    def test_changed_receiving_quantity_recalculates_affected_results_only(self):
        first = self.execute()
        self.edit_csv("receiving", lambda rows: rows[1].update(quantity="39"))
        second = self.execute()
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual(second["revision"], 2)
        self.assertEqual(self.read(first, "totals.json")["comparable_receiving_kg"], "163")
        totals = self.read(second, "totals.json")
        self.assertEqual(totals["comparable_receiving_kg"], "164")
        self.assertEqual(totals["difference_receiving_minus_purchase_kg"], "-1")
        entry = load_document(self.output / "current.json")["tasks"]["task-en-baseline"]
        self.assertEqual(entry["supersedes"], first["run_id"])
        self.assertIn("comparable-difference-kg", entry["invalidated_calculation_ids"])
        self.assertNotIn("raw-purchase-CAD", entry["invalidated_calculation_ids"])
        verify_snapshot(Path(first["path"]))

    def test_changed_evidence_without_new_manifest_is_rejected(self):
        first = self.execute()
        raw = self.output.joinpath("current.json").read_bytes()
        path = self.case / "receiving.csv"
        path.write_bytes(path.read_bytes().replace(b",38,", b",39,"))
        with self.assertRaises(PipelineError) as caught:
            self.execute()
        self.assertEqual(caught.exception.code, "input.digest_mismatch")
        self.assertEqual(self.output.joinpath("current.json").read_bytes(), raw)
        verify_snapshot(Path(first["path"]))

    def test_explicit_missing_unit_confirmation_retains_original_blank(self):
        self.edit_document("corrections.json", lambda decisions: decisions.extend([
            self.decision("purchases:A-04", "unit", "", "kg", "UNIT-P"),
            self.decision("receiving:B-03", "unit", "", "kg", "UNIT-R"),
        ]))
        result = self.execute()
        totals = self.read(result, "totals.json")
        self.assertEqual((totals["comparable_purchase_kg"], totals["comparable_receiving_kg"]), ("170", "168"))
        row = next(r for r in self.read(result, "normalized-records.json") if r["record_id"] == "purchases:A-04")
        self.assertEqual(row["quantity"]["original_unit"], "")
        self.assertEqual(row["quantity"]["unit"], "kg")
        self.assertEqual(row["version"], 2)

    def test_amount_correction_changes_checked_value_not_original_evidence(self):
        self.edit_document("corrections.json", lambda decisions: decisions.append(self.decision("purchases:A-04", "amount", "75.00", "76.00")))
        result = self.execute()
        totals = self.read(result, "totals.json")
        self.assertEqual(totals["included_purchase_amount"], "546.00")
        self.assertEqual(totals["raw_purchase_amount_sum"], "665.00")
        row = next(r for r in self.read(result, "normalized-records.json") if r["record_id"] == "purchases:A-04")
        self.assertEqual((row["amount"]["original_value"], row["amount"]["value"]), ("75.00", "76.00"))

    def test_conflicting_decisions_are_not_applied(self):
        def conflict(decisions):
            second = deepcopy(decisions[0]); second["correction_id"] = "DUP-002"
            decisions.append(second)
        self.edit_document("corrections.json", conflict)
        result = self.execute()
        self.assertIsNone(self.read(result, "totals.json")["included_purchase_amount"])
        self.assertTrue(all(item["status"] == "not_applied" for item in self.read(result, "correction-history.json")))
        self.assertIn("correction.conflict", {item["code"] for item in self.read(result, "exceptions.json")})

    def test_stale_previous_value_remains_unapplied(self):
        self.edit_document("corrections.json", lambda decisions: decisions[0].update(previous_value="wrong prior reference"))
        result = self.execute()
        self.assertEqual(self.read(result, "correction-history.json")[0]["issue_code"], "correction.previous_value")
        self.assertIsNone(self.read(result, "totals.json")["included_purchase_amount"])

    def test_missing_and_duplicate_source_identifiers_keep_all_original_rows(self):
        for value in ("", "A-01"):
            with self.subTest(identifier=value):
                self.edit_csv("purchases", lambda rows: rows[2].update(source_record_id=value))
                result = self.execute(reviewed=False, output=self.folder / ("id-empty" if not value else "id-duplicate"))
                rows = self.read(result, "normalized-records.json")
                self.assertEqual(len(rows), 9)
                self.assertEqual(len({r["record_id"] for r in rows}), 9)
                provisional = [r for r in rows if r["source"].get("identity_status") == "provisional"]
                self.assertTrue(provisional)
                self.assertTrue(all(r["disposition"] == "unresolved" for r in provisional))
                self.assertIsNone(self.read(result, "totals.json")["included_purchase_amount"])

    def test_wrong_scope_and_currency_do_not_enter_a_confirmed_total(self):
        self.edit_csv("purchases", lambda rows: rows[0].update(enterprise_id="OTHER", date="2026-10-01", currency="USD"))
        result = self.execute()
        totals = self.read(result, "totals.json")
        self.assertIsNone(totals["included_purchase_amount"])
        self.assertEqual(totals["raw_amount_sums_by_currency"], {"CAD": "415.00", "USD": "250.00"})
        codes = {item["code"] for item in self.read(result, "exceptions.json")}
        self.assertTrue({"enterprise.wrong_scope", "date.wrong_period", "amount.wrong_currency"} <= codes)

    def test_suppressed_and_estimated_amounts_never_become_confirmed_zero(self):
        for value, status in (("[suppressed]", "suppressed"), ("", "missing"), ("~0", "estimated")):
            with self.subTest(value=value):
                self.edit_csv("purchases", lambda rows: rows[0].update(amount=value))
                result = self.execute(output=self.folder / status)
                row = next(r for r in self.read(result, "normalized-records.json") if r["record_id"] == "purchases:A-01")
                self.assertEqual(row["amount"]["status"], status)
                self.assertIsNone(self.read(result, "totals.json")["included_purchase_amount"])
                if status != "estimated":
                    self.assertIsNone(row["amount"]["value"])

    def test_measured_zero_is_retained_as_confirmed(self):
        self.edit_csv("purchases", lambda rows: rows[0].update(amount="0.00", quantity="0"))
        result = self.execute()
        row = self.read(result, "normalized-records.json")[0]
        self.assertEqual((row["amount"]["value"], row["amount"]["status"]), ("0.00", "confirmed"))
        self.assertEqual(row["quantity"]["value"], "0")

    def test_incompatible_unit_cannot_be_converted_by_a_label_correction(self):
        self.edit_csv("purchases", lambda rows: rows[0].update(unit="L"))
        self.edit_document("corrections.json", lambda decisions: decisions.append(self.decision("purchases:A-01", "unit", "L", "kg")))
        result = self.execute()
        row = self.read(result, "normalized-records.json")[0]
        self.assertEqual(row["quantity"]["status"], "unsupported")
        self.assertEqual(self.read(result, "correction-history.json")[-1]["issue_code"], "correction.unsupported_conversion")

    def test_receiving_amount_is_not_counted_as_a_purchase(self):
        self.edit_csv("receiving", lambda rows: rows[0].update(amount="999.00", currency="CAD"))
        result = self.execute()
        self.assertEqual(self.read(result, "totals.json")["included_purchase_amount"], "545.00")
        self.assertIn("receiving.amount_not_purchase", {e["code"] for e in self.read(result, "exceptions.json")})

    def test_formula_like_text_is_inert_in_export_and_original_is_preserved(self):
        value = '=HYPERLINK("https://example.invalid","x")'
        self.edit_csv("purchases", lambda rows: rows[0].update(reference=value))
        original = (self.case / "purchases.csv").read_bytes()
        result = self.execute()
        with (Path(result["path"]) / "normalized-records.csv").open(encoding="utf-8", newline="") as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(row["reference"], "'" + value)
        self.assertEqual(self.read(result, "original-records.json")[0]["original_fields"]["reference"], value)
        self.assertEqual((Path(result["path"]) / "originals/purchases.csv").read_bytes(), original)

    def test_expired_permission_stops_before_source_read(self):
        self.edit_document("task.json", lambda task: task["permission"].update(expires_at="2026-10-15T00:00:00Z"))
        with patch.object(Path, "read_bytes", side_effect=AssertionError("Source must not be read")):
            with self.assertRaises(PipelineError) as caught:
                self.execute()
        self.assertEqual(caught.exception.code, "permission.expired")
        self.assertFalse(self.output.exists())

    def test_count_mismatch_and_duplicate_headers_are_rejected(self):
        self.edit_document("manifest.json", lambda manifest: manifest["inputs"][0].update(declared_record_count=99))
        with self.assertRaises(PipelineError) as caught:
            self.execute()
        self.assertEqual(caught.exception.code, "input.record_count")
        path = self.case / "purchases.csv"
        path.write_bytes(path.read_bytes().replace(b"source_record_id,reference", b"reference,reference", 1))
        self.edit_document("manifest.json", lambda manifest: manifest["inputs"][0].update(sha256=digest(path.read_bytes()), declared_record_count=5))
        with self.assertRaises(PipelineError) as caught:
            self.execute()
        self.assertEqual(caught.exception.code, "input.headers")

    def test_complete_single_source_task_can_be_ready_for_review(self):
        manifest = load_document(self.case / "manifest.json")
        path = self.case / "purchases.csv"
        lines = path.read_bytes().splitlines(keepends=True)
        path.write_bytes(b"".join(lines[:2]))
        manifest["inputs"] = manifest["inputs"][:1]
        manifest["inputs"][0].update(sha256=digest(path.read_bytes()), declared_record_count=1)
        (self.case / "manifest.json").write_bytes(json_bytes(manifest))
        self.edit_document("task.json", lambda task: task["permission"].update(selected_source_ids=["purchases"]))
        result = self.execute(reviewed=False)
        self.assertEqual(result["package_status"], "ready_for_review")
        self.assertEqual(self.read(result, "totals.json")["included_purchase_amount"], "250.00")

    def test_interrupted_write_preserves_previous_current_and_retry_recovers(self):
        first = self.execute()
        previous = (self.output / "current.json").read_bytes()
        self.edit_csv("receiving", lambda rows: rows[1].update(quantity="39"))
        original_write = storage._write_file
        counter = 0

        def fail_midway(path, raw):
            nonlocal counter
            counter += 1
            if counter == 3:
                raise OSError("simulated storage interruption")
            return original_write(path, raw)

        with patch.object(storage, "_write_file", fail_midway):
            with self.assertRaises(OSError):
                self.execute()
        self.assertEqual((self.output / "current.json").read_bytes(), previous)
        pending = list(self.output.glob(".pending-*"))
        self.assertTrue(pending)
        with self.assertRaises(PipelineError):
            verify_snapshot(pending[0])
        second = self.execute()
        self.assertEqual(second["revision"], 2)
        verify_snapshot(Path(first["path"]))
        verify_snapshot(Path(second["path"]))

    def test_interruption_after_publication_repairs_selector_on_retry(self):
        first = self.execute()
        previous = (self.output / "current.json").read_bytes()
        self.edit_csv("receiving", lambda rows: rows[1].update(quantity="39"))
        with patch.object(storage, "_replace_selector", side_effect=OSError("simulated selector interruption")):
            with self.assertRaises(OSError):
                self.execute()
        self.assertEqual((self.output / "current.json").read_bytes(), previous)
        second = self.execute()
        self.assertTrue(second["reused"])
        self.assertEqual(second["revision"], 2)
        self.assertNotEqual(first["run_id"], second["run_id"])

    def test_tampered_or_extra_output_is_not_silently_replaced(self):
        result = self.execute()
        folder = Path(result["path"])
        (folder / "unexpected.txt").write_text("unexpected extra material", encoding="utf-8")
        with self.assertRaises(PipelineError) as caught:
            self.execute()
        self.assertEqual(caught.exception.code, "output.integrity")
        (folder / "unexpected.txt").unlink()
        (folder / "totals.json").write_text("{}", encoding="utf-8")
        with self.assertRaises(PipelineError):
            verify_snapshot(folder)
        self.assertEqual((folder / "totals.json").read_text(encoding="utf-8"), "{}")

    def test_output_lock_is_nonblocking_and_released_after_failure(self):
        with _writer_lock(self.output):
            with self.assertRaises(PipelineError) as caught:
                self.execute()
            self.assertEqual(caught.exception.code, "output.busy")
        self.assertEqual(self.execute()["delivery_state"], "saved_locally")

    def test_cli_reports_failure_without_successful_save_claim(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        from contextlib import redirect_stderr, redirect_stdout
        with patch.object(storage, "_write_file", side_effect=OSError("simulated write failure")), redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(["reconcile", "--task", str(self.case / "task.json"), "--manifest", str(self.case / "manifest.json"), "--output", str(self.output)])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertNotIn('"saved_locally"', stderr.getvalue())
        self.assertFalse((self.output / "current.json").exists())


if __name__ == "__main__":
    unittest.main()
