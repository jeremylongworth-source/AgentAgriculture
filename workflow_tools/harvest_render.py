from .common import safe_markdown as esc

TEXT={
 'enterprise_snapshot_scope_unresolved':('Enterprise snapshot scope is unresolved','Portée du relevé pour l’entreprise non résolue'),
 'snapshot_scope_source_missing':('Snapshot scope source is missing','Source de portée du relevé manquante'),
 'snapshot_location_conflicts_with_enterprise_scope':('Location-specific snapshot cannot establish enterprise balance','Relevé propre à un lieu ne pouvant établir le solde de l’entreprise'),
 'net_mass_unresolved':('Confirmed net mass is unresolved','Masse nette confirmée non résolue'),
 'source_missing':('Record source is missing','Source du relevé manquante'),
 'observation_time_unknown':('Observation time is unknown','Date d’observation inconnue'),
 'outside_declared_period_utc':('Outside the declared UTC period','Hors de la période UTC déclarée'),
 'recorded_before_observation':('Recorded before the stated observation','Consigné avant l’observation indiquée'),
 'event_not_observed':('Event is planned or unknown','Événement prévu ou inconnu'),
 'observation_after_as_of':('Observation is after cutoff','Observation après la date limite'),
 'movement_scope_mismatch':('Movement scope does not match its stated kind','Portée du mouvement incompatible avec son type déclaré'),
 'internal_locations_missing_or_same':('Internal locations are missing or identical','Lieux internes manquants ou identiques'),
 'lot_identity_unresolved':('Lot identity/source is unresolved','Identité ou source du lot non résolue'),
 'record_reference_missing':('Selected record is missing','Relevé sélectionné manquant'),
 'lot_mismatch':('Selected record belongs to a different lot','Relevé sélectionné appartenant à un autre lot'),
 'record_role_mismatch':('Selected record has a different role','Rôle du relevé sélectionné différent'),
 'snapshot_order_invalid':('Opening/closing order is invalid','Ordre initial/final invalide'),
 'movement_outside_snapshot_interval':('Movement is outside the snapshot interval','Mouvement hors de l’intervalle des relevés'),
 'negative_listed_balance':('Listed balance is negative; resolve records','Solde listé négatif ; résoudre les relevés'),
 'commitment_quantity_not_declared':('Commitment quantity is missing or estimated','Quantité d’engagement manquante ou estimée'),
 'commitment_mass_basis_unsupported':('Commitment mass basis/unit is unsupported','Base ou unité de masse de l’engagement non prise en charge'),
 'commitment_source_missing':('Commitment source is missing','Source de l’engagement manquante'),
 'commitment_destination_unknown':('Commitment destination is unknown','Destination de l’engagement inconnue'),
 'commitment_issued_after_as_of':('Commitment was issued after cutoff','Engagement émis après la date limite'),
 'selected_record_not_dispatch':('Selected record is not a dispatch','Relevé sélectionné autre qu’une expédition'),
 'dispatch_destination_mismatch':('Dispatch destination differs from declaration','Destination d’expédition différente de la déclaration'),
 'dispatch_after_declared_due_date':('Dispatch is after declared due date','Expédition après l’échéance déclarée'),
 'verify_lot_identity_sources_and_measurements':('Verify lot identity, sources and measurements','Vérifier identité des lots, sources et mesures'),
 'resolve_units_tare_coverage_and_corrections':('Resolve units, tare, coverage and corrections','Résoudre unités, tare, couverture et corrections'),
 'review_internal_movement_scope_without_double_counting':('Review internal movements without double counting','Réviser mouvements internes sans double comptage'),
 'verify_dispatch_allocation_and_declared_commitment_version':('Verify dispatch allocation and declared commitment version','Vérifier affectation des expéditions et version de l’engagement déclaré'),
 'verify_actual_delivery_and_acceptance_separately':('Verify actual delivery and acceptance separately','Vérifier séparément livraison réelle et acceptation'),
 'obtain_qualified_food_or_contract_interpretation_if_needed':('Obtain qualified food/contract interpretation when needed','Obtenir au besoin une interprétation qualifiée alimentaire ou contractuelle'),
 'movement_coverage_unknown':('Movement coverage unknown','Couverture des mouvements inconnue'),
 'movement_coverage_partial':('Movement coverage partial','Couverture des mouvements partielle'),
 'coverage_source_missing':('Coverage source missing','Source de couverture manquante'),
 'closing_stale_under_supplied_rule':('Closing observation stale under supplied rule','Observation finale périmée selon la règle fournie'),
 'unresolved_lot_record_difference':('Unresolved lot record difference; cause unknown','Écart non résolu dans les relevés du lot ; cause inconnue'),
 'unselected_current_lot_movement':('Current movement omitted from selection','Mouvement courant omis de la sélection'),
 'unresolved_lot_correction_fork':('Lot correction fork unresolved','Branche de correction du lot non résolue'),
 'dispatch_allocation_ambiguous':('Dispatch allocated more than once','Expédition affectée plus d’une fois'),
 'dispatch_coverage_unknown':('Dispatch coverage unknown','Couverture des expéditions inconnue'),
 'dispatch_coverage_partial':('Dispatch coverage partial','Couverture des expéditions partielle'),
 'gross_below_tare':('Gross is below tare','Masse brute inférieure à la tare'),
 'gross_tare_unit_mismatch':('Gross/tare units differ; no conversion','Unités brut/tare différentes ; aucune conversion'),
 'record_not_current_as_of':('Selected record is not current at cutoff','Relevé sélectionné non courant à la date limite'),
 'correction_fork':('Conflicting correction branches','Branches de correction en conflit'),
 'recorded_after_as_of':('Recorded after cutoff','Consigné après la date limite'),
 'net_unit_mismatch':('Net mass units differ; no conversion','Unités de masse nette différentes ; aucune conversion'),
}

def markdown(result):
    fr=result['language']=='fr';context=result['context']
    def show(value):return esc('?' if value is None else value)
    def label(en,fr_text):return fr_text if fr else en
    def meaning(code):
        if code in TEXT:return TEXT[code][fr]
        for prefix,names in [('gross_',('Gross','Brut')),('tare_',('Tare','Tare'))]:
            if code.startswith(prefix):
                suffix=code[len(prefix):]
                endings={'missing':(' is missing',' manquante' if prefix=='tare_' else ' manquant'),'estimated':(' is estimated',' estimée' if prefix=='tare_' else ' estimé'),
                    'trace':(' is reported as trace',' déclaré comme trace'),'suppressed':(' is suppressed',' non divulguée' if prefix=='tare_' else ' non divulgué'),
                    'mass_unit_unsupported':(' mass unit is unsupported',' : unité de masse non prise en charge')}
                if suffix in endings:return names[fr]+endings[suffix][fr]
        return code
    def issues(items):return ['- '+show(meaning(x)) for x in items]
    lines=['# '+label('Lot mass and declared-delivery review','Révision des masses de lots et livraisons déclarées'),' ',
      label('Synthetic record arithmetic; measurement accuracy, food quality and legal fulfilment unverified.','Calcul sur relevés synthétiques ; exactitude des mesures, qualité alimentaire et exécution juridique non vérifiées.'),'',
      label('Task','Tâche')+': '+show(result['task_id'])+'; '+show(context['enterprise_id'])+'; '+show(context['jurisdiction']),
      'UTC: '+show(context['period']['start'])+' / '+show(context['period']['end'])+'; '+label('Cutoff','Date limite')+': '+show(context['as_of']),
      label('Method','Méthode')+': '+show(result['method_version']),'']
    lines += [label('Status','État')+': '+label('Review draft with gaps' if result['state']=='review_draft_with_gaps' else 'Review draft','Brouillon de révision avec lacunes' if result['state']=='review_draft_with_gaps' else 'Brouillon de révision')+' ('+show(result['state'])+')','']
    for lot in result['lots']:
        lines+=[label('Lot identity as supplied','Identité du lot fournie')+': '+show(lot['id'])+'; '+show(lot['commodity_as_reported'])+'; '+show(lot['identity_state'])+'; '+show(lot['identity_source_ref'])]
    for record in result['records']:
        item=record['original'];net=record['net_mass']
        lines+=['','## '+show(item['id'])+'; '+show(item['lot_id'])+'; '+show(item['kind']),
          label('Observed / recorded','Observé / consigné')+': '+show(item['observed_at'])+' / '+show(item['recorded_at'])+'; '+show(item['source_ref']),
          label('Supplied event state','État d’événement fourni')+': '+show(item['event_state']),
          label('Revision / current at cutoff','Révision / courant à la date limite')+': '+show(record['revision_state'])+' / '+show(record['current_as_of']),
          label('Supersedes / reason','Remplace / raison')+': '+show(item['supersedes'])+' / '+show(item['correction_reason']),
          label('Movement scope / from / to','Portée du mouvement / de / vers')+': '+show(item['movement_scope'])+' / '+show(item['from_location_id'])+' / '+show(item['to_location_id'])]
        for field,title in [('gross',label('Gross','Brut')),('tare',label('Tare','Tare'))]:
            x=item[field];lines+=[title+': '+show(x['value'])+' '+show(x['unit'])+'; '+show(x['state'])]
        lines+=[label('Derived net mass','Masse nette calculée')+': '+show(net['quantity'])+' '+show(net['unit'])+'; '+show(net['basis'])]
        lines+=issues(record['issues'])
    for review in result['lot_reviews']:
        q=review['original_request']
        lines+=['','## '+label('Enterprise lot balance','Solde du lot dans l’entreprise')+': '+show(q['id'])+'; '+show(q['lot_id']),
          label('Selected records','Relevés sélectionnés')+': '+show(', '.join(review['selected_record_ids'])),
          label('Supplied coverage / source','Couverture fournie / source')+': '+show(q['coverage'])+' / '+show(q['coverage_source_ref']),
          label('Snapshot scope / source','Portée des relevés initial/final / source')+': '+show(q['snapshot_scope'])+' / '+show(q['snapshot_scope_source_ref']),
          label('Internal moves excluded from balance','Mouvements internes exclus du solde')+': '+show(', '.join(review['excluded_internal_move_ids']) or '[]'),
          label('Unselected current movements','Mouvements courants non sélectionnés')+': '+show(', '.join(review['unselected_current_movement_ids']) or '[]'),
          label('Closing observation age / supplied maximum, seconds','Âge observation finale / maximum fourni, secondes')+': '+show(review['closing_age_seconds'])+' / '+show(result['max_closing_age_seconds']),
          label('Listed balance / complete expected closing / observed minus expected','Solde listé / clôture complète attendue / observé moins attendu')+': '+show(review['listed_balance'])+' / '+show(review['complete_expected_closing'])+' / '+show(review['observed_minus_expected'])+' '+show(review['unit'])+'; net_mass']
        lines+=issues(review['issues'])
    for review in result['delivery_reviews']:
        q=review['original_commitment']
        lines+=['','## '+label('Declared commitment','Engagement déclaré')+': '+show(q['id'])+' @ '+show(q['version'])+'; '+show(q['lot_id']),
          label('Source / issued / due','Source / émis / échéance')+': '+show(q['source_ref'])+' / '+show(q['issued_at'])+' / '+show(q['due_on']),
          label('Destination / dispatch records','Destination / relevés d’expédition')+': '+show(q['destination_id'])+' / '+show(', '.join(q['dispatch_ids']) or '[]'),
          label('Declared quantity / basis','Quantité déclarée / base')+': '+show(q['quantity'])+' '+show(q['unit'])+' / '+show(q['basis'])+'; '+show(q['quantity_state']),
          label('Supplied dispatch coverage / source','Couverture fournie des expéditions / source')+': '+show(q['coverage'])+' / '+show(q['coverage_source_ref']),
          label('Listed dispatch / dispatch minus declared','Expédition listée / expédié moins déclaré')+': '+show(review['listed_dispatch_quantity'])+' / '+show(review['dispatch_minus_declared'])+' '+show(q['unit']),
          label('No delivery, acceptance or legal fulfilment verified.','Livraison, acceptation et exécution juridique non vérifiées.')]
        lines+=issues(review['issues'])
    lines+=['','## '+label('Local handover','Relais local'),show(result['handover']['recipient_role'])+'; '+show(result['handover']['purpose']),
      label('Nothing sent; no permission to ship or execute.','Aucun envoi ; aucune autorisation d’expédier ou d’exécuter.'),'']
    lines+=issues(result['required_reviews']);return '\n'.join(lines).replace('\n \n','\n\n')+'\n'
