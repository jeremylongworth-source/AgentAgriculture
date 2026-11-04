from datetime import date, datetime, timezone
from copy import deepcopy
import hashlib
from pathlib import Path
import re
from router.core import ROOT, issues, schema


def validate(name, data, root=ROOT):
    found = issues(schema(Path(root), name), data)
    if found:
        raise ValueError('workflow.input_invalid:' + ','.join(found))
    if isinstance(data,dict) and data.get('period') and date.fromisoformat(data['period']['start'])>date.fromisoformat(data['period']['end']):
        raise ValueError('workflow.period_invalid')


def instant(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if value.utcoffset() is None:
        raise ValueError('workflow.offset_required')
    return value.astimezone(timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def unique(items, key='id'):
    answer = {}
    for item in items:
        if item[key] in answer:
            raise ValueError('workflow.duplicate_id')
        answer[item[key]] = item
    return answer


def acyclic(items, dependencies):
    active, visited = set(), set()
    def visit(key):
        if key in active:
            raise ValueError('workflow.dependency_cycle')
        if key in visited:
            return
        active.add(key)
        for dependency in dependencies(items[key]):
            if dependency not in items:
                raise ValueError('workflow.unknown_dependency')
            visit(dependency)
        active.remove(key); visited.add(key)
    for key in items:
        visit(key)


def report(workflow, data, language):
    if language not in {'en','fr'}:
        raise ValueError('workflow.language_unsupported')
    return {'schema_version': '1.0.0', 'workflow': workflow, 'task_id': data['task_id'],
            'language': language, 'method_version': '0.1.2', 'synthetic': True,
            'context': {**{key:deepcopy(data[key]) for key in ['enterprise_id','jurisdiction','period','as_of']},
                        'period_date_basis':'UTC'},
            'execution_allowed': False, 'operational_advice_allowed': False,
            'field_use_validated': False, 'user_review_required': True,
            'required_reviews': [], 'issues': []}


def safe_markdown(value):
    """Presentation-only escaping; retain original strings in canonical JSON."""
    value = str(value).replace('\r', ' ').replace('\n', ' ')
    return re.sub(r'([\\`*_{}\[\]()#+.!|<>-])', r'\\\1', value)


def implementation_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
