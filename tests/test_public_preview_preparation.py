"""Material source-release selection and draft-integrity failures; no publishing."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from copy import deepcopy
import hashlib
import shutil
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agent_agriculture.contracts import Contracts
spec = importlib.util.spec_from_file_location("public_draft", ROOT / "scripts/prepare_public_preview.py")
draft = importlib.util.module_from_spec(spec)
spec.loader.exec_module(draft)


class PublicDraftTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "outputs").mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="ag-public-draft-", dir=ROOT / "outputs")
        self.root = Path(self.temporary.name).resolve()
        entries = []
        for name in sorted(draft.REQUIRED | {"docs/start.md"}):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = b"No public redistribution licence is granted" if name == "LICENSE" else b"synthetic fixture\n"
            if name == "README.md": raw = b"[Start](docs/start.md)\n"
            path.write_bytes(raw)
            entries.append({"path": name, "category": "synthetic-test", "rights_review": "pending"})
        self.inventory = {"status": "private_local_draft_only", "files": entries}
        self.save()

    def save(self):
        path = self.root / draft.INVENTORY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.inventory), encoding="utf-8")

    def tearDown(self):
        self.assertTrue(self.root.name.startswith("ag-public-draft-"))
        self.assertTrue(self.root.is_relative_to((ROOT / "outputs").resolve()))
        self.temporary.cleanup()

    def test_selected_only_hashes_and_open_owner_decisions_survive_staging(self):
        (self.root / "private").mkdir()
        (self.root / "private/unselected.txt").write_text("must stay out")
        result = draft.stage_draft(self.root / "outputs/source", self.root)
        self.assertFalse(result["public_release_ready"])
        self.assertFalse(result["publication_authorized"])
        self.assertTrue(result["project_license_private_only"])
        self.assertEqual(len(result["open_owner_gates"]), 4)
        self.assertFalse(result["reporting_activation_verified"])
        self.assertEqual(draft.verify_draft(result["draft_path"])["files"], len(self.inventory["files"]))
        self.assertFalse((Path(result["draft_path"]) / "private").exists())

    def test_source_mapping_is_explicit_and_link_closure_uses_target_names(self):
        (self.root / "docs/public-readme.md").write_text("[Start](docs/start.md)\n", encoding="utf-8")
        next(e for e in self.inventory["files"] if e["path"] == "README.md")["source"] = "docs/public-readme.md"
        self.save()
        _, payloads = draft.inspect(self.root)
        self.assertEqual(payloads["README.md"], (self.root / "docs/public-readme.md").read_bytes())

    def mit_fixture(self):
        self.inventory.update(status="local_source_candidate_only", project_license_expression="MIT",
                              reporting_route_selected="https://github.com/jeremylongworth-source/AgentAgriculture",
                              reporting_activation_verified=True)
        (self.root / "pyproject.toml").write_text('[project]\nlicense = "MIT"\nlicense-files = ["LICENSE", "THIRD_PARTY_NOTICES.md"]\n')
        (self.root / "LICENSE").write_text("MIT License\nSynthetic licence fixture; no legal assertion.\n")
        (self.root / "THIRD_PARTY_NOTICES.md").write_text("Synthetic scope fixture\n")
        self.inventory["files"].append({"path": "THIRD_PARTY_NOTICES.md", "category": "synthetic-test", "rights_review": "pending"})
        self.save()

    def test_mit_choice_and_selected_target_never_grant_publication_or_remote_status(self):
        self.mit_fixture()
        result=draft.stage_draft(self.root / "outputs/mit", self.root)
        self.assertEqual(result["project_license_expression"], "MIT")
        self.assertFalse(result["project_license_private_only"])
        self.assertEqual(result["reporting_route_selected"], self.inventory["reporting_route_selected"])
        self.assertFalse(result["reporting_activation_verified"])
        self.assertFalse(result["public_release_ready"])
        self.assertFalse(result["publication_authorized"])

    def test_mit_candidate_refuses_private_terms_or_dropped_notices(self):
        self.mit_fixture()
        original=(self.root / "LICENSE").read_bytes()
        (self.root / "LICENSE").write_bytes(b"No public redistribution licence is granted")
        with self.assertRaises(ValueError): draft.inspect(self.root)
        (self.root / "LICENSE").write_bytes(original)
        self.inventory["files"]=[e for e in self.inventory["files"] if e["path"]!="THIRD_PARTY_NOTICES.md"]
        self.save()
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_mit_inventory_cannot_mislabel_package_license(self):
        self.mit_fixture()
        (self.root / "pyproject.toml").write_text('[project]\nlicense = "Other"\n')
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_forged_reporting_activation_manifest_is_refused(self):
        self.mit_fixture()
        result=draft.stage_draft(self.root / "outputs/mit", self.root)
        path=Path(result["draft_path"]) / "DRAFT-MANIFEST.json"
        manifest=json.loads(path.read_text());manifest["reporting_activation_verified"]=True
        path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError): draft.verify_draft(path.parent)

    def test_private_history_study_generated_and_escape_paths_refused_before_read(self):
        for name in ("../outside", ".git/config", "docs/research/R01.md", "docs/studies/forms.md", "templates/study/consent.md", "subprojects/field-study/roadmap.md", "outputs/result.json", "secrets.key", "D:/outside"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                draft.safe_name(name)

    def test_duplicate_or_missing_mandatory_source_refused(self):
        self.inventory["files"].append(dict(self.inventory["files"][0]))
        self.save()
        with self.assertRaises(ValueError): draft.inspect(self.root)
        self.inventory["files"] = [e for e in self.inventory["files"][:-1] if e["path"] != "LICENSE"]
        self.save()
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_broken_public_document_link_refused(self):
        (self.root / "README.md").write_text("[Private](docs/studies/notes.md)\n", encoding="utf-8")
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_linked_member_refused_without_following_target(self):
        real = Path.is_symlink
        with patch.object(Path, "is_symlink", lambda p: p.name == "LICENSE" or real(p)):
            with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_existing_or_outside_destination_never_overwritten(self):
        destination = self.root / "outputs/source"
        destination.mkdir(parents=True)
        marker = destination / "keep.txt"; marker.write_bytes(b"keep")
        for target in (destination, self.root / "outside"):
            with self.subTest(target=target), self.assertRaises(ValueError): draft.stage_draft(target, self.root)
        self.assertEqual(marker.read_bytes(), b"keep")
        self.assertFalse(list(destination.parent.glob(".public-draft-*")))

    def test_changed_or_extra_member_and_forged_ready_flag_refused(self):
        destination = self.root / "outputs/source"
        draft.stage_draft(destination, self.root)
        original = (destination / "LICENSE").read_bytes()
        (destination / "LICENSE").write_bytes(b"changed")
        with self.assertRaises(ValueError): draft.verify_draft(destination)
        (destination / "LICENSE").write_bytes(original)
        extra = destination / "unselected.txt"; extra.write_bytes(b"extra")
        with self.assertRaises(ValueError): draft.verify_draft(destination)
        extra.unlink()
        manifest_path = destination / "DRAFT-MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["publication_authorized"] = True
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError): draft.verify_draft(destination)

    def add_member(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        if not any(e["path"] == name for e in self.inventory["files"]):
            self.inventory["files"].append({"path": name, "category": "synthetic-test", "rights_review": "pending"})
        self.save()

    def test_structured_private_reference_refused_even_when_file_exists_outside_selection(self):
        hidden = self.root / "docs/research/R04.md"
        hidden.parent.mkdir(parents=True)
        hidden.write_bytes(b"not selected")
        self.add_member("registries/sources.yaml", b"sources:\n- source_id: SYN\n  evidence:\n    report: docs/research/R04.md\n")
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_coverage_and_workflow_structured_paths_are_checked_and_directories_work(self):
        self.add_member("registries/coverage.yaml", b"jurisdictions:\n- jurisdiction: SYN\n  evidence: [docs/start.md]\n")
        self.add_member("registries/workflows.yaml", b"workflows:\n- workflow_id: SYN\n  evidence: [docs/]\n")
        report, _ = draft.inspect(self.root)
        self.assertEqual(report["structured_evidence_references"]["checked"], 2)
        self.add_member("registries/workflows.yaml", b"workflows:\n- workflow_id: SYN\n  evidence: [../outside]\n")
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_duplicate_yaml_metadata_cannot_hide_an_earlier_reference(self):
        self.add_member("registries/sources.yaml", b"sources: []\nsources: []\n")
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_declared_export_is_idempotent_and_preserves_historical_fields(self):
        import public_provenance as provenance
        raw = (ROOT / "registries/sources.yaml").read_bytes()
        original = yaml.safe_load(raw)
        exported = provenance.transform("registries/sources.yaml", raw, provenance.EXPORT_ID)
        changed = yaml.safe_load(exported)
        for before, after in zip(original["sources"], changed["sources"]):
            expected = deepcopy(before)
            expected["evidence"]["report"] = provenance.INDEX
            self.assertEqual(after, expected)
            self.assertNotEqual(after["evidence"]["state"], "O")
            self.assertIsNone(after["rights"]["redistribution"])
        self.assertEqual(provenance.transform("registries/sources.yaml", exported, provenance.EXPORT_ID), exported)
        self.assertEqual((ROOT / "registries/sources.yaml").read_bytes(), raw)

    def test_unknown_or_unrelated_export_transform_is_refused(self):
        self.inventory["files"][0]["export_transform"] = "unrecognized"
        self.save()
        with self.assertRaises(ValueError): draft.inspect(self.root)
        self.inventory["files"][0]["export_transform"] = "public-provenance-v1"
        self.save()
        with self.assertRaises(ValueError): draft.inspect(self.root)

    def test_export_schema_accepts_only_historical_or_public_report_locations(self):
        import public_provenance as provenance
        contract_root = self.root / "contract-check"
        schema_root = contract_root / "schemas/v1"
        schema_root.mkdir(parents=True)
        for source in (ROOT / "schemas/v1").glob("*.json"):
            shutil.copyfile(source, schema_root / source.name)
        schema = schema_root / "source-registry.schema.json"
        schema.write_bytes(provenance.transform(provenance.REGISTRY_SCHEMA, schema.read_bytes(), provenance.EXPORT_ID))
        contracts = Contracts(contract_root)
        registry = yaml.safe_load((ROOT / "registries/sources.yaml").read_text(encoding="utf-8"))
        for report in [provenance.HISTORICAL_REPORT, provenance.INDEX]:
            with self.subTest(report=report):
                for source in registry["sources"]: source["evidence"]["report"] = report
                self.assertFalse(contracts.validate("source-registry", registry))
        registry["sources"][0]["evidence"]["report"] = "docs/other.md"
        self.assertTrue(contracts.validate("source-registry", registry))

    def test_public_index_cannot_promote_or_change_historical_source_assertions(self):
        import public_provenance as provenance
        _, payloads = draft.inspect(ROOT)
        index = json.loads(payloads[provenance.INDEX])
        index["sources"][0]["public_evidence_status"] = "operationally_verified"
        payloads[provenance.INDEX] = json.dumps(index).encode()
        with self.assertRaises(ValueError): provenance.validate_structured_references(payloads)

    def test_verifier_rejects_broken_structured_reference_even_after_hashes_are_rewritten(self):
        self.add_member("registries/sources.yaml", b"sources:\n- source_id: SYN\n  evidence:\n    report: docs/start.md\n")
        destination = self.root / "outputs/source"
        draft.stage_draft(destination, self.root)
        raw = b"sources:\n- source_id: SYN\n  evidence:\n    report: docs/missing.md\n"
        (destination / "registries/sources.yaml").write_bytes(raw)
        path = destination / "DRAFT-MANIFEST.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        entry = next(e for e in manifest["files"] if e["path"] == "registries/sources.yaml")
        entry.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaises(ValueError): draft.verify_draft(destination)


if __name__ == "__main__":
    unittest.main()
