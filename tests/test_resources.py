from copy import deepcopy
import hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from router.core import Catalog,read_document
from workflow_tools import resources
from workflow_tools.common import safe_markdown as esc,validate
from workflow_tools.execute import build
from workflow_tools.render import markdown

class ResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read_document(ROOT/'examples/ecosystem/resources-en.json');cls.catalog=Catalog()
    def case(self,change=None):
        d=deepcopy(self.data)
        if change:change(d)
        return resources.run(d)
    def context(self,lang='en'):return read_document(ROOT/f'tests/fixtures/ecosystem/context/resources-{lang}.json')
    def test_exact_selected_version_step_text_order_and_originals_retained(self):
        d=deepcopy(self.data);before=deepcopy(d);r=resources.run(d)
        self.assertEqual(d,before);self.assertEqual(r['procedures'],d['procedures'])
        self.assertEqual(r['cards'][0]['quoted_steps'],d['procedures'][0]['steps'])
        self.assertEqual(r['cards'][0]['selected_procedure_ref']['version'],'1')
        self.assertNotIn('SYN-V2-STEP',[x['id'] for x in r['cards'][0]['quoted_steps']])
    def test_missing_version_does_not_choose_newer_approved_version(self):
        r=self.case(lambda d:d['tasks'][0].update(procedure_version='3'))['cards'][0]
        self.assertEqual(r['quoted_steps'],[]);self.assertIn('selected_procedure_version_missing',r['issues'])
    def test_missing_procedure_withholds_steps_and_keeps_task_claims(self):
        card=self.case()['cards'][1];self.assertEqual(card['quoted_steps'],[])
        self.assertEqual(card['original_task']['completion_state'],'claimed_complete')
        self.assertIn('completion_claim_without_evidence',card['issues'])
    def test_unresolved_requested_procedure_and_version_survive_readable_handover(self):
        for lang in ['en','fr']:
            d=read_document(ROOT/f'examples/ecosystem/resources-{lang}.json')
            d['tasks'][0]['procedure_version']='3'
            r=build(self.context(lang),d,self.catalog);view=markdown(r)
            for task,card in zip(d['tasks'],r['cards']):
                self.assertIsNone(card['selected_procedure_ref']);self.assertEqual(card['quoted_steps'],[])
                self.assertIn(esc(task['procedure_id'])+' @ '+esc(task['procedure_version']),view)
    def test_draft_unknown_missing_source_or_approval_has_no_substitute_steps(self):
        for field,value,issue in [('approval_status','draft','procedure_not_declared_approved'),('approval_status','unknown','procedure_not_declared_approved'),
                                  ('source_ref',None,'procedure_source_missing'),('approval_ref',None,'approval_source_missing'),('approval_recorded_at',None,'approval_time_unknown'),
                                  ('stop_escalation_ref',None,'stop_escalation_source_missing')]:
            r=self.case(lambda d:d['procedures'][0].update(**{field:value}))['cards'][0]
            self.assertEqual(r['quoted_steps'],[]);self.assertIn(issue,r['issues'])
    def test_expired_future_and_unknown_effective_dates_withhold(self):
        for field,value,issue in [('review_due','2026-10-19','procedure_review_due_before_cutoff'),('effective_from','2026-10-21','procedure_not_effective_at_cutoff'),
                                  ('effective_from',None,'procedure_dates_unknown')]:
            r=self.case(lambda d:d['procedures'][0].update(**{field:value}))['cards'][0]
            self.assertEqual(r['quoted_steps'],[]);self.assertIn(issue,r['issues'])
    def test_effective_and_review_boundary_day_is_inclusive(self):
        r=self.case(lambda d:d['procedures'][0].update(effective_from='2026-10-20',review_due='2026-10-20'))['cards'][0]
        self.assertEqual(len(r['quoted_steps']),3)
    def test_future_approval_and_future_task_not_used_at_cutoff(self):
        r=self.case(lambda d:d['procedures'][0].update(approval_recorded_at='2026-10-20T09:00:00.000001Z'))['cards'][0]
        self.assertEqual(r['quoted_steps'],[]);self.assertIn('approval_recorded_after_cutoff',r['issues'])
        r=self.case(lambda d:d['tasks'][0].update(recorded_at='2026-10-21T09:00:00Z'))['cards'][0]
        self.assertEqual(r['quoted_steps'],[]);self.assertIn('task_recorded_after_cutoff',r['issues'])
    def test_wrong_enterprise_jurisdiction_asset_or_role_is_not_reused(self):
        for field,value in [('enterprise_id','SYN-OTHER'),('jurisdiction','CA-AB'),('asset_id','SYN-OTHER-ASSET'),('role','SYN-OTHER-ROLE')]:
            r=self.case(lambda d:d['procedures'][0].update(**{field:value}))['cards'][0]
            self.assertEqual(r['quoted_steps'],[]);self.assertIn('procedure_scope_mismatch:'+field,r['issues'])
    def test_unknown_assigned_context_is_not_filled_from_procedure(self):
        for taskfield,scopefield in [('asset_id','asset_id'),('assigned_role','role')]:
            r=self.case(lambda d:d['tasks'][0].update(**{taskfield:None}))['cards'][0]
            self.assertEqual(r['quoted_steps'],[]);self.assertIn('procedure_scope_unknown:'+scopefield,r['issues'])
    def test_language_mismatch_does_not_generate_translation(self):
        r=self.case(lambda d:d['procedures'][0].update(language='fr'))['cards'][0]
        self.assertEqual(r['quoted_steps'],[]);self.assertIn('procedure_language_mismatch_no_translation',r['issues'])
    def test_translated_source_without_fidelity_reference_is_not_quoted(self):
        d=read_document(ROOT/'examples/ecosystem/resources-fr.json');d['procedures'][0]['fidelity_review_ref']=None
        r=resources.run(d,'fr')['cards'][0];self.assertEqual(r['quoted_steps'],[])
        self.assertIn('translation_fidelity_reference_missing',r['issues'])
    def test_receipt_acknowledgement_never_becomes_competence_or_completion(self):
        r=self.case();card=r['cards'][1]
        self.assertEqual(card['original_task']['acknowledgement_state'],'claimed_received')
        for key in ['source_approval_verified','translation_fidelity_verified','completion_verified','receipt_verified','competence_established']:self.assertFalse(card[key])
        self.assertFalse(r['handover']['sent']);self.assertFalse(r['handover']['competence_established'])
    def test_evidence_pointers_do_not_verify_claims(self):
        def change(d):d['tasks'][0].update(completion_state='claimed_complete',completion_evidence_ref='SYN-COMPLETE-REF',acknowledgement_state='claimed_received',acknowledgement_ref='SYN-RECEIPT-REF',competence_evidence_ref='SYN-COMPETENCE-REF')
        r=self.case(change);self.assertIn('SYN-TASK-A',r['handover']['claimed_complete_task_ids'])
        for key in ['completion_verified','receipt_verified','competence_established']:self.assertFalse(r['cards'][0][key])
    def test_unknown_unavailable_resources_next_owner_and_recipient_remain_gaps(self):
        for availability in ['unknown','unavailable']:
            r=self.case(lambda d:d['tasks'][0].update(resource_availability=availability))['cards'][0]
            self.assertIn('resource_'+availability,r['issues']);self.assertEqual(r['state'],'review_draft_with_gaps')
        r=self.case(lambda d:d.update(handover_recipient_role=None));self.assertIn('handover_recipient_role_unknown',r['issues'])
        self.assertIn('next_owner_role_unknown',r['cards'][1]['issues'])
    def test_failed_unknown_and_open_due_work_are_not_claimed_complete(self):
        for state in ['failed','unknown','open']:
            r=self.case(lambda d:d['tasks'][0].update(completion_state=state,due_on='2026-10-19'))
            self.assertIn('SYN-TASK-A',r['handover']['open_or_unknown_task_ids']);self.assertNotIn('SYN-TASK-A',r['handover']['claimed_complete_task_ids'])
            self.assertIn('open_due_date_before_cutoff',r['cards'][0]['issues'])
    def test_duplicate_procedure_versions_steps_tasks_and_bad_date_order_refused(self):
        def dup(d):
            x=deepcopy(d['procedures'][0]);x['steps'][0]['text']='different duplicate';d['procedures'].append(x)
        for change in [dup,lambda d:d['procedures'][0]['steps'][1].update(id='SYN-S1'),lambda d:d['tasks'][1].update(id='SYN-TASK-A'),
                       lambda d:d['procedures'][0].update(effective_from='2026-11-01')]:
            with self.assertRaises(ValueError):self.case(change)
    def test_unsupported_operating_procedure_domain_rejected(self):
        for domain in ['machine_repair','clinical_care','emergency_response']:
            with self.assertRaises(ValueError):self.case(lambda d:d['procedures'][0].update(domain=domain))
    def test_supplied_procedure_hash_identifies_content_not_approval(self):
        r=self.case();p=self.data['procedures'][0]
        expected=hashlib.sha256(json.dumps(p,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
        self.assertEqual(r['cards'][0]['supplied_procedure_sha256'],expected)
        changed=self.case(lambda d:d['procedures'][0]['steps'][0].update(text='Another supplied desk step.'))
        self.assertNotEqual(changed['cards'][0]['supplied_procedure_sha256'],expected)
    def test_source_context_and_exact_quoted_text_survive_both_readable_languages(self):
        for lang in ['en','fr']:
            d=read_document(ROOT/f'examples/ecosystem/resources-{lang}.json');r=build(self.context(lang),d,self.catalog);view=markdown(r)
            for value in [d['as_of'],d['enterprise_id'],d['jurisdiction'],d['procedures'][0]['approval_ref'],d['procedures'][0]['effective_from'],d['procedures'][0]['review_due'],d['tasks'][1]['exception_refs'][0]]:
                self.assertIn(esc(value),view)
            for step in d['procedures'][0]['steps']:self.assertIn(esc(step['text']),view)
            self.assertFalse(r['operational_advice_allowed']);self.assertFalse(r['handover']['sent'])
    def test_untrusted_source_text_escaped_and_notes_omitted_without_execution(self):
        d=deepcopy(self.data);d['procedures'][0]['steps'][0]['text']='[send](https://example.invalid/do) `system`'
        r=resources.run(d);view=markdown(r)
        self.assertEqual(r['cards'][0]['quoted_steps'][0]['text'],d['procedures'][0]['steps'][0]['text'])
        self.assertNotIn('[send](',view);self.assertNotIn('ignore the procedure',view)
    def test_contract_rejects_claimed_authority_or_sent_state(self):
        r=build(self.context(),deepcopy(self.data),self.catalog)
        for field in ['source_approval_verified','completion_verified','receipt_verified','competence_established']:
            other=deepcopy(r);other['cards'][0][field]=True
            with self.assertRaises(ValueError):validate('workflow-result',other)
        other=deepcopy(r);other['handover']['sent']=True
        with self.assertRaises(ValueError):validate('workflow-result',other)
    def test_pre_read_control_and_certification_scope_blocked(self):
        with tempfile.TemporaryDirectory(prefix='ag-resource-',dir=ROOT/'outputs') as temp:
            self.assertTrue(Path(temp).resolve().is_relative_to((ROOT/'outputs').resolve()))
            for action in ['control_equipment','certify']:
                c=self.context();c['requested_actions']=[action];p=Path(temp)/'context.json';p.write_text(json.dumps(c))
                r=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/run_farm_workflow.py'),'--context',str(p),'--input',str(Path(temp)/'absent.json')],capture_output=True,encoding='utf-8',env=dict(os.environ,PYTHONUTF8='1'))
                self.assertEqual(r.returncode,0);self.assertFalse(json.loads(r.stdout)['data_read']);self.assertEqual(json.loads(r.stdout)['route']['state'],'blocked_scope')

if __name__=='__main__':unittest.main()
