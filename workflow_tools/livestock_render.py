from .common import safe_markdown as esc

TERMS={
 'recorded_after_as_of':('Recorded after cutoff','Consigné après la date limite'),
 'observation_after_as_of':('Observation after cutoff','Observation après la date limite'),
 'observation_time_unknown':('Observation time is unknown','Date d’observation inconnue'),
 'outside_declared_period_utc':('Outside the declared UTC period','Hors de la période UTC déclarée'),
 'recorded_before_observation':('Recording precedes the observed event','Consignation antérieure à l’événement observé'),
 'event_not_observed':('Event is planned or uncertain','Événement prévu ou incertain'),
 'value_estimated':('Quantity is estimated','Quantité estimée'),
 'value_missing':('Quantity is missing','Quantité manquante'),
 'value_trace':('Trace reported','Trace déclarée'),
 'value_suppressed':('Quantity is withheld','Quantité non divulguée'),
 'record_not_current_as_of':('Selected revision is not current at cutoff','Version sélectionnée non courante à la date limite'),
 'record_reference_missing':('Selected record is absent','Relevé sélectionné absent'),
 'entity_reference_missing':('Selected entity is absent','Entité sélectionnée absente'),
 'entity_mismatch':('Record belongs to a different entity','Relevé associé à une autre entité'),
 'identity_source_missing':('Identity source is missing','Source d’identité manquante'),
 'species_unknown':('Species is unknown','Espèce inconnue'),
 'unit_unknown':('Quantity unit is unknown','Unité quantitative inconnue'),
 'basis_unknown':('Quantity basis is unknown','Base quantitative inconnue'),
 'feed_quantity_basis_required':('Feed requires an as-fed or dry-matter basis','Base telle que distribuée ou de matière sèche requise'),
 'head_count_basis_required':('Group counts require head/head_count','Comptage du groupe en head/head_count requis'),
 'fractional_head_count':('A head count is fractional','Comptage de têtes fractionnaire'),
 'individual_balance_unsupported':('Individual-animal balance is unsupported','Balance d’un animal individuel non prise en charge'),
 'snapshot_order_invalid':('Opening and closing times are inconsistent','Dates initiale et finale incohérentes'),
 'movement_outside_snapshot_interval':('Movement is outside the snapshot interval','Mouvement hors de l’intervalle des relevés'),
 'coverage_source_missing':('Coverage declaration source is missing','Source de déclaration de couverture manquante'),
 'negative_listed_balance':('Listed-record balance is negative','Balance des écritures listées négative'),
 'record_role_mismatch':('Record role differs from the requested arithmetic role','Rôle du relevé différent du rôle de calcul demandé'),
 'snapshot_stale_under_supplied_rule':('Closing snapshot is stale under the supplied age rule','Le relevé final est périmé selon la règle fournie'),
 'unresolved_record_count_difference':('Unresolved record/count difference','Écart de registres ou de comptage non résolu'),
 'movement_coverage_unknown':('Movement coverage is unknown','Couverture des mouvements inconnue'),
 'movement_coverage_partial':('Movement coverage is partial','Couverture des mouvements partielle'),
 'quantity_not_measured':('Quantity is not labelled measured','Quantité non déclarée mesurée'),
 'unit_mismatch':('Units differ; no conversion','Unités différentes ; aucune conversion'),
 'basis_mismatch':('Quantity bases differ; no conversion','Bases quantitatives différentes ; aucune conversion'),
 'entity_identity_unknown':('Entity identity needs confirmation','Identité de l’entité à confirmer'),
 'correction_fork':('Correction versions conflict','Versions corrigées en conflit'),
 'confirm_identity_species_and_snapshot_scope':('Confirm identity, species and snapshot scope','Confirmer identité, espèce et portée des relevés'),
 'verify_selected_sources_and_movement_coverage':('Verify selected sources and movement coverage','Vérifier les sources et la couverture des mouvements'),
 'resolve_record_differences_without_inventing_events':('Resolve differences without inventing missing events','Résoudre les écarts sans inventer d’événements'),
 'refer_clinical_nutrition_or_welfare_questions_to_qualified_reviewer':('Refer clinical, nutrition or welfare questions to the qualified reviewer','Transmettre les questions cliniques, nutritionnelles ou de bien-être au spécialiste compétent'),
 'inspect_notes_and_recipient_scope_before_sharing':('Inspect notes and recipient scope before sharing','Vérifier les notes et la portée du destinataire avant partage'),
}

def markdown(result):
    fr=result['language']=='fr';c=result['context']
    def show(x):return esc('?' if x is None else x)
    def meaning(code):return TERMS.get(code,(code,code))[fr]
    lines=['# '+('Registres des animaux et des aliments à réviser' if fr else 'Livestock and feed records for review'),' ',
        ('Exercice synthétique ; aucune prescription ni approbation opérationnelle.' if fr else 'Synthetic exercise; no prescription or operational approval.'),'',
        ('Tâche' if fr else 'Task')+': '+show(result['task_id'])+'; '+('Entreprise' if fr else 'Enterprise')+': '+show(c['enterprise_id'])+'; '+show(c['jurisdiction']),
        ('Période UTC' if fr else 'UTC date period')+': '+show(c['period']['start'])+' / '+show(c['period']['end'])+'; '+('Date limite' if fr else 'Cutoff')+': '+show(c['as_of']),
        ('Âge maximal du relevé final, secondes' if fr else 'Maximum closing snapshot age, seconds')+': '+show(result['max_snapshot_age_seconds']),
        ('Méthode' if fr else 'Method')+': '+show(result['method_version']),'']
    lines+=['## '+('Entités déclarées' if fr else 'Supplied entities'),'']
    for entity in result['entities']:
        lines+=['- '+show(entity['id'])+'; '+show(entity['kind'])+'; '+show(entity['species_as_reported'])+'; '+show(entity['production_class_as_reported'])+'; '+show(entity['identity_state'])+'; source: '+show(entity['identity_source_ref'])]
    lines+=['','## '+('Relevés et versions' if fr else 'Records and versions'),'']
    states={'measured':('labelled measured','déclarée mesurée'),'estimated':('estimated','estimée'),'missing':('missing','manquante'),'trace':('trace','trace'),'suppressed':('withheld','non divulguée')}
    for item in result['records']:
        x=item['original'];current=('versions en conflit' if fr else 'conflicting versions') if item['revision_state']=='conflicted' else (('courant' if fr else 'current') if item['current_as_of'] else ('conservé, non courant' if fr else 'retained, not current'))
        lines+=['- '+show(x['id'])+'; '+show(x['entity_id'])+'; '+show(x['kind'])+'; '+show(x['quantity'])+' '+show(x['unit'])+' / '+show(x['basis'])+' ('+show(states[x['value_state']][fr])+'); '+current,
                '  '+('Observation' if fr else 'Observed')+': '+show(x['observed_at'])+'; '+('Consignation' if fr else 'Recorded')+': '+show(x['recorded_at'])+'; source: '+show(x['source_ref'])+'; '+show(x['event_state']),
                '  '+('Remplace' if fr else 'Supersedes')+': '+show(x['supersedes'])+'; '+('Motif' if fr else 'Reason')+': '+show(x['correction_reason'])+'; '+('; '.join(show(meaning(code)) for code in item['issues']) or '—')]
    lines+=['','## '+('Balances des relevés sélectionnés' if fr else 'Balances of selected records'),'']
    for x in result['reviews']:
        lines+=['- '+show(x['review_id'])+'; '+show(x['entity_id'])+'; '+show(', '.join(x['selected_record_ids']))+'; '+show(x['unit'])+' / '+show(x['basis']),
            '  '+('Balance des écritures listées' if fr else 'Listed-record balance')+': '+show(x['listed_balance'])+'; '+('Solde attendu, couverture déclarée complète' if fr else 'Expected closing, coverage declared complete')+': '+show(x['complete_expected_closing'])+'; '+('Observé moins attendu' if fr else 'Observed minus expected')+': '+show(x['observed_minus_expected']),
            '  '+('Couverture déclarée' if fr else 'Declared coverage')+': '+show(x['coverage_as_supplied'])+'; source: '+show(x['original_request']['coverage_source_ref'])+'; '+show(', '.join(x['source_refs'])),
            '  '+('Âge du relevé final, secondes depuis observation jusqu’à la date limite' if fr else 'Closing age, seconds from observation to cutoff')+': '+show(x['closing_age_seconds']),
            '  '+('; '.join(show(meaning(code)) for code in x['issues']) or ('arithmétique seulement' if fr else 'arithmetic only'))]
    lines+=['',('La couverture physique, la santé, la nutrition et le bien-être ne sont pas établis. Les notes libres restent dans le JSON.' if fr else 'Physical coverage, health, nutrition and welfare are not established. Free notes remain in JSON.'),'',
            '## '+('Vérifications restantes' if fr else 'Remaining checks'),'']
    lines+=['- '+show(meaning(code)) for code in result['required_reviews']]
    return '\n'.join(lines).replace('\n \n','\n\n')+'\n'
