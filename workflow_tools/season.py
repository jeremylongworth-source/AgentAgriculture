"""Calendar options under declared constraints; no agronomic/safety decision."""
from datetime import timedelta
from copy import deepcopy
import importlib.util
from pathlib import Path
from router.core import ROOT
_lab_path = Path(__file__).resolve().parents[1] / 'scripts/weather_evidence_lab.py'
_spec = importlib.util.spec_from_file_location('agentagriculture_synthetic_weather', _lab_path)
_lab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lab)
assess_value = _lab.assess_value  # Fixed project code path, never selected by imported metadata.
from .common import acyclic, implementation_hash, instant, report, stamp, unique, validate

MAX_CANDIDATES = 256


def merged(intervals):
    result = []
    for start, end in sorted(intervals):
        if start >= end:
            raise ValueError('season.interval_invalid')
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def intersection(a, b):
    values = [(max(x,y), min(z,w)) for x,z in a for y,w in b if max(x,y) < min(z,w)]
    return merged(values)


def run(data, language='en', root=ROOT):
    validate('season-input', data, root)
    now = instant(data['as_of'])
    tasks = unique(data['tasks']); resources = unique(data['resources']); unique(data['windows'])
    acyclic(tasks, lambda item: item['depends_on'])
    calendars = {key: merged([(instant(x['start']), instant(x['end'])) for x in item['availability']]) for key,item in resources.items()}
    windows, weather = {}, []
    for window in data['windows']:
        start,end = instant(window['start']),instant(window['end'])
        if start >= end:
            raise ValueError('season.interval_invalid')
        item = window['weather']
        assessment = assess_value(item, now=data['as_of'], location_id=data['location_id'], unit=data['weather_unit'],
                                  max_age_seconds=data['max_weather_age_seconds'], window=(window['start'],window['end']))
        reasons = list(assessment['issues'])
        evidence_time = instant(item['observed_at'] if item['kind']=='observation' else item['issued_at'])
        if (now-evidence_time).total_seconds() > data['max_weather_age_seconds']:
            reasons.append('evidence_stale')  # Preserve exact fractional-second boundary, not age floor.
        if item['kind']=='observation' and end > now:
            reasons.append('observation_is_not_future_forecast')
        if end <= now:
            reasons.append('window_elapsed')
        if window['condition_status']!='operator_candidate':
            reasons.append('condition_'+window['condition_status'])
        if window['condition_status']=='operator_candidate' and window['criterion_ref'] is None:
            reasons.append('criterion_reference_missing')
        reasons = sorted(set(reasons))
        weather.append({'window_id':window['id'],'source_id':item['source_id'],'assessment':assessment,
                        'declared_window':{'start':window['start'],'end':window['end']},
                        'original_evidence':item,'declared_condition':window['condition_status'],
                        'criterion_ref':window['criterion_ref'],'issues':reasons})
        if not reasons:
            windows[window['id']] = (max(start,now),end)
    result = report('season-work-planning',data,language)
    result['resources']=deepcopy(data['resources'])
    result['weather_policy']={key:deepcopy(data[key]) for key in ['location_id','weather_unit','max_weather_age_seconds']}
    result['weather_review']=weather; result['tasks']=[]; all_candidates=[]
    for key,task in tasks.items():
        earliest,latest = instant(task['earliest']),instant(task['latest'])
        if earliest >= latest:
            raise ValueError('season.task_interval_invalid')
        reasons=[]; candidates=[]
        if task['resource_requirement_state']=='unknown':
            reasons.append('resource_requirements_unknown')
        missing=[key for key in task['resource_ids'] if key not in calendars]
        if missing:
            reasons.append('resource_calendar_missing')
        if not reasons:
            for window_id,(start,end) in windows.items():
                start,end=max(start,earliest),min(end,latest)
                if start>=end:
                    continue
                segments=[(start,end)]
                for resource_id in task['resource_ids']:
                    segments=intersection(segments,calendars[resource_id])
                for start,end in segments:
                    if (end-start).total_seconds() < task['duration_minutes']*60:
                        continue
                    candidate={'task_id':key,'window_id':window_id,'start':stamp(start),'end':stamp(end),
                               'earliest_start':stamp(start),'latest_start':stamp(end-timedelta(minutes=task['duration_minutes'])),
                               'duration_minutes':task['duration_minutes'],'resource_ids':task['resource_ids'],
                               'depends_on':task['depends_on'],'condition':'declared_constraints_only'}
                    candidates.append(candidate);all_candidates.append(candidate)
                    if len(all_candidates)>MAX_CANDIDATES:
                        raise ValueError('season.too_many_candidates')
        if task['depends_on']:
            reasons.append('dependencies_not_jointly_scheduled')
        if not candidates:
            reasons.append('no_calendar_candidate')
        result['tasks'].append({'task_id':key,'label_as_supplied':task['label'],'original':deepcopy(task),'candidates':candidates,
                                'missing_resource_ids':missing,'issues':sorted(set(reasons))})
    conflicts=[]
    for number,a in enumerate(all_candidates):
        for b in all_candidates[number+1:]:
            shared=sorted(set(a['resource_ids'])&set(b['resource_ids']))
            if a['task_id']!=b['task_id'] and shared and max(instant(a['start']),instant(b['start']))<min(instant(a['end']),instant(b['end'])):
                conflict={'tasks':sorted([a['task_id'],b['task_id']]),'resources':shared}
                if conflict not in conflicts:
                    conflicts.append(conflict)
    result['shared_resource_conflicts']=conflicts
    result['candidate_count']=len(all_candidates)
    result['state']='conditional_options' if all_candidates else 'no_supported_option'
    result['alerts_checked']=False
    result['required_reviews']=['confirm_actual_weather_alerts_and_field_conditions','review_declared_criteria_and_procedure',
                                'choose_options_and_resolve_dependencies_resources','no_operational_permission_from_calendar_fit']
    result['implementation_sha256']=implementation_hash(__file__)
    result['weather_lab_sha256']=implementation_hash(Path(root)/'scripts/weather_evidence_lab.py')
    return result
