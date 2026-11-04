from .common import safe_markdown as esc

TEXT={
 'sensitivity_recording_time_unknown':('Sensitivity recording time is unknown','Date de consignation de sensibilité inconnue'),
 'sensitivity_recorded_after_cutoff':('Sensitivity was recorded after cutoff','Sensibilité consignée après la date limite'),
 'amount_missing':('Amount is missing','Montant manquant'),'amount_suppressed':('Amount is suppressed','Montant non divulgué'),
 'currency_unknown':('Currency is unknown','Devise inconnue'),'currency_mismatch_no_fx':('Currency differs; no FX conversion','Devise différente ; aucune conversion'),
 'accounting_basis_unknown':('Accounting basis is unknown','Base comptable inconnue'),'accounting_basis_mismatch':('Accounting bases differ','Bases comptables différentes'),
 'amount_period_mismatch':('Amount period differs','Période du montant différente'),'amount_source_missing':('Amount source is missing','Source du montant manquante'),
 'amount_recording_time_unknown':('Amount recording time is unknown','Date de consignation du montant inconnue'),'amount_recorded_after_cutoff':('Amount recorded after cutoff','Montant consigné après la date limite'),
 'selected_coverage_unknown':('Selected coverage is unknown','Couverture sélectionnée inconnue'),'selected_coverage_partial':('Selected coverage is partial','Couverture sélectionnée partielle'),
 'coverage_source_missing':('Coverage source is missing','Source de couverture manquante'),'revenue_rows_unresolved':('Revenue rows remain unresolved','Lignes de revenus non résolues'),
 'variable_cost_rows_unresolved':('Variable-cost rows remain unresolved','Lignes de coûts variables non résolues'),'cash_receipt_rows_unresolved':('Cash-receipt rows remain unresolved','Lignes d’encaissements non résolues'),
 'cash_payment_rows_unresolved':('Cash-payment rows remain unresolved','Lignes de décaissements non résolues'),'recipient_role_unknown':('Recipient role is unknown','Rôle destinataire inconnu'),
 'sensitivity_source_missing':('Sensitivity assumption source is missing','Source d’hypothèse de sensibilité manquante'),'complete_selected_contribution_unresolved':('Complete selected contribution is unresolved','Contribution sélectionnée complète non résolue'),
 'verify_sources_versions_period_currency_and_basis':('Verify sources, versions, period, currency and basis','Vérifier sources, versions, période, devise et base'),
 'resolve_missing_and_excluded_costs_without_imputation':('Resolve missing/excluded costs without imputation','Résoudre coûts manquants/exclus sans imputation'),
 'keep_contribution_cash_and_net_profit_distinct':('Keep contribution, cash and net profit distinct','Distinguer contribution, trésorerie et bénéfice net'),
 'review_sensitivity_multipliers_and_held_assumptions':('Review sensitivity multipliers and held assumptions','Réviser multiplicateurs de sensibilité et hypothèses maintenues'),
 'obtain_qualified_financial_interpretation_for_actual_decisions':('Obtain qualified financial interpretation for actual decisions','Obtenir une interprétation financière qualifiée pour les décisions réelles'),
 'inspect_recipient_scope_before_sharing':('Inspect recipient scope before sharing','Vérifier la portée du destinataire avant partage')}

def markdown(result):
    fr=result['language']=='fr';context=result['context']
    def label(en,frtext):return frtext if fr else en
    def show(x):return esc('?' if x is None else x)
    def issues(codes):return ['- '+show(TEXT.get(x,(x,x))[fr]) for x in codes]
    def rows(request,review,title):
        lines=['### '+title]
        for item,checked in zip(request,review['rows']):
            lines+=[show(item['id'])+' @ '+show(item['version'])+': '+show(item['amount'])+' '+show(item['currency'])+'; '+show(item['amount_state'])+'; '+show(item['accounting_basis']),
                label('Source / recorded / period','Source / consigné / période')+': '+show(item['source_ref'])+' / '+show(item['recorded_at'])+' / '+show(item['period']['start'])+' - '+show(item['period']['end']),
                label('Included in compatible known subset','Inclus dans le sous-ensemble connu compatible')+': '+show(checked['included_in_known_subset'])]
            lines+=issues(checked['issues'])
        lines+=[label('Compatible known subtotal','Sous-total connu compatible')+': '+show(review['known_subset'])+' '+show(result['currency'])];return lines
    lines=['# '+label('Supplied-assumption business review','Révision économique des hypothèses fournies'),' ',
        label('Synthetic conditional arithmetic; actual results, net profit and whole-farm cash flow remain unverified.','Calcul conditionnel synthétique ; résultats réels, bénéfice net et trésorerie de toute l’entreprise non vérifiés.'),'',
        label('Status','État')+': '+label('Review draft with gaps' if result['state']=='review_draft_with_gaps' else 'Review draft','Brouillon de révision avec lacunes' if result['state']=='review_draft_with_gaps' else 'Brouillon de révision')+' ('+show(result['state'])+')',
        label('Task / enterprise / jurisdiction','Tâche / entreprise / territoire')+': '+show(result['task_id'])+' / '+show(context['enterprise_id'])+' / '+show(context['jurisdiction']),
        'UTC: '+show(context['period']['start'])+' / '+show(context['period']['end'])+'; '+label('Cutoff','Date limite')+': '+show(context['as_of']),
        label('Method','Méthode')+': '+show(result['method_version']),'']
    for item in result['scenarios']:
        q=item['original_scenario'];lines+=['## '+show(q['id'])+' @ '+show(q['version'])+'; '+show(q['label']),
            label('Accounting basis / supplied coverage / source','Base comptable / couverture fournie / source')+': '+show(q['accounting_basis'])+' / '+show(q['coverage'])+' / '+show(q['coverage_source_ref'])]
        lines+=rows(q['revenues'],item['revenue_review'],label('Scenario revenue','Revenus du scénario'))+rows(q['variable_costs'],item['variable_cost_review'],label('Scenario variable costs','Coûts variables du scénario'))
        lines+=[label('Listed contribution / complete selected contribution','Contribution listée / contribution sélectionnée complète')+': '+show(item['listed_contribution'])+' / '+show(item['complete_selected_contribution'])+' '+show(result['currency']),
            label('Excluded cost categories','Catégories de coûts exclues')+': '+show(', '.join(q['excluded_cost_categories'])),
            label('Net profit unknown; no investment or lending recommendation.','Bénéfice net inconnu ; aucune recommandation de placement ou de prêt.')]
        lines+=issues(item['issues'])
        for sensitivity in item['sensitivity']:
            a=sensitivity['original_assumption'];lines+=[label('Conditional sensitivity','Sensibilité conditionnelle')+': '+show(a['id'])+' @ '+show(a['version'])+'; '+show(a['source_ref'])+'; '+show(a['recorded_at']),
                label('Revenue multiplier / variable-cost multiplier','Multiplicateur revenus / multiplicateur coûts variables')+': '+show(a['revenue_multiplier'])+' / '+show(a['variable_cost_multiplier']),
                label('Held assumptions','Hypothèses maintenues')+': '+show(a['held_assumptions']),
                label('Conditional contribution','Contribution conditionnelle')+': '+show(sensitivity['conditional_contribution'])+' '+show(result['currency'])]
            lines+=issues(sensitivity['issues'])
    for item in result['cash_reviews']:
        q=item['original_request'];lines+=['','## '+label('Separate cash movement','Mouvement de trésorerie distinct')+': '+show(q['id'])+' @ '+show(q['version']),
            label('Supplied coverage / source','Couverture fournie / source')+': '+show(q['coverage'])+' / '+show(q['coverage_source_ref'])]
        lines+=rows(q['receipts'],item['receipt_review'],label('Cash receipts','Encaissements'))+rows(q['payments'],item['payment_review'],label('Cash payments','Décaissements'))
        lines+=[label('Listed / complete selected net cash movement','Mouvement net listé / sélectionné complet')+': '+show(item['listed_net_cash_movement'])+' / '+show(item['complete_selected_net_cash_movement'])+' '+show(result['currency']),
            label('Whole-farm cash flow is not established.','Trésorerie de toute l’entreprise non établie.')];lines+=issues(item['issues'])
    lines+=['','## '+label('Local handover','Relais local'),show(result['handover']['recipient_role'])+'; '+show(result['handover']['purpose']),
        label('Nothing sent; no tax, eligibility or financial decision is established.','Aucun envoi ; aucune décision fiscale, d’admissibilité ou financière établie.')]
    lines+=issues(result['issues']+result['required_reviews']);return '\n'.join(lines).replace('\n \n','\n\n')+'\n'
