"""Validate portable compositions and route explicit task context, never execute it."""
from datetime import date
import hashlib
import json
from pathlib import Path, PurePosixPath

from jsonschema import Draft202012Validator, FormatChecker
import yaml

ROOT = Path(__file__).resolve().parents[1]
MAX_DOCUMENT_BYTES = 256 * 1024
ALLOWED_CONTEXT_FIELDS = frozenset({'enterprise_id', 'jurisdiction', 'period'})
UNSUPPORTED_ACTIONS = frozenset({'send_message', 'submit_filing', 'purchase', 'control_equipment',
                                'clinical_prescription', 'agronomic_prescription', 'certify'})
TEXT = {
    'input.invalid': ('The task context is invalid; correct the listed fields.', 'Le contexte est invalide ; corrigez les champs indiqués.'),
    'route.scope': ('The requested action exceeds preparation scope. Retain the evidence and seek the appropriate authorized review.', 'L’action demandée dépasse la préparation. Conservez les preuves et demandez la révision autorisée appropriée.'),
    'route.context': ('Clarify the missing task context before selecting this workflow.', 'Précisez le contexte manquant avant de choisir ce parcours.'),
    'route.unavailable': ('This workflow is not implemented in this catalog. No operational support is inferred.', 'Ce parcours ne figure pas dans ce catalogue. Aucun soutien opérationnel n’est présumé.'),
    'route.ready': ('The selected skills can prepare a review; inspect scope, omissions and required checks before using outputs.', 'Les compétences choisies peuvent préparer une révision ; vérifiez la portée, les omissions et les contrôles requis avant utilisation.'),
}


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('document.duplicate_key')
        result[key] = value
    return result


class UniqueLoader(yaml.SafeLoader):
    pass


UniqueLoader.add_constructor('tag:yaml.org,2002:map',
                             lambda loader, node: unique_pairs(loader.construct_pairs(node, deep=True)))


def read_document(path):
    """Bounded selected control document read; no credential or data-source access."""
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(raw) > MAX_DOCUMENT_BYTES:
        raise ValueError('document.too_large')
    text = raw.decode('utf-8-sig')
    if Path(path).suffix.lower() in {'.yaml', '.yml'}:
        return yaml.load(text, Loader=UniqueLoader)
    return json.loads(text, object_pairs_hook=unique_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('document.nonfinite')))


def member(root, name, prefix=None):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('catalog.unsafe_path')
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or str(parts) != name:
        raise ValueError('catalog.unsafe_path')
    if prefix and not name.startswith(prefix):
        raise ValueError('catalog.wrong_path_scope')
    path = root / name
    if not path.is_file() or any(root.joinpath(*parts.parts[:n]).is_symlink() for n in range(1, len(parts.parts) + 1)):
        raise ValueError('catalog.missing_or_linked_member')
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('catalog.unsafe_path')
    return path


def schema(root, name):
    value = read_document(root / 'schemas/ecosystem/v1' / (name + '.schema.json'))
    Draft202012Validator.check_schema(value)
    return Draft202012Validator(value, format_checker=FormatChecker())


def issues(validator, document):
    return sorted({'/'.join(map(str, e.absolute_path)) or '$' for e in validator.iter_errors(document)})


class Catalog:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.context_validator = schema(self.root, 'context')
        self.result_validator = schema(self.root, 'result')
        self.manifest_validator = schema(self.root, 'composition')
        self.document = read_document(self.root / 'router/catalog.json')
        self.skills, self.compositions = {}, {}
        if set(self.document) != {'schema_version', 'skills', 'workflows'} or self.document['schema_version'] != '1.0.0':
            raise ValueError('catalog.shape')
        for item in self.document['skills']:
            if set(item) != {'id', 'path'} or item['id'] in self.skills:
                raise ValueError('catalog.duplicate_or_invalid_skill')
            path = member(self.root, item['path'], 'skills/')
            text = path.read_text(encoding='utf-8')
            pieces = text.split('---', 2)
            if len(pieces) != 3 or pieces[0].strip() or yaml.load(pieces[1], Loader=UniqueLoader).get('name') != item['id']:
                raise ValueError('catalog.skill_identity')
            self.skills[item['id']] = item['path']
        ids = set()
        for workflow, path in self.document['workflows'].items():
            if workflow not in self.context_validator.schema['properties']['workflow']['enum'] or workflow == 'unknown':
                raise ValueError('catalog.unknown_workflow')
            manifest = read_document(member(self.root, path, 'skillsets/'))
            if issues(self.manifest_validator, manifest) or manifest['workflow'] != workflow or manifest['id'] in ids:
                raise ValueError('catalog.invalid_manifest')
            ids.add(manifest['id'])
            steps = manifest['steps']
            step_ids = [s['id'] for s in steps]
            if len(set(step_ids)) != len(step_ids):
                raise ValueError('catalog.duplicate_step')
            by_id = {s['id']: s for s in steps}
            for step in steps:
                if step['skill'] not in self.skills or any(x not in by_id for x in step['depends_on']):
                    raise ValueError('catalog.unresolved_dependency')
            visited, active = set(), set()
            def visit(key):
                if key in active:
                    raise ValueError('catalog.dependency_cycle')
                if key in visited:
                    return
                active.add(key)
                for dependency in by_id[key]['depends_on']:
                    visit(dependency)
                active.remove(key); visited.add(key)
            for key in step_ids:
                visit(key)
            # Listed order is the portable execution order, not an ignored display order.
            seen = set()
            for step in steps:
                if not set(step['depends_on']) <= seen:
                    raise ValueError('catalog.dependency_order')
                seen.add(step['id'])
            if not set(manifest['requires_context']) <= ALLOWED_CONTEXT_FIELDS:
                raise ValueError('catalog.unknown_context_requirement')
            for reference in manifest['references']:
                member(self.root, reference)
            self.compositions[workflow] = manifest
        identity = {'catalog': self.document, 'compositions': self.compositions,
                    'skill_bytes': {key: hashlib.sha256((self.root / path).read_bytes()).hexdigest() for key, path in self.skills.items()},
                    'reference_bytes': {path: hashlib.sha256((self.root / path).read_bytes()).hexdigest()
                                        for path in sorted({p for m in self.compositions.values() for p in m['references']})},
                    'context_schema': self.context_validator.schema, 'result_schema': self.result_validator.schema,
                    'composition_schema': self.manifest_validator.schema}
        self.digest = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

    def context_issues(self, context):
        found = issues(self.context_validator, context)
        if not found and context['period'] is not None and date.fromisoformat(context['period']['start']) > date.fromisoformat(context['period']['end']):
            found.append('period/order')
        return found

    def route(self, context):
        invalid = self.context_issues(context)
        language = context.get('language', 'en') if isinstance(context, dict) else 'en'
        language = language if isinstance(language, str) and language in {'en', 'fr'} else 'en'
        task = context.get('task_id') if isinstance(context, dict) else None
        workflow = context.get('workflow') if isinstance(context, dict) else None
        result = {'schema_version': '1.0.0', 'task_id': task if isinstance(task, str) and 0 < len(task) <= 80 else 'invalid-context',
                  'workflow': workflow if isinstance(workflow, str) and len(workflow) <= 80 else 'unknown',
                  'language': language, 'state': 'input_invalid', 'composition_id': None, 'skills': [],
                  'missing_context': invalid, 'review_requirements': [], 'messages': [],
                  'execution_allowed': False, 'operational_advice_allowed': False, 'field_use_validated': False,
                  'permissions_enforced': False, 'catalog_sha256': self.digest}
        code = 'input.invalid'
        if not invalid:
            actions = set(context['requested_actions'])
            if actions & UNSUPPORTED_ACTIONS or context['intent'] in {'execute_external', 'interpret_operational'}:
                result['state'], code = 'blocked_scope', 'route.scope'
            elif context['intent'] == 'unknown' or context['consequence'] == 'unknown' or 'unknown' in actions or workflow == 'unknown':
                result['state'], code = 'needs_context', 'route.context'
                result['missing_context'] = [key for key in ['intent', 'consequence', 'workflow'] if context[key] == 'unknown']
                if 'unknown' in actions:
                    result['missing_context'].append('requested_actions')
            elif workflow not in self.compositions:
                result['state'], code = 'not_implemented', 'route.unavailable'
            else:
                manifest = self.compositions[workflow]
                # Explaining a workflow does not require collecting a farm profile.
                missing = [] if context['intent'] == 'explain' else [key for key in manifest['requires_context'] if context[key] is None or context[key] == 'unknown']
                if missing:
                    result['state'], code = 'needs_context', 'route.context'
                    result['missing_context'] = missing
                else:
                    result['state'], code = 'ready_for_preparation', 'route.ready'
                    result['composition_id'] = manifest['id']
                    result['skills'] = [s['skill'] for s in manifest['steps']]
                    result['review_requirements'] = (['information_only_no_record_processing'] if context['intent'] == 'explain'
                                                     else list(manifest['review_requirements']))
                    if context['consequence'] == 'operational':
                        result['review_requirements'].append('qualified_domain_interpretation')
        result['messages'] = [{'code': code, 'text': TEXT[code][language == 'fr']}]
        if issues(self.result_validator, result):
            raise ValueError('router.invalid_result')
        return result
