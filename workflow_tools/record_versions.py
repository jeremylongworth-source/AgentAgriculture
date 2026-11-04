"""As-of revision selection for explicitly supplied local evidence, never source truth."""
from .common import acyclic,instant,unique


def select(records,as_of,identity_fields):
    by_id=unique(records);acyclic(by_id,lambda x:[] if x['supersedes'] is None else [x['supersedes']])
    cutoff=instant(as_of);eligible=set();issues={key:[] for key in by_id}
    for key,item in by_id.items():
        if item['supersedes'] is not None:
            parent=by_id[item['supersedes']]
            if any(parent[f]!=item[f] for f in identity_fields) or instant(parent['recorded_at'])>instant(item['recorded_at']):
                raise ValueError('workflow.invalid_correction_lineage')
            if item['correction_reason'] is None:
                raise ValueError('workflow.correction_reason_required')
        if instant(item['recorded_at'])>cutoff:issues[key].append('recorded_after_as_of')
        elif item['observed_at'] is not None and instant(item['observed_at'])>cutoff:issues[key].append('observation_after_as_of')
        else:eligible.add(key)
    children={key:[] for key in by_id}
    for key in eligible:
        parent=by_id[key]['supersedes']
        if parent is not None:children[parent].append(key)
    conflicted=set();superseded=set()
    def mark(key):
        conflicted.add(key)
        for child in children[key]:mark(child)
    for key,values in children.items():
        if len(values)>1:mark(key)
        elif values:superseded.add(key)
    for key in conflicted:issues[key].append('correction_fork')
    # A fork has no uniquely current revision. Retain every candidate with its
    # conflict issue, but never label parent/children as current evidence.
    return by_id,(eligible-superseded)-conflicted,children,issues
