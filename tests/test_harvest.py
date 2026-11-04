from copy import deepcopy
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from router.core import Catalog,read_document
from workflow_tools import harvest
from workflow_tools.common import safe_markdown as esc,validate
from workflow_tools.execute import build
from workflow_tools.render import markdown

class HarvestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=read_document(ROOT/'examples/ecosystem/harvest-en.json');cls.catalog=Catalog()
    def case(self,change=None):
        d=deepcopy(self.data)
        if change:change(d)
        return harvest.run(d)
    def context(self,lang='en'):return read_document(ROOT/f'tests/fixtures/ecosystem/context/harvest-{lang}.json')
    def test_selected_mass_lot_and_declared_dispatch_known_answers(self):
        r=self.case();q=r['lot_reviews'][0];delivery=r['delivery_reviews'][0]
        self.assertEqual((q['listed_balance'],q['complete_expected_closing'],q['observed_minus_expected']),('125','125','-1'))
        self.assertEqual((delivery['listed_dispatch_quantity'],delivery['dispatch_minus_declared']),('25','-5'))
    def test_exact_high_precision_gross_less_tare(self):
        def change(d):d['records'][6]['gross']['value']='999999999999999999999999999999.999999999999';d['records'][6]['tare']['value']='0.000000000001'
        self.assertEqual(self.case(change)['records'][6]['net_mass']['quantity'],'999999999999999999999999999999.999999999998')
    def test_internal_transfer_trace_excluded_from_enterprise_quantity(self):
        q=self.case()['lot_reviews'][0];self.assertEqual(q['excluded_internal_move_ids'],['SYN-INTERNAL']);self.assertEqual(q['listed_balance'],'125')
        for field,value in [('movement_scope','boundary'),('to_location_id','SYN-STORE-A'),('from_location_id',None)]:
            self.assertIsNone(self.case(lambda d:d['records'][4].update(**{field:value}))['lot_reviews'][0]['listed_balance'])
    def test_missing_tare_keeps_gross_and_independent_dispatch_comparison(self):
        def change(d):d['records'][1]['tare'].update(value=None,state='missing')
        r=self.case(change);self.assertEqual(r['records'][1]['original']['gross']['value'],'54');self.assertIsNone(r['lot_reviews'][0]['listed_balance']);self.assertEqual(r['delivery_reviews'][0]['dispatch_minus_declared'],'-5')
    def test_gross_below_tare_does_not_produce_negative_net(self):
        r=self.case()['records'][8];self.assertIsNone(r['net_mass']['quantity']);self.assertIn('gross_below_tare',r['issues'])
    def test_mixed_gross_tare_and_selected_net_units_are_not_converted(self):
        r=self.case();self.assertIsNone(r['records'][9]['net_mass']['quantity']);self.assertIn('gross_tare_unit_mismatch',r['records'][9]['issues'])
        def change(d):
            for field in ['gross','tare']:d['records'][1][field]['unit']='g'
        r=self.case(change)['lot_reviews'][0];self.assertIsNone(r['listed_balance']);self.assertIn('net_unit_mismatch',r['issues'])
    def test_count_volume_unknown_units_do_not_become_mass(self):
        for unit in ['crate','L','unknown',None]:
            def change(d):
                for field in ['gross','tare']:d['records'][0][field]['unit']=unit
            self.assertIsNone(self.case(change)['lot_reviews'][0]['listed_balance'])
    def test_explicit_measured_zero_is_confirmed_numeric_zero(self):
        r=self.case()['records'][6];self.assertEqual(r['net_mass']['quantity'],'0');self.assertEqual(r['net_mass']['issues'],[])
    def test_estimated_trace_suppressed_are_not_measured_zero(self):
        for state,value in [('estimated','0'),('trace',None),('suppressed',None)]:
            def change(d):d['records'][1]['tare'].update(state=state,value=value)
            r=self.case(change);self.assertIsNone(r['records'][1]['net_mass']['quantity']);self.assertIsNone(r['lot_reviews'][0]['complete_expected_closing'])
    def test_quantity_state_value_contradictions_are_refused(self):
        for state,value in [('measured',None),('estimated',None),('missing','0'),('trace','1')]:
            with self.assertRaises(ValueError):self.case(lambda d:d['records'][1]['gross'].update(state=state,value=value))
    def test_unknown_partial_or_unsourced_coverage_only_listed_balance(self):
        for change in [lambda d:d['lot_reviews'][0].update(coverage='unknown'),lambda d:d['lot_reviews'][0].update(coverage='partial'),lambda d:d['lot_reviews'][0].update(coverage_source_ref=None)]:
            q=self.case(change)['lot_reviews'][0];self.assertEqual(q['listed_balance'],'125');self.assertIsNone(q['complete_expected_closing']);self.assertIsNone(q['observed_minus_expected'])
    def test_omitted_relevant_current_movement_contradicts_complete_coverage(self):
        q=self.case(lambda d:d['lot_reviews'][0]['movement_ids'].remove('SYN-RECEIPT'))['lot_reviews'][0]
        self.assertEqual(q['listed_balance'],'75');self.assertIsNone(q['complete_expected_closing']);self.assertEqual(q['unselected_current_movement_ids'],['SYN-RECEIPT'])
    def test_movement_before_opening_is_not_an_omitted_interval_movement(self):
        def change(d):
            d['records'][0].update(observed_at='2026-10-03T08:00:00Z',recorded_at='2026-10-03T09:00:00Z')
            x=deepcopy(d['records'][1]);x.update(id='SYN-PRIOR',observed_at='2026-10-02T08:00:00Z',recorded_at='2026-10-02T09:00:00Z');d['records'].append(x)
        q=self.case(change)['lot_reviews'][0];self.assertEqual(q['complete_expected_closing'],'125');self.assertEqual(q['unselected_current_movement_ids'],[])
    def test_stale_closing_uses_observation_not_recent_recording_time(self):
        def change(d):d['records'][5].update(observed_at='2026-10-19T08:00:00Z',recorded_at='2026-10-20T09:00:00Z')
        q=self.case(change)['lot_reviews'][0];self.assertEqual(q['closing_age_seconds'],'90000');self.assertEqual(q['listed_balance'],'125');self.assertIsNone(q['complete_expected_closing'])
    def test_originals_and_correction_reason_retained_without_mutation(self):
        d=deepcopy(self.data);before=deepcopy(d);r=harvest.run(d)
        self.assertEqual(d,before);self.assertEqual([x['original'] for x in r['records']],d['records']);self.assertNotIn('SYN-DISPATCH-OLD',r['current_ids']);self.assertIn('SYN-DISPATCH-CORRECTED',r['current_ids'])
    def test_future_correction_cannot_replace_current_selected_evidence(self):
        def change(d):d['records'][3]['recorded_at']='2026-10-21T09:00:00Z'
        r=self.case(change);self.assertNotIn('SYN-DISPATCH-CORRECTED',r['current_ids']);self.assertIn('SYN-DISPATCH-OLD',r['current_ids']);self.assertIsNone(r['delivery_reviews'][0]['listed_dispatch_quantity'])
    def test_unselected_fork_remains_a_complete_balance_blocker(self):
        def change(d):
            x=deepcopy(d['records'][3]);x.update(id='SYN-FORK');x['gross']['value']='28';d['records'].append(x);d['lot_reviews'][0]['movement_ids'].remove('SYN-DISPATCH-CORRECTED')
        q=self.case(change)['lot_reviews'][0];self.assertEqual(q['listed_balance'],'150');self.assertIsNone(q['complete_expected_closing']);self.assertIn('unresolved_lot_correction_fork',q['issues'])
    def test_selected_fork_has_no_current_revision_or_delivery_quantity(self):
        def change(d):
            x=deepcopy(d['records'][3]);x.update(id='SYN-FORK');d['records'].append(x)
        r=self.case(change);self.assertIsNone(r['delivery_reviews'][0]['listed_dispatch_quantity'])
        for index in [2,3,10]:self.assertEqual(r['records'][index]['revision_state'],'conflicted');self.assertFalse(r['records'][index]['current_as_of'])
    def test_missing_identity_wrong_lot_or_source_suppresses_selected_math(self):
        for change in [lambda d:d['lots'][0].update(identity_state='unknown'),lambda d:d['lots'][0].update(identity_source_ref=None),lambda d:d['records'][1].update(lot_id='SYN-APPLE-B'),lambda d:d['records'][1].update(source_ref=None)]:
            self.assertIsNone(self.case(change)['lot_reviews'][0]['listed_balance'])
    def test_unobserved_future_outside_or_pre_observation_records_are_not_confirmed(self):
        for change in [lambda d:d['records'][1].update(event_state='planned'),lambda d:d['records'][1].update(observed_at=None),lambda d:d['records'][1].update(recorded_at='2026-10-21T09:00:00Z'),lambda d:d['records'][1].update(recorded_at='2026-10-03T09:00:00Z')]:
            self.assertIsNone(self.case(change)['lot_reviews'][0]['listed_balance'])
    def test_snapshot_and_movement_interval_order_is_checked(self):
        for change in [lambda d:d['records'][0].update(observed_at='2026-10-20T08:00:00Z',recorded_at='2026-10-20T09:00:00Z'),lambda d:d['records'][1].update(observed_at='2026-10-01T08:00:00Z')]:
            self.assertIsNone(self.case(change)['lot_reviews'][0]['listed_balance'])
    def test_duplicate_ids_selections_and_invalid_lineage_are_refused(self):
        for change in [lambda d:d['records'].append(deepcopy(d['records'][0])),lambda d:d['lot_reviews'][0]['movement_ids'].append('SYN-RECEIPT'),lambda d:d['commitments'][0]['dispatch_ids'].append('SYN-DISPATCH-CORRECTED'),lambda d:d['records'][3].update(lot_id='SYN-APPLE-B'),lambda d:d['records'][3].update(correction_reason=None)]:
            with self.assertRaises(ValueError):self.case(change)
    def test_delivery_destination_due_basis_source_and_version_are_explicit(self):
        for change in [lambda d:d['commitments'][0].update(destination_id='SYN-OTHER'),lambda d:d['commitments'][0].update(due_on='2026-10-08'),lambda d:d['commitments'][0].update(basis='package_count'),lambda d:d['commitments'][0].update(source_ref=None),lambda d:d['commitments'][0].update(issued_at='2026-10-21T09:00:00Z')]:
            r=self.case(change)['delivery_reviews'][0];self.assertIsNone(r['listed_dispatch_quantity']);self.assertIsNone(r['dispatch_minus_declared']);self.assertEqual(r['original_commitment']['version'],'supplied-2')
    def test_partial_dispatch_coverage_keeps_listed_not_complete_difference(self):
        q=self.case(lambda d:d['commitments'][0].update(coverage='partial'))['delivery_reviews'][0];self.assertEqual(q['listed_dispatch_quantity'],'25');self.assertIsNone(q['dispatch_minus_declared'])
    def test_one_dispatch_allocated_to_two_commitments_is_ambiguous(self):
        def change(d):
            x=deepcopy(d['commitments'][0]);x['id']='SYN-SECOND-COMMITMENT';d['commitments'].append(x)
        for q in self.case(change)['delivery_reviews']:self.assertEqual(q['listed_dispatch_quantity'],'25');self.assertIsNone(q['dispatch_minus_declared']);self.assertIn('dispatch_allocation_ambiguous',q['issues'])
    def test_strict_result_cannot_claim_accuracy_food_delivery_or_legal_proof(self):
        r=build(self.context(),deepcopy(self.data),self.catalog)
        for field in ['physical_measurement_accuracy_verified','food_grade_shelf_life_established']:
            x=deepcopy(r);x[field]=True
            with self.assertRaises(ValueError):validate('workflow-result',x)
        for field in ['delivery_or_acceptance_verified','legal_fulfilment_established']:
            x=deepcopy(r);x['delivery_reviews'][0][field]=True
            with self.assertRaises(ValueError):validate('workflow-result',x)
    def test_bilingual_readable_retains_units_raw_states_correction_age_and_gaps(self):
        for lang in ['en','fr']:
            d=read_document(ROOT/f'examples/ecosystem/harvest-{lang}.json');r=build(self.context(lang),d,self.catalog);view=markdown(r)
            for value in [d['task_id'],d['jurisdiction'],d['as_of'],d['records'][3]['correction_reason'],d['records'][7]['id'],'31','missing','500','g','SYN-INTERNAL','SYN-DECLARATION-ONLY','supplied-2','3600','125','-5']:
                self.assertIn(esc(value),view)
            self.assertNotIn('send these files',view);self.assertEqual(r['notes'],d['notes']);self.assertFalse(r['handover']['sent'])
    def test_pre_read_external_shipping_block_does_not_open_missing_input(self):
        with tempfile.TemporaryDirectory(prefix='ag-harvest-',dir=ROOT/'outputs') as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to((ROOT/'outputs').resolve()));c=self.context();c['intent']='execute_external';p=Path(temp)/'context.json';p.write_text(json.dumps(c))
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/run_farm_workflow.py'),'--context',str(p),'--input',str(Path(temp)/'absent.json')],capture_output=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'))
            self.assertEqual(r.returncode,0);self.assertFalse(json.loads(r.stdout)['data_read']);self.assertEqual(json.loads(r.stdout)['route']['state'],'blocked_scope')
    def test_readable_status_and_missing_mass_reasons_are_explicit_in_both_languages(self):
        for lang,missing,unresolved in [('en','Tare is missing','Confirmed net mass is unresolved'),('fr','Tare manquante','Masse nette confirmée non résolue')]:
            d=read_document(ROOT/f'examples/ecosystem/harvest-{lang}.json');d['records'][1]['tare'].update(value=None,state='missing')
            r=build(self.context(lang),d,self.catalog);view=markdown(r)
            self.assertIn(esc(r['state']),view);self.assertIn(missing,view);self.assertIn(unresolved,view)
    def test_location_only_unknown_or_unsourced_snapshot_scope_cannot_be_enterprise_balance(self):
        for fields in [{'snapshot_scope':'location_only'},{'snapshot_scope':'unknown'},{'snapshot_scope_source_ref':None}]:
            q=self.case(lambda d:d['lot_reviews'][0].update(**fields))['lot_reviews'][0]
            self.assertIsNone(q['listed_balance']);self.assertIsNone(q['complete_expected_closing']);self.assertIsNone(q['observed_minus_expected'])
        q=self.case(lambda d:d['records'][5].update(to_location_id='SYN-ONLY-STORE-A'))['lot_reviews'][0]
        self.assertIsNone(q['listed_balance']);self.assertIn('snapshot_location_conflicts_with_enterprise_scope',q['issues'])

if __name__=='__main__':unittest.main()
