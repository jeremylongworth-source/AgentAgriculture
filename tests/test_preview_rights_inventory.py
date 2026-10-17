"""Hash/membership/retained-notice evidence must not become release clearance."""

import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from inventory_preview_rights import inventory, sha256


class PreviewRightsInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="ag10-rights-")
        self.path = Path(self.temporary.name) / "synthetic-preview.zip"

    def tearDown(self):
        self.temporary.cleanup()

    def wheel(self, name, license_body, *, missing=False, expression=True):
        stream = io.BytesIO()
        root = name.replace("-", "_") + "-1.0.dist-info/"
        metadata = f"Metadata-Version: 2.4\nName: {name}\nVersion: 1.0\nLicense-File: LICENSE\n"
        metadata += "License-Expression: MIT\n" if expression else "License: Invented legacy declaration\n"
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr(root + "METADATA", metadata)
            if not missing:
                archive.writestr(root + "licenses/LICENSE", license_body)
        return stream.getvalue()

    def bundle(self, *, missing=False, bad_member=False, extra=False, project_drift=False):
        files = {"LICENSE": b"SYNTHETIC PRIVATE PROJECT TERMS",
                 "wheelhouse/project.whl": self.wheel("agent-agriculture", b"DRIFT" if project_drift else b"SYNTHETIC PRIVATE PROJECT TERMS"),
                 "wheelhouse/dependency.whl": self.wheel("invented-dependency", b"SYNTHETIC NOTICE", missing=missing, expression=False)}
        manifest = {"files": [{"path": name, "sha256": "0" * 64 if bad_member and name == "LICENSE" else sha256(raw), "bytes": len(raw)} for name, raw in files.items()]}
        with zipfile.ZipFile(self.path, "w") as archive:
            for name, raw in files.items(): archive.writestr(name, raw)
            archive.writestr("bundle-manifest.json", json.dumps(manifest))
            if extra: archive.writestr("UNDECLARED", b"not in manifest")
        return sha256(self.path.read_bytes())

    def test_metadata_fallback_and_retained_notices_do_not_claim_clearance(self):
        result = inventory(self.path, self.bundle())
        self.assertEqual(result["component_count"], 2)
        dependency = next(item for item in result["components"] if not item["project_component"])
        self.assertIsNone(dependency["license_expression"])
        self.assertEqual(dependency["legacy_license_field"], "Invented legacy declaration")
        self.assertTrue(dependency["declared_license_evidence"])
        self.assertFalse(dependency["redistribution_approved"])
        self.assertEqual(result["distribution_clearance"], "not_assessed")

    def test_wrong_archive_hash_stops_before_zip_parsing(self):
        self.bundle()
        with patch.object(zipfile, "ZipFile", side_effect=AssertionError("Unpinned bytes must not be parsed")), self.assertRaises(ValueError):
            inventory(self.path, "0" * 64)

    def test_missing_declared_notice_refuses_inventory(self):
        with self.assertRaises(ValueError): inventory(self.path, self.bundle(missing=True))

    def test_changed_manifest_or_extra_member_refuses_inventory(self):
        for change in ({"bad_member": True}, {"extra": True}):
            with self.subTest(change=change), self.assertRaises(ValueError): inventory(self.path, self.bundle(**change))

    def test_project_licence_must_match_root_without_becoming_distribution_permission(self):
        with self.assertRaises(ValueError): inventory(self.path, self.bundle(project_drift=True))


if __name__ == "__main__":
    unittest.main()
