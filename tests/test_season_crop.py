"""Known answers and false-clear boundaries for the two real E02 helper slices."""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from router.core import Catalog, read_document
from workflow_tools import crop,season
from workflow_tools.execute import build
from workflow_tools.render import markdown
from workflow_tools.common import safe_markdown as esc


class SeasonCropTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog()
        cls.season=read_document(ROOT/'examples/ecosystem/season-en.json')
        cls.crop=read_document(ROOT/'examples/ecosystem/crop-en.json')

    def context(self,kind='season',lang='en'):
        return read_document(ROOT/f'tests/fixtures/ecosystem/context/{kind}-{lang}.json')

    def seasonal(self,change=None):
        data=deepcopy(self.season)
        if change:change(data)
        return season.run(data)

    def cropping(self,change=None):
        data=deepcopy(self.crop)
        if change:change(data)
        return crop.run(data)

    def test_real_calendar_intersection_duration_and_joint_conflicts(self):
        r=self.seasonal();a,b,c=r['tasks']
        self.assertEqual(r['candidate_count'],2)
        self.assertEqual(a['candidates'][0]['start'],'2026-10-20T09:30:00Z')
        self.assertEqual(a['candidates'][0]['latest_start'],'2026-10-20T10:30:00Z')
        self.assertEqual(b['candidates'][0]['latest_start'],'2026-10-20T10:00:00Z')
        self.assertIn('dependencies_not_jointly_scheduled',b['issues'])
        self.assertIn('resource_requirements_unknown',c['issues'])
        self.assertEqual(r['shared_resource_conflicts'],[{'tasks':['SYN-WORK-A','SYN-WORK-B'],'resources':['SYN-CREW-A']}])
        self.assertFalse(r['alerts_checked']);self.assertFalse(r['execution_allowed'])

    def test_stale_weather_does_not_clear_work_options(self):
        r=season.run(read_document(ROOT/'tests/fixtures/ecosystem/workflows/season-stale.json'))
        self.assertEqual(r['candidate_count'],0)
        self.assertTrue(all('evidence_stale' in w['issues'] for w in r['weather_review']))

    def test_exact_fractional_age_boundary_is_not_rounded_fresh(self):
        def change(d):d.update(as_of='2026-10-20T08:00:00.000001Z',max_weather_age_seconds=3600)
        r=self.seasonal(change)
        self.assertEqual(r['candidate_count'],0)
        self.assertIn('evidence_stale',r['weather_review'][0]['issues'])

    def test_observation_cannot_substitute_for_future_forecast(self):
        def change(d):
            for w in d['windows']:
                w['weather'].update(kind='observation',observed_at='2026-10-20T07:00:00Z',value_state='measured')
        r=self.seasonal(change)
        self.assertEqual(r['candidate_count'],0)
        self.assertIn('observation_is_not_future_forecast',r['weather_review'][0]['issues'])

    def test_location_unit_missing_and_unreviewed_values_remain_unavailable(self):
        for key,value,issue in [('location_id','ANOTHER-SITE','location_mismatch'),('unit','mm','unit_mismatch'),('quality','unreviewed','quality_unreviewed')]:
            def change(d):
                for w in d['windows']:w['weather'][key]=value
            r=self.seasonal(change)
            self.assertEqual(r['candidate_count'],0);self.assertIn(issue,r['weather_review'][0]['issues'])
        def missing(d):
            for w in d['windows']:w['weather'].update(value_state='missing',value=None)
        self.assertEqual(self.seasonal(missing)['candidate_count'],0)

    def test_unknown_condition_or_missing_criterion_is_not_assumed_approval(self):
        for key,value in [('condition_status','unknown'),('criterion_ref',None)]:
            def change(d):
                for w in d['windows']:w[key]=value
            self.assertEqual(self.seasonal(change)['candidate_count'],0)

    def test_forecast_expiry_future_issue_and_uncovered_interval_block_candidates(self):
        for change in [lambda w:w.update(valid_end='2026-10-20T08:00:00Z'),
                       lambda w:w.update(issued_at='2026-10-20T09:00:00Z'),
                       lambda w:w.update(valid_start='2026-10-20T10:00:00Z')]:
            def mutate(d):
                for w in d['windows']:change(w['weather'])
            self.assertEqual(self.seasonal(mutate)['candidate_count'],0)

    def test_missing_resource_or_insufficient_duration_preserves_task_gaps(self):
        def missing(d):d['resources']=[]
        r=self.seasonal(missing)
        self.assertIn('resource_calendar_missing',r['tasks'][0]['issues'])
        def too_long(d):d['tasks'][0]['duration_minutes']=121
        self.assertEqual(self.seasonal(too_long)['tasks'][0]['candidates'],[])

    def test_calendar_overlap_is_merged_without_duplicate_availability(self):
        def change(d):d['resources'][0]['availability'].append({'start':'2026-10-20T10:00:00Z','end':'2026-10-20T11:00:00Z'})
        self.assertEqual(self.seasonal(change)['tasks'][0]['candidates'],self.seasonal()['tasks'][0]['candidates'])

    def test_task_cycle_unknown_dependency_duplicate_id_and_bad_interval_refused(self):
        edits=[lambda d:d['tasks'][0].update(depends_on=['SYN-WORK-B']),
               lambda d:d['tasks'][0].update(depends_on=['absent']),
               lambda d:d['tasks'][1].update(id='SYN-WORK-A'),
               lambda d:d['windows'][0].update(end='2026-10-20T09:00:00Z')]
        for edit in edits:
            with self.assertRaises(ValueError):self.seasonal(edit)

    def test_calendar_candidate_budget_refuses_instead_of_truncating(self):
        d=deepcopy(self.season)
        # A few KiB of invented intervals are enough to exercise the finite budget.
        d['windows']=[deepcopy(d['windows'][0]) for _ in range(8)]
        for i,w in enumerate(d['windows']):w['id']='W'+str(i)
        d['resources'][0]['availability']=[{'start':f'2026-10-20T{9+i//4:02d}:{(i%4)*15:02d}:00Z','end':f'2026-10-20T{9+i//4:02d}:{(i%4)*15+5:02d}:00Z'} for i in range(8)]
        d['tasks']=[deepcopy(d['tasks'][0]) for _ in range(12)]
        for i,t in enumerate(d['tasks']):t.update(id='T'+str(i),duration_minutes=1)
        with self.assertRaisesRegex(ValueError,'too_many_candidates'):season.run(d)

    def test_crop_corrected_arithmetic_and_complete_original_history(self):
        r=self.cropping()
        self.assertEqual(r['comparisons'][0]['difference_right_minus_left'],'0.7')
        self.assertIn('SYN-O2-REV',r['current_ids']);self.assertNotIn('SYN-O2',r['current_ids'])
        self.assertNotIn('SYN-O2-FUTURE',r['current_ids'])
        originals={x['original']['id']:x['original'] for x in r['observations']}
        self.assertEqual(originals['SYN-O2']['value'],'13.0')
        self.assertEqual(originals['SYN-O2-REV']['value'],'13.1')
        self.assertEqual(originals['SYN-O2-FUTURE']['value'],'99')
        self.assertEqual(r['comparisons'][0]['interpretation'],'not_established')

    def test_missing_is_not_zero_and_method_mismatch_yields_no_numeric_result(self):
        r=self.cropping();items={x['original']['id']:x['original'] for x in r['observations']}
        self.assertEqual(items['SYN-O3']['value'],'0');self.assertIsNone(items['SYN-O4']['value'])
        self.assertIsNone(r['comparisons'][1]['difference_right_minus_left'])
        self.assertIn('metadata_mismatch:method',r['comparisons'][2]['issues'])
        self.assertIsNone(r['comparisons'][2]['difference_right_minus_left'])

    def test_two_unknown_methods_do_not_establish_comparability(self):
        r=crop.run(read_document(ROOT/'tests/fixtures/ecosystem/workflows/crop-missing-method.json'))
        self.assertIsNone(r['comparisons'][0]['difference_right_minus_left'])
        self.assertIn('metadata_missing:method',r['comparisons'][0]['issues'])

    def test_estimated_trace_and_suppressed_values_not_treated_as_measurements(self):
        for state in ['estimated','trace','suppressed']:
            def change(d):d['observations'][0].update(value_state=state,value='12.4' if state=='estimated' else None)
            r=self.cropping(change)
            self.assertIsNone(r['comparisons'][0]['difference_right_minus_left'])
            self.assertIn('value_not_measured',r['comparisons'][0]['issues'])

    def test_explicit_measured_zero_and_high_precision_difference_are_retained(self):
        def zero(d):d['observations'][0]['value']='0';d['observations'][2]['value']='0.2'
        self.assertEqual(self.cropping(zero)['comparisons'][0]['difference_right_minus_left'],'0.2')
        def precise(d):d['observations'][0]['value']='1'*50+'.12345678';d['observations'][2]['value']='1'*50+'.12345679'
        self.assertEqual(self.cropping(precise)['comparisons'][0]['difference_right_minus_left'],'0.00000001')

    def test_undated_observation_not_dated_by_recording_time(self):
        r=self.cropping(lambda d:d['observations'][0].update(observed_at=None))
        item=next(x for x in r['observations'] if x['original']['id']=='SYN-O1')
        self.assertIsNone(item['original']['observed_at'])
        self.assertIn('observation_time_unknown',r['comparisons'][0]['issues'])

    def test_forked_corrections_preserve_conflict_without_choosing_latest(self):
        def change(d):
            item=deepcopy(d['observations'][2]);item.update(id='SYN-FORK',value='13.2',recorded_at='2026-10-12T13:00:00Z')
            d['observations'].append(item)
        r=self.cropping(change)
        self.assertIsNone(r['comparisons'][0]['difference_right_minus_left'])
        self.assertIn('correction_fork',r['comparisons'][0]['issues'])
        self.assertTrue({'SYN-O2','SYN-O2-REV','SYN-FORK'}<=set(r['current_ids']))

    def test_future_original_and_planned_event_cannot_be_measured_evidence(self):
        def change(d):d['comparisons'].append({'id':'FUTURE','left':'SYN-O1','right':'SYN-O7'})
        r=self.cropping(change)
        self.assertIsNone(r['comparisons'][-1]['difference_right_minus_left'])
        self.assertIn('event_not_observed',r['comparisons'][-1]['issues'])

    def test_outside_declared_utc_period_is_retained_but_not_compared(self):
        r=self.cropping(lambda d:d['observations'][0].update(observed_at='2026-09-30T23:00:00Z'))
        self.assertIn('observation_outside_declared_period_utc',r['comparisons'][0]['issues'])
        self.assertIsNone(r['comparisons'][0]['difference_right_minus_left'])

    def test_crop_cycle_unknown_entity_and_incompatible_lineage_refused(self):
        edits=[lambda d:d['observations'][1].update(supersedes='SYN-O2-REV',correction_reason='cycle'),
               lambda d:d['observations'][0].update(entity_id='absent'),
               lambda d:d['observations'][2].update(entity_id='SYN-BLOCK-B'),
               lambda d:d['observations'][2].update(correction_reason=None)]
        for edit in edits:
            with self.assertRaises(ValueError):self.cropping(edit)

    def test_helper_does_not_modify_selected_records(self):
        for d,runner in [(deepcopy(self.season),season.run),(deepcopy(self.crop),crop.run)]:
            before=deepcopy(d);runner(d);self.assertEqual(d,before)

    def test_context_identity_and_real_data_flags_refused(self):
        context=self.context();d=deepcopy(self.season);d['enterprise_id']='ANOTHER'
        with self.assertRaisesRegex(ValueError,'context_mismatch'):build(context,d,self.catalog)
        d=deepcopy(self.season);d['synthetic_only']=False
        with self.assertRaisesRegex(ValueError,'synthetic_helper_only'):build(context,d,self.catalog)

    def test_en_fr_canonical_results_and_escaped_views(self):
        for kind in ['season','crop']:
            a=build(self.context(kind),read_document(ROOT/f'examples/ecosystem/{kind}-en.json'),self.catalog)
            b=build(self.context(kind,'fr'),read_document(ROOT/f'examples/ecosystem/{kind}-fr.json'),self.catalog)
            self.assertEqual(a['state'],b['state'])
            if kind=='season':
                self.assertEqual(a['candidate_count'],b['candidate_count'])
                self.assertEqual([t['candidates'] for t in a['tasks']],[t['candidates'] for t in b['tasks']])
            else:self.assertEqual(a['comparisons'],b['comparisons'])
            self.assertNotEqual(markdown(a).splitlines()[0],markdown(b).splitlines()[0])
            self.assertFalse(a['execution_allowed']);self.assertFalse(b['operational_advice_allowed'])
        d=deepcopy(self.crop);d['observations'][0]['unit']='[unsafe](https://example.invalid)'
        rendered=markdown(crop.run(d));self.assertNotIn('[unsafe](',rendered)
        self.assertNotIn('https://example.invalid/',rendered) # Notes are omitted from readable packet.

    def test_cli_checks_intent_before_reading_domain_file(self):
        (ROOT/'outputs').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='ag-domain-cli-',dir=ROOT/'outputs') as temp:
            folder=Path(temp);context=self.context();context['requested_actions']=['control_equipment']
            p=folder/'context.json';p.write_text(json.dumps(context),encoding='utf-8')
            r=subprocess.run([sys.executable,str(ROOT/'scripts/run_farm_workflow.py'),'--context',str(p),'--input',str(folder/'not-there.json')],capture_output=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'))
            self.assertEqual(r.returncode,0);answer=json.loads(r.stdout)
            self.assertEqual(answer['route']['state'],'blocked_scope');self.assertFalse(answer['data_read'])
            context.update(requested_actions=['read_selected'],intent='explain',enterprise_id=None,jurisdiction='unknown',period=None)
            p.write_text(json.dumps(context),encoding='utf-8')
            r=subprocess.run([sys.executable,str(ROOT/'scripts/run_farm_workflow.py'),'--context',str(p),'--input',str(folder/'not-there.json')],capture_output=True,encoding='utf-8')
            self.assertEqual(r.returncode,0);self.assertFalse(json.loads(r.stdout)['data_read'])

    def test_entity_types_are_preserved_and_cross_entity_values_not_compared(self):
        for kind in ['field','bed','block','house']:
            d=deepcopy(self.crop);d['entities'][0]['type']=kind
            self.assertEqual(crop.run(d)['entities'][0]['type'],kind)
        d=deepcopy(self.crop);right=d['observations'][3]
        for key in ['metric','unit','method','basis','sampling_scope']:right[key]=d['observations'][0][key]
        d['comparisons']=[{'id':'CROSS-ENTITY','left':'SYN-O1','right':'SYN-O3'}]
        result=crop.run(d)['comparisons'][0]
        self.assertIsNone(result['difference_right_minus_left'])
        self.assertEqual(result['issues'],['metadata_mismatch:entity_id'])

    def test_uncertainty_states_survive_summary_and_readable_view(self):
        for state,value,en,fr in [('estimated','12.4','estimated','estimée'),('missing',None,'missing','manquante'),
                                  ('trace',None,'trace','trace'),('suppressed',None,'withheld','non divulguée')]:
            d=deepcopy(self.crop);d['observations']=d['observations'][:1];d['comparisons']=[]
            d['observations'][0].update(value_state=state,value=value)
            report=crop.run(d)
            self.assertEqual(report['state'],'review_draft_with_gaps')
            self.assertIn('value_'+state,report['observations'][0]['issues'])
            self.assertIn(en,markdown(report))
            report['language']='fr';self.assertIn(fr,markdown(report))

    def test_saved_results_identify_review_context_without_input_file(self):
        for kind,data in [('season',self.season),('crop',self.crop)]:
            result=build(self.context(kind),deepcopy(data),self.catalog)
            expected={key:deepcopy(data[key]) for key in ['enterprise_id','jurisdiction','period','as_of']}
            expected['period_date_basis']='UTC'
            self.assertEqual(result['context'],expected)
            for language in ['en','fr']:
                result['language']=language
                view=markdown(result)
                for value in [data['task_id'],data['enterprise_id'],data['jurisdiction'],data['period']['start'],data['period']['end'],data['as_of']]:
                    self.assertIn(esc(value),view)
                self.assertIn('UTC',view)
            result['context']['period']['start']='2000-01-01'
            self.assertNotEqual(result['context']['period'],data['period'])

    def test_crop_readable_packet_contains_sources_methods_and_correction_lineage(self):
        result=self.cropping()
        for language in ['en','fr']:
            result['language']=language;view=markdown(result)
            for value in ['SYN-REPORT-TWO-REV','SYN-METHOD-A-v1','SYN-depth-and-composite-A','SYN-O2','dry','SYN annual crop','2026-10-12T12:00:00Z']:
                self.assertIn(esc(value),view)
            self.assertIn(esc('SYN-O1'),view);self.assertIn(esc('SYN-O2-REV'),view)
            self.assertIn('Corrected invented transcription',view)
        result['observations'][0]['original']['source_ref']='[untrusted](https://example.invalid/action)'
        self.assertNotIn('[untrusted](',markdown(result))
        self.assertNotIn('Invented laboratory number',markdown(result)) # Free notes remain in JSON only.

    def test_season_readable_packet_contains_criteria_weather_and_resource_context(self):
        result=self.seasonal()
        self.assertEqual(result['resources'],self.season['resources'])
        self.assertEqual(result['tasks'][0]['original'],self.season['tasks'][0])
        self.assertEqual(result['weather_policy']['max_weather_age_seconds'],7200)
        self.assertEqual(result['weather_review'][1]['declared_window'],{'start':'2026-10-20T13:00:00Z','end':'2026-10-20T16:00:00Z'})
        for language in ['en','fr']:
            result['language']=language;view=markdown(result)
            for value in ['SYN-SITE-A','SYN-WX-A','SYN-PROCEDURE-AVAILABLE-WINDOW','SYN-CREW-A','SYN-WORK-A','7200','2026-10-20T07:00:00Z','2026-10-20T07:05:00Z','2026-10-20T13:00:00Z','2026-10-20T16:00:00Z','degC','forecast']:
                self.assertIn(esc(value),view)

if __name__=='__main__':unittest.main()
