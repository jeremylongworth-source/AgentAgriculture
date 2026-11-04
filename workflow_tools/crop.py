"""Preserve supplied crop observations and conservative measurement comparisons."""
from copy import deepcopy
from decimal import Decimal, localcontext
from datetime import date
from router.core import ROOT
from .common import acyclic, implementation_hash, instant, report, unique, validate


def run(data, language='en', root=ROOT):
    validate('crop-input',data,root)
    now=instant(data['as_of']);entities=unique(data['entities']);observations=unique(data['observations'])
    period_start,period_end=map(date.fromisoformat,[data['period']['start'],data['period']['end']])
    if period_start>period_end:
        raise ValueError('crop.period_invalid')
    unique(data['comparisons'])
    acyclic(observations,lambda x:[] if x['supersedes'] is None else [x['supersedes']])
    notes={key:[] for key in observations};eligible=set()
    for key,item in observations.items():
        if item['entity_id'] not in entities:
            raise ValueError('crop.unknown_entity')
        if item['supersedes'] is not None:
            old=observations[item['supersedes']]
            if old['entity_id']!=item['entity_id'] or old['metric']!=item['metric'] or instant(old['recorded_at'])>instant(item['recorded_at']):
                raise ValueError('crop.invalid_correction_lineage')
            if item['correction_reason'] is None:
                raise ValueError('crop.correction_reason_required')
        if item['value_state'] in {'missing','suppressed','trace'} and item['value'] is not None:
            raise ValueError('crop.non_numeric_state_value')
        if item['value_state'] in {'measured','estimated'} and item['value'] is None:
            raise ValueError('crop.numeric_value_missing')
        if item['value_state']!='measured':
            notes[key].append('value_'+item['value_state'])
        if item['observed_at'] is None:
            notes[key].append('observation_time_unknown')
        elif not period_start <= instant(item['observed_at']).date() <= period_end:
            notes[key].append('outside_declared_period_utc')
        if item['event_state']!='observed':
            notes[key].append('event_not_observed')
        if instant(item['recorded_at'])>now:
            notes[key].append('recorded_after_as_of')
        elif item['observed_at'] is not None and instant(item['observed_at'])>now:
            notes[key].append('observation_after_as_of')
        else:
            eligible.add(key)
    children={key:[] for key in observations}
    for key in eligible:
        parent=observations[key]['supersedes']
        if parent is not None:
            children[parent].append(key)
    conflicted=set();superseded=set()
    def mark(key):
        conflicted.add(key)
        for child in children[key]:
            mark(child)
    for key,values in children.items():
        if len(values)>1:
            mark(key)
        elif values:
            superseded.add(key)
    for key in conflicted:
        notes[key].append('correction_fork')
    active=(eligible-superseded)| (conflicted&eligible)
    # Unknown observation time remains undated; do not substitute transcription time.
    ordered=sorted(observations,key=lambda key:(observations[key]['observed_at'] is None,
                    instant(observations[key]['observed_at']) if observations[key]['observed_at'] else now,key))
    result=report('crop-production-review',data,language)
    result['entities']=deepcopy(data['entities'])
    result['observations']=[{'original':deepcopy(observations[key]),'current_as_of':key in active,
                            'superseded_by':sorted(children[key]),'issues':notes[key]} for key in ordered]
    result['current_ids']=sorted(active);result['comparisons']=[]
    fields=['entity_id','metric','unit','method','basis','sampling_scope']
    for comparison in data['comparisons']:
        left=observations.get(comparison['left']);right=observations.get(comparison['right']);reasons=[]
        if left is None or right is None:
            reasons.append('observation_reference_missing')
        else:
            for item in [left,right]:
                if item['id'] not in active:
                    reasons.append('observation_not_current_as_of')
                if item['id'] in conflicted:
                    reasons.append('correction_fork')
                if item['value_state']!='measured':
                    reasons.append('value_not_measured')
                if item['event_state']!='observed':
                    reasons.append('event_not_observed')
                if item['observed_at'] is None:
                    reasons.append('observation_time_unknown')
                if 'outside_declared_period_utc' in notes[item['id']]:
                    reasons.append('observation_outside_declared_period_utc')
            for field in fields:
                if left[field] is None or right[field] is None:
                    reasons.append('metadata_missing:'+field)
                elif left[field]!=right[field]:
                    reasons.append('metadata_mismatch:'+field)
        difference=None
        if not reasons:
            with localcontext() as ctx:
                ctx.prec=160
                difference=format(Decimal(right['value'])-Decimal(left['value']),'f')
        result['comparisons'].append({'comparison_id':comparison['id'],'left':comparison['left'],'right':comparison['right'],
             'status':'arithmetic_only' if not reasons else 'unresolved','difference_right_minus_left':difference,
             'unit':left['unit'] if left else None,'issues':sorted(set(reasons)),
             'source_refs':list(dict.fromkeys([x['source_ref'] for x in [left,right] if x is not None])),
             'interpretation':'not_established'})
    result['state']='review_draft_with_gaps' if any(notes.values()) or any(x['issues'] for x in result['comparisons']) else 'review_draft'
    result['required_reviews']=['confirm_entity_observation_method_and_source_meaning','resolve_conflicts_and_missing_context',
                                'professional_interpretation_if_requested','inspect_notes_and_recipient_scope_before_sharing']
    result['implementation_sha256']=implementation_hash(__file__)
    return result
