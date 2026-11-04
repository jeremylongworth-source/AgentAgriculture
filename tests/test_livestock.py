from copy import deepcopy
from decimal import Decimal
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from router.core import Catalog,read_document
from workflow_tools import livestock
from workflow_tools.execute import build
from workflow_tools.render import markdown
from workflow_tools.common import safe_markdown as esc

class LivestockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read_document(ROOT/'examples/ecosystem/livestock-en.json');cls.catalog=Catalog()
    def run_case(self,change=None):
        data=deepcopy(self.data)
        if change:change(data)
        return livestock.run(data)
    def context(self,lang='en'):return read_document(ROOT/f'tests/fixtures/ecosystem/context/livestock-{lang}.json')
    def test_group_and_corrected_feed_exact_balances(self):
        r=self.run_case();group,feed,unknown=r['reviews']
        self.assertEqual((group['listed_balance'],group['complete_expected_closing'],group['observed_minus_expected']),('42','42','-1'))
        self.assertEqual((feed['listed_balance'],feed['complete_expected_closing'],feed['observed_minus_expected']),('1050','1050','-5'))
        self.assertIn('unresolved_record_count_difference',feed['issues'])
        self.assertFalse(feed['physical_completeness_verified']);self.assertFalse(feed['nutrition_or_welfare_established'])
    def test_unknown_or_partial_coverage_is_not_complete(self):
        for coverage in ['unknown','partial']:
            r=self.run_case(lambda d:d['reviews'][1].update(coverage=coverage))['reviews'][1]
            self.assertEqual(r['listed_balance'],'1050');self.assertIsNone(r['complete_expected_closing']);self.assertIsNone(r['observed_minus_expected'])
    def test_missing_coverage_source_prevents_complete_claim(self):
        r=self.run_case(lambda d:d['reviews'][1].update(coverage_source_ref=None))['reviews'][1]
        self.assertIn('coverage_source_missing',r['issues']);self.assertIsNone(r['complete_expected_closing'])
    def test_missing_quantity_is_not_zero(self):
        r=self.run_case(lambda d:d['records'][7].update(quantity=None,value_state='missing'))['reviews'][1]
        self.assertIsNone(r['listed_balance']);self.assertIsNone(r['observed_minus_expected'])
        zero=self.run_case(lambda d:d['records'][7].update(quantity='0'))['reviews'][1]
        self.assertEqual(zero['observed_minus_expected'],'-1050')
    def test_estimated_trace_suppressed_are_distinct(self):
        for state,value in [('estimated','1045'),('trace',None),('suppressed',None)]:
            r=self.run_case(lambda d:d['records'][7].update(value_state=state,quantity=value))
            self.assertIn('value_'+state,r['records'][7]['issues']);self.assertIsNone(r['reviews'][1]['listed_balance'])
            self.assertIn({'estimated':'estimated','trace':'trace','suppressed':'withheld'}[state],markdown(r))
    def test_unit_mismatch_blocks_instead_of_converting(self):
        r=self.run_case(lambda d:d['records'][7].update(unit='lb'))['reviews'][1]
        self.assertIn('unit_mismatch',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_as_fed_and_dry_matter_are_not_added(self):
        r=self.run_case(lambda d:d['records'][8].update(basis='dry_matter'))['reviews'][1]
        self.assertIn('basis_mismatch',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_unknown_unit_and_basis_do_not_become_defaults(self):
        for key in ['unit','basis']:
            r=self.run_case(lambda d:d['records'][4].update(**{key:None}))['reviews'][1]
            self.assertIn(key+'_unknown',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_feed_lot_cannot_use_animal_head_count_basis(self):
        def change(d):
            for item in d['records']:
                if item['entity_id']=='SYN-LOT-A':item['basis']='head_count'
        r=self.run_case(change)['reviews'][1]
        self.assertIn('feed_quantity_basis_required',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_stale_closing_keeps_listed_math_but_no_current_complete_balance(self):
        r=self.run_case(lambda d:d['records'][7].update(observed_at='2026-10-19T08:00:00Z'))['reviews'][1]
        self.assertEqual(r['listed_balance'],'1050');self.assertIsNone(r['complete_expected_closing'])
        self.assertIn('snapshot_stale_under_supplied_rule',r['issues'])
    def test_fractional_age_boundary_is_exact(self):
        r=self.run_case(lambda d:d.update(as_of='2026-10-20T10:00:00.000001Z'))['reviews'][1]
        self.assertIn('snapshot_stale_under_supplied_rule',r['issues'])
    def test_closing_age_is_explicit_and_uses_observation_not_recent_recording(self):
        r=self.run_case();self.assertEqual(r['reviews'][1]['closing_age_seconds'],'3600')
        r=self.run_case(lambda d:d['records'][7].update(observed_at='2026-10-18T08:00:00Z'))
        self.assertEqual(r['reviews'][1]['closing_age_seconds'],'176400')
        self.assertIn('176400',markdown(r));r['language']='fr';self.assertIn('176400',markdown(r))
    def test_conflicting_candidates_are_never_labelled_current(self):
        def change(d):
            fork=deepcopy(d['records'][8]);fork.update(id='SYN-FORK',quantity='160');d['records'].append(fork)
        r=self.run_case(change)
        for key in ['SYN-F-OUT','SYN-F-OUT-REV','SYN-FORK']:
            item=next(x for x in r['records'] if x['original']['id']==key)
            self.assertFalse(item['current_as_of']);self.assertEqual(item['revision_state'],'conflicted');self.assertNotIn(key,r['current_ids'])
        self.assertIn('conflicting versions',markdown(r));r['language']='fr';self.assertIn('versions en conflit',markdown(r))
    def test_current_correction_does_not_erase_original_or_adopt_future(self):
        r=self.run_case();self.assertIn('SYN-F-OUT-REV',r['current_ids']);self.assertNotIn('SYN-F-OUT',r['current_ids']);self.assertNotIn('SYN-F-OUT-FUTURE',r['current_ids'])
        self.assertEqual([x['original'] for x in r['records']],self.data['records'])
        self.assertEqual(r['records'][6]['superseded_by'],['SYN-F-OUT-REV'])
    def test_correction_fork_is_unresolved_not_latest_wins(self):
        def change(d):
            fork=deepcopy(d['records'][8]);fork.update(id='SYN-FORK',quantity='160');d['records'].append(fork)
        r=self.run_case(change)['reviews'][1];self.assertIn('correction_fork',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_invalid_correction_reason_parent_entity_time_or_cycle_refused(self):
        changes=[lambda d:d['records'][8].update(correction_reason=None),lambda d:d['records'][8].update(entity_id='SYN-GROUP-A'),
                 lambda d:d['records'][8].update(recorded_at='2026-10-01T00:00:00Z'),lambda d:d['records'][6].update(supersedes='SYN-F-OUT-REV',correction_reason='cycle')]
        for change in changes:
            with self.assertRaises(ValueError):self.run_case(change)
    def test_noncurrent_selected_revision_is_not_silently_replaced(self):
        r=self.run_case(lambda d:d['reviews'][1].update(movement_ids=['SYN-F-IN','SYN-F-OUT']))['reviews'][1]
        self.assertIn('record_not_current_as_of',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_movement_outside_snapshot_interval_refuses_balance(self):
        r=self.run_case(lambda d:d['records'][5].update(observed_at='2026-10-20T08:30:00Z'))['reviews'][1]
        self.assertIn('movement_outside_snapshot_interval',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_unknown_observation_time_is_not_recording_time(self):
        r=self.run_case(lambda d:d['records'][5].update(observed_at=None))['reviews'][1]
        self.assertIn('observation_time_unknown',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_recording_before_observed_event_is_not_silently_accepted(self):
        r=self.run_case(lambda d:d['records'][5].update(recorded_at='2026-10-04T12:00:00Z'))['reviews'][1]
        self.assertIn('recorded_before_observation',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_planned_future_and_outside_period_records_are_not_observed_inventory(self):
        for change,issue in [(lambda d:d['records'][5].update(event_state='planned'),'event_not_observed'),
                             (lambda d:d['records'][5].update(observed_at='2026-10-21T08:00:00Z'),'record_not_current_as_of'),
                             (lambda d:d['records'][5].update(observed_at='2026-09-30T08:00:00Z'),'outside_declared_period_utc')]:
            r=self.run_case(change)['reviews'][1];self.assertIn(issue,r['issues']);self.assertIsNone(r['listed_balance'])
    def test_unknown_identity_species_or_source_is_not_inferred(self):
        for field,value,issue in [('identity_state','unknown','entity_identity_unknown'),('species_as_reported',None,'species_unknown'),('identity_source_ref',None,'identity_source_missing')]:
            r=self.run_case(lambda d:d['entities'][0].update(**{field:value}))['reviews'][0]
            self.assertIn(issue,r['issues']);self.assertIsNone(r['listed_balance'])
    def test_cross_entity_and_missing_references_stay_unresolved(self):
        r=self.run_case(lambda d:d['reviews'][1].update(movement_ids=['SYN-G-IN']))['reviews'][1]
        self.assertIn('entity_mismatch',r['issues']);self.assertIsNone(r['listed_balance'])
        r=self.run_case(lambda d:d['reviews'][1].update(movement_ids=['ABSENT']))['reviews'][1]
        self.assertIn('record_reference_missing',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_fractional_head_count_and_individual_balance_are_unsupported(self):
        r=self.run_case(lambda d:d['records'][0].update(quantity='40.5'))['reviews'][0]
        self.assertIn('fractional_head_count',r['issues'])
        r=self.run_case(lambda d:d['entities'][0].update(kind='animal'))['reviews'][0]
        self.assertIn('individual_balance_unsupported',r['issues'])
    def test_negative_listed_balance_is_not_valid_stock(self):
        r=self.run_case(lambda d:d['records'][8].update(quantity='1300'))['reviews'][1]
        self.assertEqual(r['listed_balance'],'-100');self.assertIn('negative_listed_balance',r['issues']);self.assertIsNone(r['complete_expected_closing'])
    def test_invalid_states_duplicates_bad_numbers_and_roles_refused_or_blocked(self):
        for change in [lambda d:d['records'][1].update(quantity='-1'),lambda d:d['records'][1].update(quantity='1e3'),
                       lambda d:d['records'][1].update(quantity='4',value_state='missing'),lambda d:d['records'][1].update(id=d['records'][0]['id'])]:
            with self.assertRaises(ValueError):self.run_case(change)
        r=self.run_case(lambda d:d['reviews'][1].update(movement_ids=['SYN-F-CLOSE']))['reviews'][1]
        self.assertIn('record_role_mismatch',r['issues'])
    def test_decimal_arithmetic_does_not_round_long_quantities(self):
        def change(d):
            for index,value in [(4,'1000.000000000000000001'),(5,'200.000000000000000002'),(8,'150.000000000000000001')]:d['records'][index]['quantity']=value
        self.assertEqual(self.run_case(change)['reviews'][1]['listed_balance'],'1050.000000000000000002')
    def test_input_immutable_and_standalone_source_context_retained(self):
        data=deepcopy(self.data);before=deepcopy(data);r=livestock.run(data);self.assertEqual(data,before)
        for key in ['enterprise_id','jurisdiction','period','as_of']:self.assertEqual(r['context'][key],data[key])
        for value in ['SYN-CORRECTED-SCALE-LINE','head_count','as_fed','2026-10-13T12:00:00Z','SYN-GROUP-REGISTER']:
            self.assertIn(esc(value),markdown(r))
        self.assertNotIn('Invented evidence only',markdown(r))
    def test_bilingual_canonical_states_and_escaped_untrusted_text(self):
        reports=[]
        for lang in ['en','fr']:
            data=read_document(ROOT/f'examples/ecosystem/livestock-{lang}.json');reports.append(build(self.context(lang),data,self.catalog))
        self.assertEqual(reports[0]['reviews'],reports[1]['reviews']);self.assertNotEqual(markdown(reports[0]).splitlines()[0],markdown(reports[1]).splitlines()[0])
        reports[0]['entities'][0]['identity_source_ref']='[send](https://example.invalid/do)'
        self.assertNotIn('[send](',markdown(reports[0]));self.assertFalse(reports[0]['operational_advice_allowed'])
    def test_output_contract_rejects_physical_or_nutrition_claim(self):
        from workflow_tools.common import validate
        r=build(self.context(),deepcopy(self.data),self.catalog)
        for field in ['physical_completeness_verified','nutrition_or_welfare_established']:
            copy=deepcopy(r);copy['reviews'][0][field]=True
            with self.assertRaises(ValueError):validate('workflow-result',copy)
    def test_reused_record_role_is_a_review_gap_without_schema_crash(self):
        data=deepcopy(self.data);data['reviews'][1]['movement_ids']=['SYN-F-CLOSE']
        r=build(self.context(),data,self.catalog)['reviews'][1]
        self.assertIn('record_role_mismatch',r['issues']);self.assertIsNone(r['listed_balance'])
    def test_cli_scope_checked_before_missing_data_file(self):
        with tempfile.TemporaryDirectory(prefix='ag-livestock-',dir=ROOT/'outputs') as temp:
            p=Path(temp)/'context.json';c=self.context();c['requested_actions']=['clinical_prescription'];p.write_text(json.dumps(c))
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/run_farm_workflow.py'),'--context',str(p),'--input',str(Path(temp)/'absent.json')],capture_output=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'))
            self.assertEqual(r.returncode,0);self.assertFalse(json.loads(r.stdout)['data_read']);self.assertEqual(json.loads(r.stdout)['route']['state'],'blocked_scope')

if __name__=='__main__':unittest.main()
