"""Select a broader local candidate from an explicit recipe; never publish."""
import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare_public_preview import selected_source, safe_name
from public_provenance import transform, validate_structured_references

ROOT = Path(__file__).resolve().parents[1]
RECIPE = 'docs/release/ecosystem-files.json'


def inspect(root=ROOT):
    root = Path(root).resolve()
    recipe = json.loads(selected_source(root, RECIPE).read_bytes())
    if recipe['publication_authorized'] is not False:
        raise ValueError('local recipe must not grant publication authority')
    payloads = {}
    entries = []
    for item in recipe['files']:
        name = item['path']; safe_name(name)
        if name in payloads:
            raise ValueError('duplicate target')
        raw = selected_source(root, item.get('source', name)).read_bytes()
        source_hash = hashlib.sha256(raw).hexdigest()
        if item.get('export_transform'):
            raw = transform(name, raw, item['export_transform'])
        payloads[name] = raw
        entries.append({'path': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                        'source_sha256': source_hash, 'source': item.get('source', name),
                        'export_transform': item.get('export_transform')})
    # A copied tree rebuilds from its exported bytes, without private aliases or
    # applying canonical-to-public transforms a second time.
    exported_recipe = {**recipe, 'files': [{'path': n, 'category': 'ecosystem_source',
                        'rights_review': 'MIT_project_owned_or_separate_notices'} for n in sorted(payloads)]}
    for name in (RECIPE, 'docs/release/public-preview-files.json'):
        payloads[name] = (json.dumps(exported_recipe, ensure_ascii=False, indent=2) + '\n').encode()
    links = 0
    for name, raw in payloads.items():
        if not name.endswith('.md'):
            continue
        text = raw.decode('utf-8')
        for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)', text):
            if '://' in target or target.startswith('#'):
                continue
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target.split('#', 1)[0])).rstrip('/')
            if resolved not in payloads and not any(p.startswith(resolved + '/') for p in payloads):
                raise ValueError('unselected link: ' + name + ' -> ' + target)
            links += 1
    validate_structured_references(payloads)
    inventory = [{'path': n, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                 for n, raw in sorted(payloads.items())]
    identity = hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'scope': 'ecosystem_developer_preview_candidate', 'publication_authorized': False,
            'tree_sha256': identity, 'files': inventory, 'local_links': links,
            'source_exports': entries}, payloads


def stage(destination, root=ROOT):
    root = Path(root).resolve(); destination = Path(destination).absolute()
    if not destination.is_relative_to(root / 'outputs') or '..' in destination.parts:
        raise ValueError('use a new project outputs directory')
    if destination.exists() or any(p.is_symlink() or p.is_junction() for p in (destination, *destination.parents)):
        raise ValueError('existing or linked destination')
    report, payloads = inspect(root)
    destination.mkdir(parents=True, exist_ok=False)
    for name, raw in payloads.items():
        path = destination / name; path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    (destination / 'CANDIDATE-MANIFEST.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def verify(folder):
    folder = Path(folder).resolve()
    report = json.loads((folder / 'CANDIDATE-MANIFEST.json').read_bytes())
    if report.get('publication_authorized') is not False:
        raise ValueError('manifest cannot grant publication authority')
    seen = set()
    for entry in report['files']:
        name = entry['path']; safe_name(name)
        if name in seen:
            raise ValueError('duplicate member')
        seen.add(name)
        raw = selected_source(folder, name).read_bytes()
        if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('changed candidate member: ' + name)
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()}
    if actual != seen | {'CANDIDATE-MANIFEST.json'}:
        raise ValueError('unexpected or missing candidate member')
    identity = hashlib.sha256(json.dumps(report['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if identity != report['tree_sha256']:
        raise ValueError('inventory identity mismatch')
    return {'state':'verified_local_candidate', 'tree_sha256':identity,
            'members':len(seen), 'publication_authorized':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--destination', type=Path)
    group.add_argument('--verify-candidate', type=Path)
    args = parser.parse_args()
    try:
        if args.verify_candidate:
            print(json.dumps(verify(args.verify_candidate))); return
        report = stage(args.destination) if args.destination else inspect()[0]
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, 'Candidate refused: ' + str(exc) + '\n')
    print(json.dumps({'tree_sha256': report['tree_sha256'], 'members': len(report['files']),
                      'local_links': report['local_links'], 'publication_authorized': False}))


if __name__ == '__main__':
    main()
