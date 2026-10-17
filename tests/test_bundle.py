"""Bilingual operator paths, checked manual capture and minimized local handoff."""

from contextlib import redirect_stderr, redirect_stdout
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_agriculture.capture import prepare
from agent_agriculture.cli import main
from agent_agriculture.contracts import load_document
from agent_agriculture.errors import PipelineError
from agent_agriculture.handoff import prepare_handoff
from agent_agriculture.language import error_text
from agent_agriculture.pipeline import run
from agent_agriculture.storage import digest, verify_snapshot

NOW = datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc)


class BundleTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="ag03-test-", dir=ROOT / "outputs")
        self.folder = Path(self.temporary.name).resolve()
        self.assertTrue(self.folder.is_relative_to((ROOT / "outputs").resolve()))

    def tearDown(self):
        self.assertTrue(self.folder.is_relative_to((ROOT / "outputs").resolve()))
        self.assertTrue(self.folder.name.startswith("ag03-test-"))
        self.temporary.cleanup()

    def capture_arguments(self, language="en"):
        source = ROOT / "examples/manual" / language
        return dict(purchase=source / "purchases.csv", receiving=source / "receiving.csv", output=self.folder / ("inputs-" + language),
                    task_id="manual-" + language, enterprise="ENT-001", jurisdiction="CA-ON", start="2026-09-01", end="2026-09-30",
                    currency="CAD", language=language, question="Synthetic review question", recipient="Local synthetic adviser",
                    current_tool="Checked synthetic paper", coverage="complete", confirm_authority=True,
                    confirm_mapping=True, confirm_transcription=True, now=NOW)

    def test_manual_english_and_french_paths_preserve_values_states_and_originals(self):
        semantic = {}
        for language in ("en", "fr"):
            with self.subTest(language=language):
                arguments = self.capture_arguments(language)
                captured = prepare(**arguments)
                manifest = load_document(Path(captured["manifest"]))
                for source in manifest["inputs"]:
                    self.assertTrue(source["transcription_checked"])
                    self.assertEqual(source["acquisition"], "checked_manual_transcription")
                    self.assertEqual(digest((Path(captured["path"]) / source["path"]).read_bytes()), source["sha256"])
                result = run(Path(captured["task"]), Path(captured["manifest"]), self.folder / ("runs-" + language),
                             ROOT / "examples/manual" / language / "corrections.json", now=NOW)
                folder = Path(result["path"])
                verify_snapshot(folder)
                totals = load_document(folder / "totals.json")
                self.assertEqual((totals["raw_purchase_amount_sum"], totals["included_purchase_amount"], totals["comparable_receiving_kg"]), ("665.00", "545.00", "163"))
                records = load_document(folder / "normalized-records.json")
                semantic[language] = [(r["record_id"], r["enterprise"]["value"], r["date"]["value"],
                                       r["quantity"]["value"], r["quantity"]["status"], r["amount"]["value"],
                                       r["amount"]["currency"], r["disposition"], r["issue_codes"]) for r in records]
                self.assertTrue(all(record["measurement_method"] == "checked_transcription" for record in load_document(folder / "original-records.json")))
                with (folder / "normalized-records.csv").open(encoding="utf-8", newline="") as stream:
                    rows = list(csv.DictReader(stream, delimiter=";" if language == "fr" else ","))
                self.assertEqual(rows[0]["montant" if language == "fr" else "amount"], "250,00" if language == "fr" else "250.00")
                summary = (folder / "summary.md").read_text(encoding="utf-8")
                review = (folder / "record-review.md").read_text(encoding="utf-8")
                self.assertIn("545,00" if language == "fr" else "545.00", summary)
                self.assertIn("SYN-P-L04", review)
                self.assertIn("INV-003", review)
                self.assertNotIn(chr(65533), summary + review)
        self.assertEqual(semantic["en"], semantic["fr"])

    def test_missing_capture_confirmations_stop_before_reading_evidence(self):
        for flag in ("confirm_authority", "confirm_mapping", "confirm_transcription"):
            with self.subTest(flag=flag):
                arguments = self.capture_arguments()
                arguments[flag] = False
                with patch.object(Path, "read_bytes", side_effect=AssertionError("Must not read unconfirmed evidence")):
                    with self.assertRaises(PipelineError) as caught:
                        prepare(**arguments)
                self.assertEqual(caught.exception.code, "capture.confirmations")
                self.assertFalse(arguments["output"].exists())

    def test_partial_and_unknown_capture_keep_coverage_visible(self):
        for coverage in ("partial", "unknown"):
            with self.subTest(coverage=coverage):
                arguments = self.capture_arguments()
                arguments.update(output=self.folder / coverage, coverage=coverage, omissions=["Selected paper page missing"] if coverage == "partial" else [])
                prepared = prepare(**arguments)
                result = run(Path(prepared["task"]), Path(prepared["manifest"]), self.folder / (coverage + "-runs"), now=NOW)
                totals = load_document(Path(result["path"]) / "totals.json")
                self.assertIsNone(totals["included_purchase_amount"])
                codes = {item["code"] for item in load_document(Path(result["path"]) / "exceptions.json")}
                self.assertIn("export." + coverage, codes)

    def test_capture_refuses_missing_omission_wrong_template_and_existing_output(self):
        arguments = self.capture_arguments()
        arguments["coverage"] = "partial"
        with self.assertRaises(PipelineError) as caught:
            prepare(**arguments)
        self.assertEqual(caught.exception.code, "capture.omission")
        arguments = self.capture_arguments()
        arguments["purchase"] = ROOT / "examples/manual/fr/purchases.csv"
        with self.assertRaises(PipelineError) as caught:
            prepare(**arguments)
        self.assertEqual(caught.exception.code, "capture.headers")
        arguments = self.capture_arguments()
        prepared = prepare(**arguments)
        before = Path(prepared["manifest"]).read_bytes()
        with self.assertRaises(PipelineError) as caught:
            prepare(**arguments)
        self.assertEqual(caught.exception.code, "capture.exists")
        self.assertEqual(Path(prepared["manifest"]).read_bytes(), before)

    def test_minimal_handoff_excludes_unneeded_notes_and_preserves_omissions(self):
        copied = self.folder / "sources"
        shutil.copytree(ROOT / "examples/manual/fr", copied)
        path = copied / "purchases.csv"
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream, delimiter=";")
            headers, rows = reader.fieldnames, list(reader)
        marker = "UNNEEDED-PERSONNEL-NOTE-9c87"
        rows[0]["note_transcription"] = marker
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, headers, delimiter=";", lineterminator="\n")
            writer.writeheader(); writer.writerows(rows)
        arguments = self.capture_arguments("fr")
        arguments.update(purchase=path, receiving=copied / "receiving.csv")
        prepared = prepare(**arguments)
        result = run(Path(prepared["task"]), Path(prepared["manifest"]), self.folder / "runs", copied / "corrections.json", now=NOW)
        source = Path(result["path"])
        self.assertIn(marker, (source / "normalized-records.json").read_text(encoding="utf-8"))
        handoff = prepare_handoff(source, self.folder / "adviser")
        target = Path(handoff["path"])
        expected = {"summary.md", "record-review.md", "calculations.json", "exceptions.json", "index.md", "handoff.json"}
        self.assertEqual({p.name for p in target.iterdir()}, expected)
        for path in target.iterdir():
            self.assertNotIn(marker, path.read_text(encoding="utf-8"))
        summary = (target / "summary.md").read_text(encoding="utf-8")
        self.assertNotIn("normalized-records.csv", summary)
        self.assertNotIn("originals/", summary)
        self.assertIn("copie minimale", summary)
        index = load_document(target / "handoff.json")
        self.assertTrue(index["omissions"])
        self.assertEqual(index["source_package_status"], "incomplete")
        for item in index["files"]:
            self.assertEqual(digest((target / item["path"]).read_bytes()), item["sha256"])
        with self.assertRaises(PipelineError) as caught:
            prepare_handoff(source, target)
        self.assertEqual(caught.exception.code, "handoff.exists")
        verify_snapshot(source)

    def test_handoff_refuses_unverified_source(self):
        with self.assertRaises(PipelineError):
            prepare_handoff(self.folder / "not-a-run", self.folder / "adviser")
        self.assertFalse((self.folder / "adviser").exists())

    def test_french_help_and_usage_errors_use_selected_language(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            main(["--language", "fr", "capture", "--help"])
        self.assertEqual(caught.exception.code, 0)
        self.assertIn("utilisation", output.getvalue())
        self.assertIn("transcription", output.getvalue())
        errors = io.StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as caught:
            main(["--language", "fr", "capture"])
        self.assertEqual(caught.exception.code, 2)
        value = json.loads(errors.getvalue())
        self.assertEqual(value["error"], "cli.usage")
        self.assertIn("obligatoires", value["message"])

    def test_french_runtime_failure_retains_code_and_localizes_action(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        args = ["--language", "fr", "capture", "--purchase", str(ROOT / "examples/manual/fr/purchases.csv"), "--output", str(self.folder / "no-confirmation"),
                "--task-id", "manual-fr", "--enterprise", "ENT-001", "--jurisdiction", "CA-ON", "--start", "2026-09-01", "--end", "2026-09-30",
                "--currency", "CAD", "--question", "Question", "--recipient", "Local", "--current-tool", "Papier", "--coverage", "complete"]
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(args)
        self.assertEqual(code, 2)
        failure = json.loads(stderr.getvalue())
        self.assertEqual(failure["error"], "capture.confirmations")
        self.assertEqual(failure["message"], error_text("fr", "capture.confirmations"))
        self.assertEqual(stdout.getvalue(), "")

    def test_cli_french_output_is_utf8_on_the_actual_host(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/reconcile.py"), "--language", "fr", "--help"], capture_output=True, check=True)
        output = result.stdout.decode("utf-8")
        self.assertIn("vérifiables", output)
        self.assertNotIn(chr(65533), output)


if __name__ == "__main__":
    unittest.main()
