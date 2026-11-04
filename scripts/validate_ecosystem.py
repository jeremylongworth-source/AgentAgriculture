"""Check implemented compositions and deterministic scenario expectations offline."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from router.core import Catalog, ROOT, member, read_document


def check(root=ROOT):
    root = Path(root).resolve()
    catalog = Catalog(root)
    corpus = read_document(root / 'tests/expected-routing.yaml')
    if set(corpus) != {'schema_version', 'scenarios'} or corpus['schema_version'] != '1.0.0':
        raise ValueError('scenario.corpus_shape')
    checked = []
    for key, expected in corpus['scenarios'].items():
        prompt = member(root, expected['prompt_file'], 'tests/scenarios/').read_text(encoding='utf-8')
        if len(prompt.split()) < 20 or 'Synthetic evaluation prompt' not in prompt:
            raise ValueError('scenario.missing_realistic_synthetic_prompt')
        context = read_document(member(root, expected['context_file'], 'tests/fixtures/ecosystem/context/'))
        if context.get('evidence_kind') != 'synthetic':
            raise ValueError('scenario.real_data_refused')
        result = catalog.route(context)
        if result['state'] != expected['expected_state'] or result['skills'] != expected['expected_routes']:
            raise ValueError('scenario.routing_mismatch:' + key)
        if result['messages'][0]['code'] != expected['expected_code'] or set(result['missing_context']) != set(expected['missing_context']):
            raise ValueError('scenario.context_or_code_mismatch:' + key)
        if expected['required_review'] and expected['required_review'] not in result['review_requirements']:
            raise ValueError('scenario.dropped_review:' + key)
        if result['execution_allowed'] or result['field_use_validated'] or any(skill not in catalog.skills for skill in result['skills']):
            raise ValueError('scenario.false_authority:' + key)
        if expected.get('input_file'):
            from workflow_tools.execute import build
            data=read_document(member(root,expected['input_file'],'tests/fixtures/ecosystem/workflows/'))
            domain=build(context,data,catalog)
            checks=expected['expected_output']
            if domain['state']!=checks['state']:
                raise ValueError('scenario.workflow_state_mismatch:'+key)
            if 'lot_balance' in checks and domain['lot_reviews'][0]['listed_balance']!=checks['lot_balance']:raise ValueError('scenario.lot_balance_mismatch:'+key)
            if 'delivery_difference' in checks and domain['delivery_reviews'][0]['dispatch_minus_declared']!=checks['delivery_difference']:raise ValueError('scenario.delivery_difference_mismatch:'+key)
            if 'selected_contribution' in checks and domain['scenarios'][0]['complete_selected_contribution']!=checks['selected_contribution']:raise ValueError('scenario.contribution_mismatch:'+key)
            if 'selected_cash_movement' in checks and domain['cash_reviews'][0]['complete_selected_net_cash_movement']!=checks['selected_cash_movement']:raise ValueError('scenario.cash_movement_mismatch:'+key)
            if 'candidate_count' in checks and domain['candidate_count']!=checks['candidate_count']:
                raise ValueError('scenario.calendar_options_mismatch:'+key)
            if 'quoted_step_count' in checks and sum(len(c['quoted_steps']) for c in domain['cards'])!=checks['quoted_step_count']:
                raise ValueError('scenario.procedure_fidelity_mismatch:'+key)
            if 'comparison_value' in checks and domain['comparisons'][0]['difference_right_minus_left']!=checks['comparison_value']:
                raise ValueError('scenario.comparison_mismatch:'+key)
        checked.append({'scenario': key, 'state': result['state'], 'skills': result['skills'], 'language': result['language']})
    actual = {p.relative_to(root).as_posix() for p in (root / 'tests/scenarios').glob('*.md')}
    declared = {v['prompt_file'] for v in corpus['scenarios'].values()}
    if actual != declared:
        raise ValueError('scenario.undeclared_or_missing_prompt')
    return {'status': 'passed_structural_and_deterministic_scenarios', 'skills': len(catalog.skills),
            'compositions': len(catalog.compositions), 'scenarios': checked, 'live_agent_evaluation': False,
            'field_use_validated': False, 'catalog_sha256': catalog.digest}


def main():
    try:
        print(json.dumps(check(), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, RecursionError) as error:
        print('FAIL ecosystem validation: ' + str(error), file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
