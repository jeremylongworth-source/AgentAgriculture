"""Synthetic same-unit mass/lot/dispatch arithmetic, never physical or legal proof."""
from collections import Counter
from copy import deepcopy
from datetime import date
from decimal import Decimal,localcontext
from router.core import ROOT
from .common import implementation_hash,instant,report,unique,validate
from .record_versions import select

MASS_UNITS={'kg','g','lb'}

def age(now,observed):
    if observed is None:return None
    delta=now-instant(observed)
    return format(Decimal(delta.days*86400+delta.seconds)+Decimal(delta.microseconds)/Decimal(1000000),'f')

def run(data,language='en',root=ROOT):
    validate('harvest-input',data,root)
    lots=unique(data['lots']);unique(data['lot_reviews']);unique(data['commitments'])
    by_id,current,children,notes=select(data['records'],data['as_of'],['lot_id','kind'])
    start,end=map(date.fromisoformat,[data['period']['start'],data['period']['end']]);now=instant(data['as_of']);derived={}
    for key,item in by_id.items():
        if item['lot_id'] not in lots:raise ValueError('workflow.unknown_lot')
        if item['source_ref'] is None:notes[key].append('source_missing')
        if item['observed_at'] is None:notes[key].append('observation_time_unknown')
        else:
            if not start<=instant(item['observed_at']).date()<=end:notes[key].append('outside_declared_period_utc')
            if item['event_state']=='observed' and instant(item['recorded_at'])<instant(item['observed_at']):notes[key].append('recorded_before_observation')
        if item['event_state']!='observed':notes[key].append('event_not_observed')
        mass_issues=[]
        for field in ['gross','tare']:
            value=item[field]
            if (value['state'] in {'measured','estimated'})!=(value['value'] is not None):raise ValueError('workflow.quantity_state_value_mismatch')
            if value['state']!='measured':mass_issues.append(field+'_'+value['state'])
            if value['unit'] not in MASS_UNITS:mass_issues.append(field+'_mass_unit_unsupported')
        if item['gross']['unit']!=item['tare']['unit']:mass_issues.append('gross_tare_unit_mismatch')
        net=None
        if not mass_issues:
            with localcontext() as ctx:
                ctx.prec=160
                quantity=Decimal(item['gross']['value'])-Decimal(item['tare']['value'])
                if quantity<0:mass_issues.append('gross_below_tare')
                else:net=format(quantity,'f')
        derived[key]={'quantity':net,'unit':item['gross']['unit'],'basis':'net_mass','issues':mass_issues}
        notes[key].extend(mass_issues)
        expected_scope='within_enterprise' if item['kind']=='internal_move' else ('snapshot' if item['kind'] in {'opening','closing'} else 'boundary')
        if item['movement_scope']!=expected_scope:notes[key].append('movement_scope_mismatch')
        if item['kind']=='internal_move' and (None in [item['from_location_id'],item['to_location_id']] or item['from_location_id']==item['to_location_id']):notes[key].append('internal_locations_missing_or_same')
    result=report('harvest-storage-delivery',data,language);result['method_version']='harvest-0.1.0'
    result['lots']=deepcopy(data['lots']);result['max_closing_age_seconds']=data['max_closing_age_seconds']
    result['notes']=deepcopy(data['notes']);result['handover']={'recipient_role':data['recipient_role'],'purpose':data['handover_purpose'],'sent':False}
    result['records']=[{'original':deepcopy(item),'current_as_of':key in current,
        'revision_state':'conflicted' if 'correction_fork' in notes[key] else ('current' if key in current else 'retained_not_current'),
        'superseded_by':sorted(children[key]),'net_mass':derived[key],'issues':sorted(set(notes[key]))} for key,item in by_id.items()]
    result['current_ids']=sorted(current);result['lot_reviews']=[]
    def identity(lot_id):
        lot=lots.get(lot_id)
        return ['lot_identity_unresolved'] if lot is None or lot['identity_state']!='declared' or lot['identity_source_ref'] is None or lot['commodity_as_reported'] is None else []
    def selected_issues(item,lot_id,unit):
        if item is None:return ['record_reference_missing']
        problems=list(notes[item['id']])
        if item['lot_id']!=lot_id:problems.append('lot_mismatch')
        if item['id'] not in current:problems.append('record_not_current_as_of')
        if derived[item['id']]['unit']!=unit:problems.append('net_unit_mismatch')
        if derived[item['id']]['quantity'] is None:problems.append('net_mass_unresolved')
        return problems
    for request in data['lot_reviews']:
        ids=[request['opening_id'],*request['movement_ids'],request['closing_id']]
        if len(set(ids))!=len(ids):raise ValueError('workflow.duplicate_selected_record')
        selected=[by_id.get(x) for x in ids];opening,closing=selected[0],selected[-1]
        unit=derived[opening['id']]['unit'] if opening else None;hard=identity(request['lot_id']);issues=[]
        if request['snapshot_scope']!='enterprise_lot':hard.append('enterprise_snapshot_scope_unresolved')
        if request['snapshot_scope_source_ref'] is None:hard.append('snapshot_scope_source_missing')
        if any(item and (item['from_location_id'] is not None or item['to_location_id'] is not None) for item in [opening,closing]):hard.append('snapshot_location_conflicts_with_enterprise_scope')
        for index,item in enumerate(selected):
            hard.extend(selected_issues(item,request['lot_id'],unit))
            if item and item['kind'] not in ({'opening'} if index==0 else ({'closing'} if index==len(selected)-1 else {'receipt','dispatch','internal_move'})):hard.append('record_role_mismatch')
        if opening and closing and opening['observed_at'] and closing['observed_at']:
            a,b=instant(opening['observed_at']),instant(closing['observed_at'])
            if a>=b:hard.append('snapshot_order_invalid')
            for item in selected[1:-1]:
                if item and item['observed_at'] and not a<instant(item['observed_at'])<=b:hard.append('movement_outside_snapshot_interval')
        def relevant(item):
            if not opening or not closing or not opening['observed_at'] or not closing['observed_at'] or not item['observed_at']:return True
            return instant(opening['observed_at'])<instant(item['observed_at'])<=instant(closing['observed_at'])
        unselected=[key for key in sorted(current) if by_id[key]['lot_id']==request['lot_id'] and by_id[key]['kind'] in {'receipt','dispatch','internal_move'} and key not in request['movement_ids'] and relevant(by_id[key])]
        if unselected:issues.append('unselected_current_lot_movement')
        if any(item['lot_id']==request['lot_id'] and item['kind'] in {'receipt','dispatch','internal_move'} and 'correction_fork' in notes[key] and relevant(item) for key,item in by_id.items()):issues.append('unresolved_lot_correction_fork')
        if request['coverage']!='complete':issues.append('movement_coverage_'+request['coverage'])
        if request['coverage_source_ref'] is None:issues.append('coverage_source_missing')
        closing_age=age(now,closing['observed_at']) if closing else None
        if closing_age is not None and Decimal(closing_age)>data['max_closing_age_seconds']:issues.append('closing_stale_under_supplied_rule')
        listed=expected=residual=None
        if not hard:
            with localcontext() as ctx:
                ctx.prec=160
                value=Decimal(derived[opening['id']]['quantity'])+sum((Decimal(derived[x['id']]['quantity'])*(1 if x['kind']=='receipt' else -1) for x in selected[1:-1] if x['kind']!='internal_move'),Decimal(0))
                listed=format(value,'f')
                if value<0:issues.append('negative_listed_balance')
                if not issues:
                    expected=listed;residual=format(Decimal(derived[closing['id']]['quantity'])-value,'f')
                    if Decimal(residual)!=0:issues.append('unresolved_lot_record_difference')
        result['lot_reviews'].append({'original_request':deepcopy(request),'selected_record_ids':ids,'unit':unit,'basis':'net_mass',
            'excluded_internal_move_ids':[x['id'] for x in selected if x and x['kind']=='internal_move'],'unselected_current_movement_ids':unselected,
            'closing_age_seconds':closing_age,'listed_balance':listed,'complete_expected_closing':expected,'observed_minus_expected':residual,
            'issues':sorted(set(hard+issues)),'physical_completeness_verified':False})
    allocations=Counter(key for c in data['commitments'] for key in c['dispatch_ids']);result['delivery_reviews']=[]
    for request in data['commitments']:
        hard=identity(request['lot_id']);issues=[];selected=[by_id.get(x) for x in request['dispatch_ids']]
        if len(set(request['dispatch_ids']))!=len(request['dispatch_ids']):raise ValueError('workflow.duplicate_selected_dispatch')
        if request['quantity_state']=='declared' and request['quantity'] is None:raise ValueError('workflow.declared_quantity_missing')
        if request['quantity_state']=='missing' and request['quantity'] is not None:raise ValueError('workflow.missing_quantity_has_value')
        if request['quantity_state']!='declared':hard.append('commitment_quantity_not_declared')
        if request['basis']!='net_mass' or request['unit'] not in MASS_UNITS:hard.append('commitment_mass_basis_unsupported')
        if request['source_ref'] is None:hard.append('commitment_source_missing')
        if request['destination_id'] is None:hard.append('commitment_destination_unknown')
        if instant(request['issued_at'])>now:hard.append('commitment_issued_after_as_of')
        for item in selected:
            hard.extend(selected_issues(item,request['lot_id'],request['unit']))
            if item:
                if item['kind']!='dispatch':hard.append('selected_record_not_dispatch')
                if item['to_location_id']!=request['destination_id']:hard.append('dispatch_destination_mismatch')
                if item['observed_at'] and instant(item['observed_at']).date()>date.fromisoformat(request['due_on']):hard.append('dispatch_after_declared_due_date')
                if allocations[item['id']]>1:issues.append('dispatch_allocation_ambiguous')
        if request['coverage']!='complete':issues.append('dispatch_coverage_'+request['coverage'])
        if request['coverage_source_ref'] is None:issues.append('coverage_source_missing')
        listed=difference=None
        if not hard:
            with localcontext() as ctx:
                ctx.prec=160;listed=format(sum((Decimal(derived[x['id']]['quantity']) for x in selected),Decimal(0)),'f')
                if not issues:difference=format(Decimal(listed)-Decimal(request['quantity']),'f')
        result['delivery_reviews'].append({'original_commitment':deepcopy(request),'listed_dispatch_quantity':listed,
            'dispatch_minus_declared':difference,'issues':sorted(set(hard+issues)),
            'delivery_or_acceptance_verified':False,'legal_fulfilment_established':False})
    result['issues']=[]
    result['state']='review_draft_with_gaps' if any(notes.values()) or any(x['issues'] for x in result['lot_reviews']+result['delivery_reviews']) else 'review_draft'
    result['physical_measurement_accuracy_verified']=False;result['food_grade_shelf_life_established']=False
    result['required_reviews']=['verify_lot_identity_sources_and_measurements','resolve_units_tare_coverage_and_corrections',
        'review_internal_movement_scope_without_double_counting','verify_dispatch_allocation_and_declared_commitment_version',
        'verify_actual_delivery_and_acceptance_separately','obtain_qualified_food_or_contract_interpretation_if_needed']
    result['implementation_sha256']=implementation_hash(__file__)
    return result
