"""Invented supplied-assumption contribution/cash/sensitivity; no financial advice."""
from copy import deepcopy
from decimal import Decimal,localcontext
from router.core import ROOT
from .common import implementation_hash,instant,report,unique,validate

def run(data,language='en',root=ROOT):
    validate('business-input',data,root);unique(data['scenarios']);unique(data['cash_reviews'])
    now=instant(data['as_of']);currency=data['currency']
    def amounts(items,basis):
        unique(items);rows=[];valid=[]
        for item in items:
            if (item['amount_state'] not in {'missing','suppressed'})!=(item['amount'] is not None):raise ValueError('workflow.amount_state_value_mismatch')
            issues=[]
            if item['amount_state'] in {'missing','suppressed'}:issues.append('amount_'+item['amount_state'])
            if currency=='unknown' or item['currency']=='unknown':issues.append('currency_unknown')
            elif item['currency']!=currency:issues.append('currency_mismatch_no_fx')
            if basis=='unknown' or item['accounting_basis']=='unknown':issues.append('accounting_basis_unknown')
            elif item['accounting_basis']!=basis:issues.append('accounting_basis_mismatch')
            if item['period']!=data['period']:issues.append('amount_period_mismatch')
            if item['source_ref'] is None:issues.append('amount_source_missing')
            if item['recorded_at'] is None:issues.append('amount_recording_time_unknown')
            elif instant(item['recorded_at'])>now:issues.append('amount_recorded_after_cutoff')
            if not issues:valid.append(item)
            rows.append({'id':item['id'],'version':item['version'],'included_in_known_subset':not issues,'issues':issues})
        with localcontext() as ctx:
            ctx.prec=160;total=format(sum((Decimal(x['amount']) for x in valid),Decimal(0)),'f') if valid else None
        return {'known_subset':total,'included_ids':[x['id'] for x in valid],'excluded_ids':[r['id'] for r in rows if r['issues']],'rows':rows}
    def subtraction(a,b):
        if a is None or b is None:return None
        with localcontext() as ctx:ctx.prec=160;return format(Decimal(a)-Decimal(b),'f')
    def coverage(request):
        issues=[]
        if request['coverage']!='complete':issues.append('selected_coverage_'+request['coverage'])
        if request['coverage_source_ref'] is None:issues.append('coverage_source_missing')
        return issues
    result=report('business-stewardship-review',data,language);result['method_version']='business-0.1.0';result['currency']=currency
    result['notes']=deepcopy(data['notes']);result['scenarios']=[];result['cash_reviews']=[]
    result['handover']={'recipient_role':data['recipient_role'],'purpose':data['handover_purpose'],'sent':False}
    for request in data['scenarios']:
        unique(request['revenues']+request['variable_costs']);unique(request['sensitivity'])
        revenues=amounts(request['revenues'],request['accounting_basis']);costs=amounts(request['variable_costs'],request['accounting_basis'])
        issues=coverage(request)
        if revenues['excluded_ids']:issues.append('revenue_rows_unresolved')
        if costs['excluded_ids']:issues.append('variable_cost_rows_unresolved')
        listed=subtraction(revenues['known_subset'],costs['known_subset']);complete=listed if not issues else None;sensitivity=[]
        for assumption in request['sensitivity']:
            gaps=[];value=None
            if assumption['source_ref'] is None:gaps.append('sensitivity_source_missing')
            if assumption['recorded_at'] is None:gaps.append('sensitivity_recording_time_unknown')
            elif instant(assumption['recorded_at'])>now:gaps.append('sensitivity_recorded_after_cutoff')
            if complete is None:gaps.append('complete_selected_contribution_unresolved')
            if not gaps:
                with localcontext() as ctx:
                    ctx.prec=160;value=format(Decimal(revenues['known_subset'])*Decimal(assumption['revenue_multiplier'])-Decimal(costs['known_subset'])*Decimal(assumption['variable_cost_multiplier']),'f')
            sensitivity.append({'original_assumption':deepcopy(assumption),'conditional_contribution':value,'issues':gaps})
        result['scenarios'].append({'original_scenario':deepcopy(request),'revenue_review':revenues,'variable_cost_review':costs,
            'listed_contribution':listed,'complete_selected_contribution':complete,'sensitivity':sensitivity,'issues':issues,
            'net_profit':None,'actual_results_verified':False,'investment_or_lending_recommendation':False})
    for request in data['cash_reviews']:
        unique(request['receipts']+request['payments']);receipts=amounts(request['receipts'],'cash');payments=amounts(request['payments'],'cash')
        issues=coverage(request)
        if receipts['excluded_ids']:issues.append('cash_receipt_rows_unresolved')
        if payments['excluded_ids']:issues.append('cash_payment_rows_unresolved')
        listed=subtraction(receipts['known_subset'],payments['known_subset'])
        result['cash_reviews'].append({'original_request':deepcopy(request),'receipt_review':receipts,'payment_review':payments,
            'listed_net_cash_movement':listed,'complete_selected_net_cash_movement':listed if not issues else None,'issues':issues,'whole_farm_cash_flow_established':False})
    if data['recipient_role'] is None:result['issues'].append('recipient_role_unknown')
    result['state']='review_draft_with_gaps' if result['issues'] or any(r['issues'] or any(s['issues'] for s in r['sensitivity']) for r in result['scenarios']) or any(r['issues'] for r in result['cash_reviews']) else 'review_draft'
    result['tax_or_eligibility_established']=False;result['actual_source_authenticity_verified']=False
    result['required_reviews']=['verify_sources_versions_period_currency_and_basis','resolve_missing_and_excluded_costs_without_imputation',
        'keep_contribution_cash_and_net_profit_distinct','review_sensitivity_multipliers_and_held_assumptions',
        'obtain_qualified_financial_interpretation_for_actual_decisions','inspect_recipient_scope_before_sharing']
    result['implementation_sha256']=implementation_hash(__file__);return result
