import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation_tools.artifacts import (
    ASSIGNMENT, MAX_ARTIFACT_BYTES, checked_cell, commit, digest, put_chunk,
)

ROOT = Path(__file__).resolve().parents[1]


class EvaluationArtifactTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="synthetic-capture-", dir=ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)
        self.cell = Path(self.temporary.name).resolve()
        (self.cell / "outputs").mkdir()
        (self.cell / "input.json").write_text('{"synthetic_only":true,"value":"SYN-français"}', encoding="utf-8")
        inventory = {"input.json": digest((self.cell / "input.json").read_bytes())}
        (self.cell / "inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
        self.assignment = {"cell_id": "SYN-CAPTURE-CELL", "cell_root": str(self.cell), "synthetic_only": True,
                           "inventory_sha256": digest((self.cell / "inventory.json").read_bytes())}
        (self.cell / ASSIGNMENT).write_text(json.dumps(self.assignment), encoding="utf-8")
        self.cell_id = self.assignment["cell_id"]

    def put(self, name, raw, index=0, total=1):
        return put_chunk(self.cell, self.cell_id, name, index, total, base64.b64encode(raw).decode("ascii"))

    def finish(self, name, raw):
        return commit(self.cell, self.cell_id, name, digest(raw))

    def test_utf8_split_bytes_preserve_order_and_source(self):
        raw = "SYN local review. Révision fictive; aucune tâche exécutée.\n".encode("utf-8")
        before = (self.cell / "input.json").read_bytes()
        split = raw.index("é".encode("utf-8")) + 1
        self.put("brief.md", raw[split:], 1, 2)
        self.put("brief.md", raw[:split], 0, 2)
        receipt = self.finish("brief.md", raw)
        self.assertEqual((self.cell / "outputs/brief.md").read_bytes(), raw)
        self.assertEqual(receipt["absolute_destination"], str(self.cell / "outputs/brief.md"))
        self.assertEqual((self.cell / "input.json").read_bytes(), before)

    def test_strict_json_object_roundtrip(self):
        raw = '{"synthetic":true,"missing":null,"zero":"0","texte":"révision"}\n'.encode("utf-8")
        self.put("review.json", raw)
        self.finish("review.json", raw)
        self.assertEqual((self.cell / "outputs/review.json").read_bytes(), raw)

    def test_identical_retry_is_idempotent(self):
        raw = b"SYN local draft."
        self.put("brief.md", raw)
        self.assertEqual(self.put("brief.md", raw)["state"], "identical_chunk_retained")
        self.finish("brief.md", raw)
        self.assertEqual(self.finish("brief.md", raw)["state"], "identical_artifact_retained")

    def test_conflicting_chunk_preserves_first_bytes(self):
        self.put("brief.md", b"SYN first")
        with self.assertRaises(ValueError):
            self.put("brief.md", b"SYN other")
        self.assertEqual((self.cell / "outputs/.capture-parts/brief.md/chunk-000.bin").read_bytes(), b"SYN first")

    def test_conflicting_destination_preserves_existing_bytes(self):
        path = self.cell / "outputs/brief.md"
        path.write_bytes(b"SYN existing")
        self.put("brief.md", b"SYN new")
        with self.assertRaises(ValueError):
            self.finish("brief.md", b"SYN new")
        self.assertEqual(path.read_bytes(), b"SYN existing")

    def test_missing_chunk_prevents_final_file(self):
        self.put("brief.md", b"SYN part", 0, 2)
        with self.assertRaises(ValueError):
            self.finish("brief.md", b"SYN partmissing")
        self.assertFalse((self.cell / "outputs/brief.md").exists())

    def test_wrong_checksum_prevents_final_file(self):
        self.put("brief.md", b"SYN first")
        with self.assertRaises(ValueError):
            self.finish("brief.md", b"SYN second")
        self.assertFalse((self.cell / "outputs/brief.md").exists())

    def test_changed_source_stops_before_output_write(self):
        (self.cell / "input.json").write_text('{"synthetic_only":true,"changed":true}')
        with self.assertRaises(ValueError):
            self.put("brief.md", b"SYN draft")
        self.assertEqual(list((self.cell / "outputs").iterdir()), [])

    def test_changed_inventory_stops_before_output_write(self):
        (self.cell / "inventory.json").write_text('{}')
        with self.assertRaises(ValueError):
            self.put("brief.md", b"SYN draft")
        self.assertEqual(list((self.cell / "outputs").iterdir()), [])

    def test_relative_cell_and_wrong_assignment_are_refused(self):
        with self.assertRaises(ValueError):
            checked_cell(Path("outputs"), self.cell_id)
        with self.assertRaises(ValueError):
            put_chunk(self.cell, "SYN-WRONG", "brief.md", 0, 1, "U1lO")
        self.assignment["synthetic_only"] = False
        (self.cell / ASSIGNMENT).write_text(json.dumps(self.assignment))
        with self.assertRaises(ValueError):
            self.put("brief.md", b"SYN draft")
        self.assertEqual(list((self.cell / "outputs").iterdir()), [])

    def test_output_and_source_traversal_are_refused(self):
        for name in ("../brief.md", "extra.txt", "outputs/brief.md", "C:/brief.md"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.put(name, b"SYN draft")
        (self.cell / "inventory.json").write_text(json.dumps({"../input.json": "0" * 64}))
        self.assignment["inventory_sha256"] = digest((self.cell / "inventory.json").read_bytes())
        (self.cell / ASSIGNMENT).write_text(json.dumps(self.assignment))
        with self.assertRaises(ValueError):
            self.put("brief.md", b"SYN draft")
        self.assertEqual(list((self.cell / "outputs").iterdir()), [])

    def test_invalid_chunk_parameters_create_no_parts(self):
        for index, total, encoded in [(0, 0, "U1lO"), (0, 129, "U1lO"), (1, 1, "U1lO"),
                                      (True, 1, "U1lO"), (0, 1, "?"), (0, 1, ""), (0, 1, "A" * 4097)]:
            with self.subTest(index=index, total=total, encoded_length=len(encoded)), self.assertRaises(ValueError):
                put_chunk(self.cell, self.cell_id, "brief.md", index, total, encoded)
        self.assertEqual(list((self.cell / "outputs").iterdir()), [])

    def test_duplicate_nonfinite_and_nonobject_json_are_refused(self):
        for name, raw in [("review.json", b'{"x":1,"x":2}'), ("activity.json", b'{"x":NaN}')]:
            self.put(name, raw)
            with self.assertRaises(ValueError):
                self.finish(name, raw)
            self.assertFalse((self.cell / "outputs" / name).exists())

    def test_json_array_and_excessive_brief_are_refused(self):
        for name, raw in [("review.json", b"[]"), ("brief.md", b"SYN " * 551)]:
            self.put(name, raw)
            with self.assertRaises(ValueError):
                self.finish(name, raw)

    def test_extra_chunk_member_prevents_commit(self):
        self.put("brief.md", b"SYN draft")
        (self.cell / "outputs/.capture-parts/brief.md/extra.bin").write_bytes(b"SYN")
        with self.assertRaises(ValueError):
            self.finish("brief.md", b"SYN draft")

    def test_malformed_assignment_and_manifest_are_refused(self):
        (self.cell / ASSIGNMENT).write_text("[]")
        with self.assertRaises(ValueError):
            self.put("brief.md", b"SYN draft")
        (self.cell / ASSIGNMENT).write_text(json.dumps(self.assignment))
        self.put("brief.md", b"SYN draft")
        (self.cell / "outputs/.capture-parts/brief.md/manifest.json").write_text("[]")
        with self.assertRaises(ValueError):
            self.finish("brief.md", b"SYN draft")

    def test_linked_outputs_refused_without_os_settings_change(self):
        actual = Path.is_junction
        output = self.cell / "outputs"
        with patch.object(Path, "is_junction", lambda p: p == output or actual(p)):
            with self.assertRaises(ValueError):
                self.put("brief.md", b"SYN draft")
        self.assertEqual(list(output.iterdir()), [])

    def test_total_bytes_bound_refuses_additional_chunk(self):
        # Existing chunks are counted before accepting new bytes; no large input fixture.
        self.put("brief.md", b"SYN", 0, 2)
        stored = self.cell / "outputs/.capture-parts/brief.md/chunk-000.bin"
        stored.write_bytes(b"S" * MAX_ARTIFACT_BYTES)
        with self.assertRaises(ValueError):
            self.put("brief.md", b"SYN", 1, 2)
        self.assertFalse((self.cell / "outputs/.capture-parts/brief.md/chunk-001.bin").exists())
