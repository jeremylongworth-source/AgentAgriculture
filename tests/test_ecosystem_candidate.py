"""Broader source candidate closure, rebuild and refusal boundaries."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('ecosystem_candidate', ROOT / 'scripts/prepare_ecosystem_preview.py')
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)


class EcosystemCandidateTests(unittest.TestCase):
    def setUp(self):
        (ROOT / 'outputs').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'outputs')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve() / 'candidate source épreuve'

    def test_complete_tree_rebuilds_from_exported_bytes(self):
        report = candidate.stage(self.base)
        verified = candidate.verify(self.base)
        self.assertEqual(verified['tree_sha256'], report['tree_sha256'])
        rebuilt, _ = candidate.inspect(self.base)
        self.assertEqual(rebuilt['tree_sha256'], report['tree_sha256'])
        self.assertFalse(verified['publication_authorized'])
        catalog = json.loads((self.base / 'router/catalog.json').read_text())
        self.assertEqual(len(catalog['skills']), 17)
        self.assertEqual(len(catalog['workflows']), 7)
        self.assertFalse((self.base / 'docs/research').exists())
        self.assertFalse((self.base / '.git').exists())

    def test_changed_and_extra_members_are_refused(self):
        candidate.stage(self.base)
        path = self.base / 'README.md'; original = path.read_bytes()
        path.write_bytes(original + b'\nSYNTHETIC TEST CHANGE\n')
        with self.assertRaisesRegex(ValueError, 'changed candidate'):
            candidate.verify(self.base)
        path.write_bytes(original)
        (self.base / 'unexpected.txt').write_text('SYNTHETIC unselected data')
        with self.assertRaisesRegex(ValueError, 'unexpected or missing'):
            candidate.verify(self.base)

    def test_existing_and_outside_destination_refused(self):
        self.base.mkdir()
        marker = self.base / 'keep.txt'; marker.write_text('SYNTHETIC existing')
        with self.assertRaises(ValueError):
            candidate.stage(self.base)
        self.assertEqual(marker.read_text(), 'SYNTHETIC existing')
        with self.assertRaises(ValueError):
            candidate.stage(ROOT / 'not-an-output')

    def test_private_alias_and_manifest_authority_refused(self):
        fixture = Path(self.temp.name) / 'fixture'
        recipe = fixture / candidate.RECIPE; recipe.parent.mkdir(parents=True)
        recipe.write_text(json.dumps({'publication_authorized':False,
            'files':[{'path':'README.md','source':'private/data.txt'}]}))
        with self.assertRaises(ValueError):
            candidate.inspect(fixture)
        candidate.stage(self.base)
        path = self.base / 'CANDIDATE-MANIFEST.json'
        report = json.loads(path.read_text()); report['publication_authorized'] = True
        path.write_text(json.dumps(report))
        with self.assertRaisesRegex(ValueError, 'publication authority'):
            candidate.verify(self.base)


if __name__ == '__main__':
    unittest.main()
