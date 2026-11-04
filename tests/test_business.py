from copy import deepcopy
import json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from router.core import Catalog,read_document
from workflow_tools import business
from workflow_tools.common import safe_markdown as esc,validate
from workflow_tools.execute import build
from workflow_tools.render import markdown

class BusinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.data=read_document(ROOT/'examples/ecosystem/business-en.json');cls.catalog=Catalog()
    def case(self,change=None):
        d=deepcopy(self.data)
        if change:change(d)
        return business.run(d)
    def context(self,lang='en'):return read_document(ROOT/f'tests/fixtures/ecosystem/context/business-{lang}.json')
    def test_contribution_cash_and_unknown_profit_are_distinct(self):
        r=self.case();self.assertEqual(r['scenarios'][0]['complete_selected_contribution'],'400');self.assertIsNone(r['scenarios'][0]['net_profit']);self.assertEqual(r['cash_reviews'][0]['complete_selected_net_cash_movement'],'100');self.assertFalse(r['cash_reviews'][0]['whole_farm_cash_flow_established'])
    def test_sensitivity_exact_stated_multipliers_and_held_assumptions(self):
        r=self.case()['scenarios'][0];self.assertEqual([x['conditional_contribution'] for x in r['sensitivity']],['300.0','500.0'])
        self.assertEqual(r['sensitivity'][0]['original_assumption']['variable_cost_multiplier'],'1')
    def test_all_missing_costs_do_not_become_zero_known_subtotal(self):
        def change(d):d['scenarios'][0]['variable_costs'][0].update(amount=None,amount_state='missing')
        r=self.case(change)['scenarios'][0];self.assertIsNone(r['variable_cost_review']['known_subset']);self.assertIsNone(r['listed_contribution']);self.assertIsNone(r['complete_selected_contribution'])
    def test_partial_known_subset_survives_without_complete_contribution(self):
        r=self.case()['scenarios'][1];self.assertEqual((r['revenue_review']['known_subset'],r['variable_cost_review']['known_subset'],r['listed_contribution']),('900','400','500'));self.assertIsNone(r['complete_selected_contribution']);self.assertIn('SYN-COST-B-MISSING',r['variable_cost_review']['excluded_ids'])
    def test_unknown_partial_coverage_keeps_listed_only(self):
        for state in ['unknown','partial']:
            r=self.case(lambda d:d['scenarios'][0].update(coverage=state))['scenarios'][0];self.assertEqual(r['listed_contribution'],'400');self.assertIsNone(r['complete_selected_contribution'])
    def test_unsourced_coverage_cannot_establish_complete_scope(self):
        r=self.case(lambda d:d['scenarios'][0].update(coverage_source_ref=None))['scenarios'][0];self.assertEqual(r['listed_contribution'],'400');self.assertIsNone(r['complete_selected_contribution'])
    def test_different_currency_is_retained_and_excluded_without_fx(self):
        r=self.case(lambda d:d['scenarios'][0]['variable_costs'][0].update(currency='USD'))['scenarios'][0]
        self.assertIsNone(r['complete_selected_contribution']);self.assertEqual(r['original_scenario']['variable_costs'][0]['currency'],'USD');self.assertIn('currency_mismatch_no_fx',r['variable_cost_review']['rows'][0]['issues'])
    def test_unknown_or_mixed_accounting_basis_is_not_summed_as_comparable(self):
        for value in ['cash','unknown']:
            r=self.case(lambda d:d['scenarios'][0]['variable_costs'][0].update(accounting_basis=value))['scenarios'][0];self.assertIsNone(r['complete_selected_contribution'])
        r=self.case(lambda d:d['scenarios'][0].update(accounting_basis='unknown'))['scenarios'][0];self.assertIsNone(r['listed_contribution'])
    def test_period_mismatch_is_visible_and_excluded(self):
        r=self.case(lambda d:d['scenarios'][0]['revenues'][0].update(period={'start':'2026-09-01','end':'2026-09-30'}))['scenarios'][0]
        self.assertIsNone(r['complete_selected_contribution']);self.assertIn('amount_period_mismatch',r['revenue_review']['rows'][0]['issues'])
    def test_missing_source_unknown_or_future_recording_excludes_amount(self):
        for field,value in [('source_ref',None),('recorded_at',None),('recorded_at','2026-10-20T09:00:00.000001Z')]:
            r=self.case(lambda d:d['scenarios'][0]['revenues'][0].update(**{field:value}))['scenarios'][0];self.assertIsNone(r['complete_selected_contribution']);self.assertEqual(r['revenue_review']['excluded_ids'],['SYN-REVENUE-A'])
    def test_explicit_numeric_zero_is_not_missing(self):
        def change(d):d['scenarios'][0]['revenues'][0]['amount']='0';d['scenarios'][0]['variable_costs'][0]['amount']='0'
        r=self.case(change)['scenarios'][0];self.assertEqual(r['complete_selected_contribution'],'0');self.assertEqual(r['variable_cost_review']['known_subset'],'0')
    def test_missing_suppressed_and_numeric_state_value_contradictions_refused(self):
        for state,value in [('budgeted',None),('estimated',None),('missing','0'),('suppressed','1')]:
            with self.assertRaises(ValueError):self.case(lambda d:d['scenarios'][0]['revenues'][0].update(amount_state=state,amount=value))
    def test_assumed_estimated_actual_labels_remain_claims(self):
        for state in ['assumed','estimated','actual_as_reported']:
            r=self.case(lambda d:d['scenarios'][0]['revenues'][0].update(amount_state=state))['scenarios'][0]
            self.assertEqual(r['complete_selected_contribution'],'400');self.assertEqual(r['original_scenario']['revenues'][0]['amount_state'],state);self.assertFalse(r['actual_results_verified'])
    def test_duplicate_row_or_scenario_ids_are_refused(self):
        for change in [lambda d:d['scenarios'][0]['revenues'].append(deepcopy(d['scenarios'][0]['revenues'][0])),lambda d:d['scenarios'].append(deepcopy(d['scenarios'][0])),lambda d:d['scenarios'][0]['variable_costs'][0].update(id='SYN-REVENUE-A')]:
            with self.assertRaises(ValueError):self.case(change)
    def test_conflicting_supplied_versions_do_not_select_latest_automatically(self):
        def change(d):
            x=deepcopy(d['scenarios'][0]['revenues'][0]);x.update(version='newer-supplied-2',amount='9999');d['scenarios'][0]['revenues'].append(x)
        with self.assertRaises(ValueError):self.case(change)
    def test_decimal_precision_and_negative_contribution_preserved(self):
        def change(d):d['scenarios'][0]['revenues'][0]['amount']='0.10';d['scenarios'][0]['variable_costs'][0]['amount']='0.30'
        r=self.case(change)['scenarios'][0];self.assertEqual(r['complete_selected_contribution'],'-0.20');self.assertEqual(r['sensitivity'][0]['conditional_contribution'],'-0.210')
    def test_unknown_currency_never_defaults_to_cad(self):
        r=self.case(lambda d:d.update(currency='unknown'))['scenarios'][0];self.assertIsNone(r['listed_contribution']);self.assertIsNone(r['revenue_review']['known_subset'])
    def test_cash_rejects_accrual_rows_without_changing_scenario(self):
        r=self.case(lambda d:d['cash_reviews'][0]['receipts'][0].update(accounting_basis='accrual'))
        self.assertIsNone(r['cash_reviews'][0]['complete_selected_net_cash_movement']);self.assertEqual(r['scenarios'][0]['complete_selected_contribution'],'400')
    def test_cash_unknown_coverage_retains_selected_movement_not_whole_farm_total(self):
        r=self.case(lambda d:d['cash_reviews'][0].update(coverage='unknown'))['cash_reviews'][0]
        self.assertEqual(r['listed_net_cash_movement'],'100');self.assertIsNone(r['complete_selected_net_cash_movement']);self.assertFalse(r['whole_farm_cash_flow_established'])
    def test_unsourced_sensitivity_is_withheld_independently(self):
        r=self.case(lambda d:d['scenarios'][0]['sensitivity'][0].update(source_ref=None))['scenarios'][0]
        self.assertEqual(r['complete_selected_contribution'],'400');self.assertIsNone(r['sensitivity'][0]['conditional_contribution']);self.assertEqual(r['sensitivity'][1]['conditional_contribution'],'500.0')
    def test_unknown_or_future_sensitivity_time_does_not_override_current_baseline(self):
        for value in [None,'2026-10-20T09:00:00.000001Z']:
            r=self.case(lambda d:d['scenarios'][0]['sensitivity'][0].update(recorded_at=value))['scenarios'][0]
            self.assertEqual(r['complete_selected_contribution'],'400');self.assertIsNone(r['sensitivity'][0]['conditional_contribution']);self.assertEqual(r['sensitivity'][1]['conditional_contribution'],'500.0')
    def test_sensitivity_cannot_use_incomplete_scenario_as_complete_baseline(self):
        for s in self.case()['scenarios'][1]['sensitivity']:self.assertIsNone(s['conditional_contribution']);self.assertIn('complete_selected_contribution_unresolved',s['issues'])
    def test_strict_result_cannot_claim_profit_whole_farm_or_financial_authority(self):
        r=build(self.context(),deepcopy(self.data),self.catalog)
        for mutate in [lambda d:d['scenarios'][0].update(net_profit='400'),lambda d:d['scenarios'][0].update(investment_or_lending_recommendation=True),lambda d:d['cash_reviews'][0].update(whole_farm_cash_flow_established=True),lambda d:d.update(tax_or_eligibility_established=True),lambda d:d['handover'].update(sent=True)]:
            d=deepcopy(r);mutate(d)
            with self.assertRaises(ValueError):validate('workflow-result',d)
    def test_originals_and_bilingual_readable_states_sources_assumptions_survive(self):
        for lang in ['en','fr']:
            d=read_document(ROOT/f'examples/ecosystem/business-{lang}.json');before=deepcopy(d);r=build(self.context(lang),d,self.catalog);view=markdown(r)
            self.assertEqual(d,before);self.assertEqual([x['original_scenario'] for x in r['scenarios']],d['scenarios']);self.assertEqual(r['notes'],d['notes'])
            for value in [d['task_id'],d['as_of'],d['jurisdiction'],'400','100','300.0','500.0','0.9','1.1','missing','SYN-COST-B-MISSING','supplied-2',d['scenarios'][0]['sensitivity'][0]['held_assumptions'],d['scenarios'][0]['excluded_cost_categories'][0],r['state']]:self.assertIn(esc(value),view)
            self.assertNotIn('apply for a loan',view);self.assertFalse(r['handover']['sent'])
    def test_pre_read_operational_advice_block_never_opens_missing_input(self):
        with tempfile.TemporaryDirectory(prefix='ag-business-',dir=ROOT/'outputs') as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to((ROOT/'outputs').resolve()));c=self.context();c['intent']='interpret_operational';p=Path(temp)/'context.json';p.write_text(json.dumps(c))
            r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/run_farm_workflow.py'),'--context',str(p),'--input',str(Path(temp)/'absent.json')],capture_output=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'))
            self.assertEqual(r.returncode,0);self.assertFalse(json.loads(r.stdout)['data_read']);self.assertEqual(json.loads(r.stdout)['route']['state'],'blocked_scope')

if __name__=='__main__':unittest.main()
