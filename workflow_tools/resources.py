"""Faithful supplied routine-record procedure cards and handover, never work approval."""
from copy import deepcopy
from datetime import date
import hashlib,json
from router.core import ROOT
from .common import implementation_hash,instant,report,unique,validate


def run(data,language='en',root=ROOT):
    validate('resource-input',data,root);now=instant(data['as_of']);unique(data['tasks'])
    procedures={}
    for p in data['procedures']:
        key=(p['id'],p['version'])
        if key in procedures:raise ValueError('workflow.duplicate_procedure_version')
        unique(p['steps']);procedures[key]=p
        if p['effective_from'] and p['review_due'] and date.fromisoformat(p['effective_from'])>date.fromisoformat(p['review_due']):
            raise ValueError('workflow.procedure_date_order')
    result=report('resource-team-coordination',data,language);result['method_version']='resources-0.1.0'
    result['procedures']=deepcopy(data['procedures']);result['cards']=[]
    for task in data['tasks']:
        source_gaps=[];gaps=[];p=procedures.get((task['procedure_id'],task['procedure_version']))
        if p is None:source_gaps.append('selected_procedure_version_missing')
        else:
            if p['approval_status']!='declared_approved':source_gaps.append('procedure_not_declared_approved')
            if p['approval_ref'] is None:source_gaps.append('approval_source_missing')
            if p['source_ref'] is None:source_gaps.append('procedure_source_missing')
            if p['approval_recorded_at'] is None:source_gaps.append('approval_time_unknown')
            elif instant(p['approval_recorded_at'])>now:source_gaps.append('approval_recorded_after_cutoff')
            if p['effective_from'] is None or p['review_due'] is None:source_gaps.append('procedure_dates_unknown')
            else:
                if date.fromisoformat(p['effective_from'])>now.date():source_gaps.append('procedure_not_effective_at_cutoff')
                if date.fromisoformat(p['review_due'])<now.date():source_gaps.append('procedure_review_due_before_cutoff')
            for field,expected in [('enterprise_id',data['enterprise_id']),('jurisdiction',data['jurisdiction']),('asset_id',task['asset_id']),('role',task['assigned_role'])]:
                if p[field] is None or expected is None:source_gaps.append('procedure_scope_unknown:'+field)
                elif p[field]!=expected:source_gaps.append('procedure_scope_mismatch:'+field)
            if p['language']!=language:source_gaps.append('procedure_language_mismatch_no_translation')
            if p['translation_of_ref'] is not None and p['fidelity_review_ref'] is None:source_gaps.append('translation_fidelity_reference_missing')
            if p['stop_escalation_ref'] is None:source_gaps.append('stop_escalation_source_missing')
        if instant(task['recorded_at'])>now:source_gaps.append('task_recorded_after_cutoff')
        if task['resource_availability']!='declared_available':gaps.append('resource_'+task['resource_availability'])
        if task['owner_next_role'] is None:gaps.append('next_owner_role_unknown')
        if task['competence_evidence_ref'] is None:gaps.append('competence_evidence_missing')
        if task['completion_state']=='claimed_complete' and task['completion_evidence_ref'] is None:gaps.append('completion_claim_without_evidence')
        if task['acknowledgement_state']=='claimed_received' and task['acknowledgement_ref'] is None:gaps.append('receipt_claim_without_evidence')
        if task['completion_state'] in {'failed','unknown'}:gaps.append('work_state_'+task['completion_state'])
        if task['exception_refs']:gaps.append('supplied_exceptions_need_review')
        if task['due_on'] is not None and date.fromisoformat(task['due_on'])<now.date() and task['completion_state']!='claimed_complete':gaps.append('open_due_date_before_cutoff')
        gaps=sorted(set(source_gaps+gaps))
        result['cards'].append({'task_id':task['id'],'original_task':deepcopy(task),
            'selected_procedure_ref':None if p is None else {key:deepcopy(p[key]) for key in ['id','version','source_ref','language','approval_status','approval_ref','approval_recorded_at','effective_from','review_due','enterprise_id','jurisdiction','asset_id','role','translation_of_ref','fidelity_review_ref']},
            'supplied_procedure_sha256':None if p is None else hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),
            'quoted_steps':deepcopy(p['steps']) if p is not None and not source_gaps else [],
            'stop_escalation_ref':p['stop_escalation_ref'] if p is not None else None,
            'state':'review_draft_with_gaps' if gaps else 'review_draft','issues':gaps,
            'source_approval_verified':False,'translation_fidelity_verified':False,'completion_verified':False,'receipt_verified':False,'competence_established':False})
    result['handover']={'recipient_role':data['handover_recipient_role'],'purpose':data['handover_purpose'],
        'open_or_unknown_task_ids':[t['id'] for t in data['tasks'] if t['completion_state']!='claimed_complete'],
        'claimed_complete_task_ids':[t['id'] for t in data['tasks'] if t['completion_state']=='claimed_complete'],
        'tasks_with_gaps':[c['task_id'] for c in result['cards'] if c['issues']],
        'receipt_verified':False,'competence_established':False,'sent':False}
    if data['handover_recipient_role'] is None:result['issues'].append('handover_recipient_role_unknown')
    result['state']='review_draft_with_gaps' if result['issues'] or any(c['issues'] for c in result['cards']) else 'review_draft'
    result['required_reviews']=['verify_actual_source_approval_scope_version_and_fidelity','review_resources_exceptions_and_next_owner',
        'verify_completion_and_receipt_separately','assess_actual_competence_separately','inspect_local_packet_before_any_sharing']
    result['implementation_sha256']=implementation_hash(__file__)
    return result
