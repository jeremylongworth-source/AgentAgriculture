"""Supplied-basis animal/group/feed record review; no clinical or feeding decisions."""
from copy import deepcopy
from datetime import date
from decimal import Decimal,localcontext
from router.core import ROOT
from .common import implementation_hash,instant,report,unique,validate
from .record_versions import select


def age_seconds(now,observed_at):
    if observed_at is None:return None
    delta=now-instant(observed_at)
    return format(Decimal(delta.days*86400+delta.seconds)+Decimal(delta.microseconds)/Decimal(1000000),'f')


def run(data,language='en',root=ROOT):
    validate('livestock-input',data,root)
    entities=unique(data['entities']);unique(data['reviews']);now=instant(data['as_of'])
    by_id,current,children,notes=select(data['records'],data['as_of'],['entity_id','kind'])
    start,end=map(date.fromisoformat,[data['period']['start'],data['period']['end']])
    for key,item in by_id.items():
        if item['entity_id'] not in entities:raise ValueError('workflow.unknown_entity')
        if item['value_state'] in {'missing','trace','suppressed'} and item['quantity'] is not None:
            raise ValueError('workflow.non_numeric_state_value')
        if item['value_state'] in {'measured','estimated'} and item['quantity'] is None:
            raise ValueError('workflow.numeric_value_missing')
        if item['observed_at'] is None:notes[key].append('observation_time_unknown')
        elif not start<=instant(item['observed_at']).date()<=end:notes[key].append('outside_declared_period_utc')
        if item['event_state']=='observed' and item['observed_at'] is not None and instant(item['recorded_at'])<instant(item['observed_at']):
            notes[key].append('recorded_before_observation')
        if item['event_state']!='observed':notes[key].append('event_not_observed')
        if item['value_state']!='measured':notes[key].append('value_'+item['value_state'])
        if item['kind']=='closing' and item['observed_at'] is not None:
            if Decimal(age_seconds(now,item['observed_at']))>data['max_snapshot_age_seconds']:
                notes[key].append('snapshot_stale_under_supplied_rule')
    result=report('livestock-record-review',data,language);result['method_version']='livestock-0.1.0'
    result['entities']=deepcopy(data['entities'])
    result['max_snapshot_age_seconds']=data['max_snapshot_age_seconds']
    result['records']=[{'original':deepcopy(item),'current_as_of':key in current,
                        'revision_state':'conflicted' if 'correction_fork' in notes[key] else ('current' if key in current else 'retained_not_current'),
                        'superseded_by':sorted(children[key]),'issues':sorted(set(notes[key]))} for key,item in by_id.items()]
    result['current_ids']=sorted(current);result['reviews']=[]
    for request in data['reviews']:
        reasons=[];hard=[];ids=[request['opening_id'],*request['movement_ids'],request['closing_id']]
        entity=entities.get(request['entity_id']);selected=[by_id.get(key) for key in ids]
        if entity is None:hard.append('entity_reference_missing')
        elif entity['identity_state']!='declared':hard.append('entity_identity_unknown')
        if entity and entity['identity_source_ref'] is None:hard.append('identity_source_missing')
        if entity and entity['kind']=='animal':hard.append('individual_balance_unsupported')
        if entity and entity['kind']=='group' and entity['species_as_reported'] is None:hard.append('species_unknown')
        if any(item is None for item in selected):hard.append('record_reference_missing')
        opening,closing=selected[0],selected[-1]
        unit=opening['unit'] if opening else None;basis=opening['basis'] if opening else None
        if unit is None:hard.append('unit_unknown')
        if basis is None:hard.append('basis_unknown')
        if entity and entity['kind']=='feed_lot' and basis not in {'as_fed','dry_matter'}:hard.append('feed_quantity_basis_required')
        for index,item in enumerate(selected):
            if item is None:continue
            expected='opening' if index==0 else ('closing' if index==len(selected)-1 else 'movement')
            if item['kind'] not in ({'receipt','removal'} if expected=='movement' else {expected}):hard.append('record_role_mismatch')
            if item['entity_id']!=request['entity_id']:hard.append('entity_mismatch')
            if item['unit']!=unit:hard.append('unit_mismatch')
            if item['basis']!=basis:hard.append('basis_mismatch')
            if item['id'] not in current:hard.append('record_not_current_as_of')
            hard.extend(x for x in notes[item['id']] if x!='snapshot_stale_under_supplied_rule')
            if item['value_state']!='measured':hard.append('quantity_not_measured')
            if entity and entity['kind']=='group':
                if unit!='head' or basis!='head_count':hard.append('head_count_basis_required')
                if item['quantity'] is not None and Decimal(item['quantity'])!=Decimal(item['quantity']).to_integral_value():hard.append('fractional_head_count')
        if opening and closing and opening['observed_at'] and closing['observed_at']:
            a,b=instant(opening['observed_at']),instant(closing['observed_at'])
            if a>=b:hard.append('snapshot_order_invalid')
            for item in selected[1:-1]:
                if item and item['observed_at'] and not a<instant(item['observed_at'])<=b:hard.append('movement_outside_snapshot_interval')
        reasons.extend(hard)
        if request['coverage']!='complete':reasons.append('movement_coverage_'+request['coverage'])
        if request['coverage_source_ref'] is None:reasons.append('coverage_source_missing')
        if closing:reasons.extend(x for x in notes[closing['id']] if x=='snapshot_stale_under_supplied_rule')
        listed=expected_value=residual=None
        if not hard:
            with localcontext() as ctx:
                ctx.prec=160
                value=Decimal(opening['quantity'])+sum((Decimal(x['quantity'])*(1 if x['kind']=='receipt' else -1) for x in selected[1:-1]),Decimal(0))
                listed=format(value,'f')
                if value<0:reasons.append('negative_listed_balance')
                if not reasons:
                    expected_value=listed;residual=format(Decimal(closing['quantity'])-value,'f')
                    if Decimal(residual)!=0:reasons.append('unresolved_record_count_difference')
        result['reviews'].append({'review_id':request['id'],'entity_id':request['entity_id'],'original_request':deepcopy(request),
             'closing_age_seconds':age_seconds(now,closing['observed_at']) if closing else None,
             'selected_record_ids':ids,'source_refs':list(dict.fromkeys(x['source_ref'] for x in selected if x is not None)),
             'unit':unit,'basis':basis,'listed_balance':listed,'complete_expected_closing':expected_value,
             'observed_minus_expected':residual,'coverage_as_supplied':request['coverage'],
             'status':'arithmetic_only' if not reasons else 'review_with_gaps','issues':sorted(set(reasons)),
             'physical_completeness_verified':False,'nutrition_or_welfare_established':False})
    result['state']='review_draft_with_gaps' if any(notes.values()) or any(x['issues'] for x in result['reviews']) else 'review_draft'
    result['required_reviews']=['confirm_identity_species_and_snapshot_scope','verify_selected_sources_and_movement_coverage',
        'resolve_record_differences_without_inventing_events','refer_clinical_nutrition_or_welfare_questions_to_qualified_reviewer',
        'inspect_notes_and_recipient_scope_before_sharing']
    result['implementation_sha256']=implementation_hash(__file__)
    return result
