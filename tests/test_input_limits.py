"""Real boundaries and refusal atomicity for the approved selected-CSV envelope."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_agriculture import input_limits as limits
from agent_agriculture.capture import HEADERS, prepare
from agent_agriculture.cli import main
from agent_agriculture.contracts import Contracts, load_document
from agent_agriculture.errors import PipelineError
from agent_agriculture.pipeline import run
from agent_agriculture.records import ingest
from agent_agriculture.storage import digest, json_bytes, verify_snapshot

NOW = datetime(2026, 10, 17, 1, 30, tzinfo=timezone.utc)


def csv_data(count, kind="P", language="en", multiline=False):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, delimiter=";" if language == "fr" else ",", lineterminator="\n")
    writer.writerow(HEADERS[language])
    for number in range(count):
        writer.writerow([f"{kind}{number}", f"SYN-{number}", "2026-09-01", "ENT-001",
                         "Synthetic\nsupplier" if multiline else "Synthetic supplier", "1", "kg",
                         "1.00" if kind == "P" else "", "CAD" if kind == "P" else ""])
    return stream.getvalue().encode("utf-8")


class InputLimitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ag-p20-test-", dir=ROOT / "outputs")
        self.folder = Path(self.temporary.name).resolve()
        self.case = self.folder / "case"
        shutil.copytree(ROOT / "tests/fixtures/cases/en-baseline", self.case)

    def tearDown(self):
        self.assertTrue(self.folder.is_relative_to((ROOT / "outputs").resolve()))
        self.assertTrue(self.folder.name.startswith("ag-p20-test-"))
        self.temporary.cleanup()

    def assert_code(self, code, function):
        with self.assertRaises(PipelineError) as caught:
            function()
        self.assertEqual(caught.exception.code, code)

    def setup_csv(self, counts=(1, 1), *, multiline=False):
        manifest = load_document(self.case / "manifest.json")
        for spec, count, kind in zip(manifest["inputs"], counts, ("P", "R")):
            raw = csv_data(count, kind, multiline=multiline)
            (self.case / spec["path"]).write_bytes(raw)
            spec.update(sha256=digest(raw), declared_record_count=count)
        (self.case / "manifest.json").write_bytes(json_bytes(manifest))
        return manifest

    def ingest(self):
        return ingest(load_document(self.case / "task.json"), load_document(self.case / "manifest.json"), self.case, Contracts(), NOW)

    def capture(self, output=None):
        return prepare(purchase=self.case / "purchases.csv", receiving=self.case / "receiving.csv",
                       output=output or self.folder / "captured", task_id="limit-test", enterprise="ENT-001", jurisdiction="CA-ON",
                       start="2026-09-01", end="2026-09-30", currency="CAD", language="en", question="Synthetic limit test",
                       recipient="Local synthetic review", current_tool="Synthetic worksheet", coverage="complete",
                       confirm_authority=True, confirm_mapping=True, confirm_transcription=True, now=NOW)

    def test_approved_policy_values_are_recorded_in_accepted_snapshot_identity(self):
        self.setup_csv()
        result = run(self.case / "task.json", self.case / "manifest.json", self.folder / "runs", now=NOW)
        engine = verify_snapshot(Path(result["path"]))["engine"]
        self.assertEqual(engine["version"], "0.1.0a3")
        self.assertEqual(engine["input_limits"], limits.policy())
        self.assertEqual((limits.MAX_SOURCE_BYTES, limits.MAX_TASK_BYTES, limits.MAX_TASK_RECORDS), (16777216, 33554432, 10000))

    def test_actual_per_source_byte_boundary_and_one_excess_byte(self):
        path = self.folder / "bytes.csv"
        for size in (limits.MAX_SOURCE_BYTES - 1, limits.MAX_SOURCE_BYTES, limits.MAX_SOURCE_BYTES + 1):
            with self.subTest(bytes=size):
                path.write_bytes(b"s" * size)
                if size <= limits.MAX_SOURCE_BYTES:
                    self.assertEqual(len(limits.InputBudget().read(path)), size)
                else:
                    self.assert_code("input.source_bytes", lambda: limits.InputBudget().read(path))
                self.assertEqual(path.stat().st_size, size)

    def test_actual_two_source_combined_byte_boundary(self):
        budget = limits.InputBudget()
        for name in ("first.csv", "second.csv"):
            path = self.folder / name
            path.write_bytes(b"s" * limits.MAX_SOURCE_BYTES)
            self.assertEqual(len(budget.read(path)), limits.MAX_SOURCE_BYTES)
        self.assertEqual(budget.bytes, 33554432)

    def test_combined_byte_guard_counts_actual_reads_and_stops_at_one_excess(self):
        first, second = self.folder / "first.csv", self.folder / "second.csv"
        first.write_bytes(b"12345")
        second.write_bytes(b"67890")
        with patch.object(limits, "MAX_SOURCE_BYTES", 6), patch.object(limits, "MAX_TASK_BYTES", 9):
            budget = limits.InputBudget()
            self.assertEqual(budget.read(first), b"12345")
            self.assert_code("input.task_bytes", lambda: budget.read(second))
        with patch.object(limits, "MAX_SOURCE_BYTES", 6), patch.object(limits, "MAX_TASK_BYTES", 10):
            budget = limits.InputBudget()
            budget.read(first)
            self.assertEqual(budget.read(second), b"67890")

    def test_growing_or_short_read_source_cannot_escape_actual_byte_cap(self):
        requests = []
        class GrowingShortReader(io.BytesIO):
            def read(self, size=-1):
                requests.append(size)
                return super().read(min(size, 2))
        stream = GrowingShortReader(b"0123456789tail-must-not-be-read")
        with patch.object(limits, "MAX_SOURCE_BYTES", 9), patch.object(Path, "stat", side_effect=AssertionError("No stale size check")), patch.object(Path, "open", return_value=stream):
            self.assert_code("input.source_bytes", lambda: limits.InputBudget().read(self.folder / "growing.csv"))
        self.assertTrue(requests and all(0 < size <= 10 for size in requests))
        self.assertEqual(sum(min(size, 2) for size in requests), 10)

    def test_utf8_bom_and_multibyte_limit_uses_bytes_not_characters(self):
        raw = "\ufeffa,b\n1,mémo\n".encode("utf-8")
        path = self.folder / "utf8.csv"
        path.write_bytes(raw)
        with patch.object(limits, "MAX_SOURCE_BYTES", len(raw)):
            self.assertEqual(limits.InputBudget().read(path), raw)
        with patch.object(limits, "MAX_SOURCE_BYTES", len(raw) - 1):
            self.assert_code("input.source_bytes", lambda: limits.InputBudget().read(path))

    def test_actual_10000_logical_records_accepted_across_two_sources_and_multiline(self):
        self.setup_csv((4999, 5001), multiline=True)
        captured = self.capture()
        self.assertEqual([s["declared_record_count"] for s in load_document(Path(captured["manifest"]))["inputs"]], [4999, 5001])
        working, _, _ = self.ingest()
        self.assertEqual(len(working), 10000)
        self.assertEqual([r.source["row_number"] for r in working[:2]], [2, 4])
        self.assertEqual(working[0].values["supplier"], "Synthetic\nsupplier")

    def test_10001_combined_records_refuse_both_paths_without_output_even_false_declared_count(self):
        self.setup_csv((5000, 5001))
        manifest = load_document(self.case / "manifest.json")
        manifest["inputs"][1]["declared_record_count"] = 0
        (self.case / "manifest.json").write_bytes(json_bytes(manifest))
        for action in (self.capture, self.ingest):
            with self.subTest(action=action.__name__):
                self.assert_code("input.task_records", action)
        self.assertFalse((self.folder / "captured").exists())
        self.assertFalse(list(self.folder.rglob(".preparing-*")))

    def test_byte_refusal_in_either_source_preserves_sources_and_creates_no_preparation(self):
        self.setup_csv()
        original = {p.name: p.read_bytes() for p in self.case.glob("*.csv")}
        for task_cap, source_cap, expected in ((999999, 1, "input.source_bytes"), (1, 999999, "input.task_bytes")):
            for action in (self.capture, self.ingest):
                with self.subTest(action=action.__name__, code=expected), patch.object(limits, "MAX_SOURCE_BYTES", source_cap), patch.object(limits, "MAX_TASK_BYTES", task_cap):
                    self.assert_code(expected, action)
        self.assertEqual(original, {p.name: p.read_bytes() for p in self.case.glob("*.csv")})
        self.assertFalse((self.folder / "captured").exists())
        self.assertFalse(list(self.folder.rglob(".preparing-*")))

    def test_second_source_excess_preserves_existing_snapshot_and_selector(self):
        self.setup_csv()
        output = self.folder / "runs"
        accepted = run(self.case / "task.json", self.case / "manifest.json", output, now=NOW)
        before = {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()}
        with patch.object(limits, "MAX_TASK_RECORDS", 1):
            self.assert_code("input.task_records", lambda: run(self.case / "task.json", self.case / "manifest.json", output, now=NOW))
            self.assert_code("input.task_records", self.capture)
        self.assertEqual(before, {p.relative_to(output): p.read_bytes() for p in output.rglob("*") if p.is_file()})
        verify_snapshot(Path(accepted["path"]))
        self.assertFalse(list(self.folder.rglob(".preparing-*")))

    def test_malformed_after_valid_row_and_invalid_utf8_refuse_both_paths_atomically(self):
        for suffix in (b'P2,"unterminated\n', b'\xff\n', b'wrong,width\n'):
            with self.subTest(suffix=suffix):
                manifest = self.setup_csv()
                raw = csv_data(1) + suffix
                (self.case / "purchases.csv").write_bytes(raw)
                manifest["inputs"][0].update(sha256=digest(raw), declared_record_count=None)
                (self.case / "manifest.json").write_bytes(json_bytes(manifest))
                expected = "input.row_width" if suffix.startswith(b"wrong") else "input.csv"
                self.assert_code(expected, self.capture)
                self.assert_code(expected, self.ingest)
                self.assertFalse((self.folder / "captured").exists())
                self.assertEqual((self.case / "purchases.csv").read_bytes(), raw)
        self.assertFalse(list(self.folder.rglob(".preparing-*")))

    def test_authority_checks_precede_bounded_reader_and_new_errors_are_bilingual(self):
        self.setup_csv()
        task = load_document(self.case / "task.json")
        task["permission"]["authority_confirmed"] = False
        (self.case / "task.json").write_bytes(json_bytes(task))
        with patch.object(limits.InputBudget, "read", side_effect=AssertionError("No authorized source read")):
            self.assert_code("contract.task-context", self.ingest)
        task["permission"]["authority_confirmed"] = True
        (self.case / "task.json").write_bytes(json_bytes(task))
        for language in ("en", "fr"):
            for name, value, expected in (("MAX_SOURCE_BYTES", 1, "input.source_bytes"), ("MAX_TASK_BYTES", 1, "input.task_bytes"), ("MAX_TASK_RECORDS", 1, "input.task_records")):
                stdout, stderr = io.StringIO(), io.StringIO()
                with self.subTest(language=language, expected=expected), patch.object(limits, name, value), redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(["reconcile", "--language", language, "--task", str(self.case / "task.json"), "--manifest", str(self.case / "manifest.json"), "--output", str(self.folder / "refused")])
                self.assertEqual(result, 2)
                self.assertEqual(stdout.getvalue(), "")
                error = json.loads(stderr.getvalue())
                self.assertEqual(error["error"], expected)
                self.assertIn("tronqué" if language == "fr" else "truncated", error["message"])
                self.assertFalse((self.folder / "refused").exists())


if __name__ == "__main__":
    unittest.main()
