from .common import safe_markdown as esc

PHRASES={
 'resource_requirements_unknown':('Required resources are unknown','Ressources nécessaires inconnues'),
 'resource_calendar_missing':('Resource availability is missing','Disponibilité d’une ressource manquante'),
 'dependencies_not_jointly_scheduled':('Predecessor work still needs scheduling','Les travaux préalables restent à planifier'),
 'no_calendar_candidate':('No interval fits the supplied constraints','Aucun intervalle ne respecte les contraintes fournies'),
 'evidence_stale':('Evidence is stale under the declared rule','Preuve périmée selon la règle déclarée'),
 'location_mismatch':('Location identity differs','Identité de lieu différente'),
 'unit_mismatch':('Units differ','Unités différentes'),
 'quality_unreviewed':('Quality has not been reviewed','Qualité non révisée'),
 'task_window_not_covered':('Forecast does not cover the task interval','La prévision ne couvre pas l’intervalle de travail'),
 'forecast_expired':('Forecast has expired','Prévision expirée'),
 'time_order_invalid':('Source time order is inconsistent','Ordre des dates de source incohérent'),
 'observation_is_not_future_forecast':('An observation does not establish future conditions','Une observation ne détermine pas les conditions futures'),
 'criterion_reference_missing':('The declared criterion has no source reference','Le critère déclaré n’a pas de référence'),
 'condition_unknown':('Conditions need clarification','Conditions à préciser'),
 'condition_not_candidate':('Excluded by the supplied criterion','Exclu par le critère fourni'),
 'window_elapsed':('The interval has elapsed','L’intervalle est terminé'),
 'observation_time_unknown':('Observation time is unknown','Date d’observation inconnue'),
 'event_not_observed':('Event is planned or uncertain','Événement planifié ou incertain'),
 'recorded_after_as_of':('Recorded after the review cutoff','Consigné après la date de révision'),
 'observation_after_as_of':('Observation is after the review cutoff','Observation après la date de révision'),
 'outside_declared_period_utc':('Outside declared period by UTC date','Hors période déclarée selon la date UTC'),
 'observation_outside_declared_period_utc':('A record falls outside the declared UTC period','Un relevé est hors de la période UTC déclarée'),
 'correction_fork':('Correction versions conflict','Versions corrigées en conflit'),
 'observation_reference_missing':('A selected observation is missing','Une observation sélectionnée manque'),
 'observation_not_current_as_of':('A selected revision is not current at cutoff','Une version sélectionnée n’est pas courante à la date limite'),
 'value_not_measured':('A value is not labelled measured','Une valeur n’est pas déclarée mesurée'),
 'value_estimated':('Value is estimated','Valeur estimée'),
 'value_missing':('Value is missing','Valeur manquante'),
 'value_trace':('Trace reported','Trace déclarée'),
 'value_suppressed':('Value is withheld','Valeur non divulguée'),
 'confirm_actual_weather_alerts_and_field_conditions':('Check actual applicable warnings and field conditions','Vérifier les avertissements applicables et les conditions réelles du terrain'),
 'review_declared_criteria_and_procedure':('Review the supplied criteria and procedure','Réviser les critères et la procédure fournis'),
 'choose_options_and_resolve_dependencies_resources':('Select options jointly and resolve dependencies/resources','Choisir les options ensemble et résoudre les dépendances et ressources'),
 'no_operational_permission_from_calendar_fit':('Calendar fit does not authorize operation','La compatibilité du calendrier n’autorise pas l’opération'),
 'confirm_entity_observation_method_and_source_meaning':('Check entity, observation method and source meaning','Vérifier l’entité, la méthode d’observation et le sens des sources'),
 'resolve_conflicts_and_missing_context':('Resolve conflicting versions and missing context','Résoudre les conflits de versions et le contexte manquant'),
 'professional_interpretation_if_requested':('Obtain appropriate professional interpretation when needed','Obtenir l’interprétation professionnelle appropriée au besoin'),
 'inspect_notes_and_recipient_scope_before_sharing':('Inspect notes and recipient scope before sharing','Vérifier les notes et la portée du destinataire avant partage'),
}

def meaning(code,fr):
    if code in PHRASES:return PHRASES[code][fr]
    for prefix,terms in [('metadata_missing:',('Missing metadata','Métadonnée manquante')),('metadata_mismatch:',('Different metadata','Métadonnée différente'))]:
        if code.startswith(prefix):
            field=code.split(':',1)[1]
            if fr:field={'entity_id':'identité d’entité','metric':'mesure','unit':'unité','method':'méthode','basis':'base','sampling_scope':'portée d’échantillonnage'}.get(field,field)
            return terms[fr]+': '+field
    return code

def markdown(result):
    if result.get('workflow')=='business-stewardship-review':
        from .business_render import markdown as business_markdown
        return business_markdown(result)
    if result.get('workflow')=='harvest-storage-delivery':
        from .harvest_render import markdown as harvest_markdown
        return harvest_markdown(result)
    if result['workflow']=='resource-team-coordination':
        from .resource_render import markdown as resource_markdown
        return resource_markdown(result)
    if result['workflow']=='livestock-record-review':
        from .livestock_render import markdown as livestock_markdown
        return livestock_markdown(result)
    fr=result['language']=='fr'
    title=('Options de travail conditionnelles' if fr else 'Conditional work options') if result['workflow']=='season-work-planning' else ('Dossier d’observations à réviser' if fr else 'Observation review packet')
    lines=['# '+title,'',('Exercice synthétique. Révision requise ; aucune autorisation opérationnelle.' if fr else 'Synthetic exercise. Review required; no operational permission.'),'']
    context=result['context'];period=context['period']
    def details(pairs):
        return '; '.join(esc(label)+': '+esc('?' if value is None else value) for label,value in pairs)
    lines += [details([('Tâche' if fr else 'Task',result['task_id']),('Entreprise' if fr else 'Enterprise',context['enterprise_id']),
                       ('Juridiction' if fr else 'Jurisdiction',context['jurisdiction'])]),
              details([('Période UTC' if fr else 'UTC date period',period['start']+' / '+period['end']),
                       ('Date limite' if fr else 'Review cutoff',context['as_of']),('Méthode' if fr else 'Method',result['method_version'])]),'']
    if result['workflow']=='season-work-planning':
        lines+=['| '+('Tâche | Fenêtre UTC | Début possible UTC | Lacunes' if fr else 'Task | UTC window | Possible UTC start | Gaps')+' |','| --- | --- | --- | --- |']
        for item in result['tasks']:
            if not item['candidates']:
                lines.append('| '+esc(item['task_id'])+' | — | — | '+esc('; '.join(meaning(x,fr) for x in item['issues']))+' |')
            for candidate in item['candidates']:
                lines.append('| '+esc(item['task_id'])+' | '+esc(candidate['start']+' / '+candidate['end'])+' | '+esc(candidate['earliest_start']+' / '+candidate['latest_start'])+' | '+esc('; '.join(meaning(x,fr) for x in item['issues']))+' |')
        lines+=['',('Conflits de ressources partagées : ' if fr else 'Shared-resource conflicts: ')+esc(len(result['shared_resource_conflicts'])),
                ('Alertes non vérifiées ; les fenêtres ne forment pas un horaire approuvé.' if fr else 'Alerts are not checked; candidate windows are not an approved joint schedule.')]
        for item in result['weather_review']:
            if item['issues']:lines.append('- '+esc(item['window_id'])+': '+esc('; '.join(meaning(x,fr) for x in item['issues'])))
        lines+=['','## '+('Contraintes et sources déclarées' if fr else 'Supplied constraints and sources'),'']
        lines.append(details([('Lieu' if fr else 'Location',result['weather_policy']['location_id']),
                              ('Unité' if fr else 'Unit',result['weather_policy']['weather_unit']),
                              ('Âge maximal en secondes' if fr else 'Maximum age in seconds',result['weather_policy']['max_weather_age_seconds'])]))
        for item in result['tasks']:
            original=item['original']
            lines.append('- '+details([('ID',item['task_id']),('Durée en minutes' if fr else 'Duration in minutes',original['duration_minutes']),
                ('Fenêtre demandée' if fr else 'Requested interval',original['earliest']+' / '+original['latest']),
                ('État des ressources' if fr else 'Resource declaration',original['resource_requirement_state']),
                ('Ressources' if fr else 'Resources',', '.join(original['resource_ids']) or '[]'),
                ('Préalables' if fr else 'Predecessors',', '.join(original['depends_on']) or '[]')]))
        for resource in result['resources']:
            lines.append('- '+details([('Ressource' if fr else 'Resource',resource['id']),
                ('Disponibilité' if fr else 'Availability','; '.join(x['start']+' / '+x['end'] for x in resource['availability']) or '[]')]))
        for item in result['weather_review']:
            original=item['original_evidence']
            lines.append('- '+details([('Fenêtre' if fr else 'Window',item['window_id']),
                ('Intervalle déclaré' if fr else 'Declared interval',item['declared_window']['start']+' / '+item['declared_window']['end']),('Source',item['source_id']),
                ('Type',original['kind']),('Lieu' if fr else 'Location',original['location_id']),
                ('Valeur' if fr else 'Value',original.get('value')),('Unité' if fr else 'Unit',original['unit']),
                ('État' if fr else 'State',original['value_state']),('Qualité déclarée' if fr else 'Supplied quality',original['quality']),
                ('Émission' if fr else 'Issued',original.get('issued_at')),('Observation' if fr else 'Observed',original.get('observed_at')),
                ('Récupération' if fr else 'Retrieved',original['retrieved_at']),
                ('Validité' if fr else 'Validity',str(original.get('valid_start'))+' / '+str(original.get('valid_end'))),
                ('Critère' if fr else 'Criterion',item['criterion_ref']),('Condition déclarée' if fr else 'Declared condition',item['declared_condition'])]))
    else:
        lines+=['| ID | '+('Entité | Observation déclarée | Valeur et unité | Version | Lacunes' if fr else 'Entity | Supplied observation time | Value and unit | Version | Gaps')+' |','| --- | --- | --- | --- | --- | --- |']
        for item in result['observations']:
            original=item['original']
            state_label={'measured':('labelled measured','déclarée mesurée'),'estimated':('estimated','estimée'),
                         'missing':('missing','manquante'),'trace':('trace','trace'),'suppressed':('withheld','non divulguée')}[original['value_state']][fr]
            value=state_label if original['value'] is None else original['value']+' ('+state_label+')'
            version=('courante à la date limite' if fr else 'current at cutoff') if item['current_as_of'] else ('version conservée, non courante' if fr else 'retained, not current')
            lines.append('| '+esc(original['id'])+' | '+esc(original['entity_id'])+' | '+esc(original['observed_at'] or ('non datée' if fr else 'undated'))+' | '+esc(value+' '+(original['unit'] or '?'))+' | '+esc(version)+' | '+esc('; '.join(meaning(x,fr) for x in item['issues']))+' |')
        lines+=['','## '+('Comparaisons' if fr else 'Comparisons'),'']
        for item in result['comparisons']:
            lines.append('- '+esc(item['comparison_id'])+' ('+esc(item['right'])+' − '+esc(item['left'])+'): '+esc(item['difference_right_minus_left'] if item['difference_right_minus_left'] is not None else ('non résolue' if fr else 'unresolved'))+' '+esc(item['unit'] or '?')+'; '+esc('; '.join(meaning(x,fr) for x in item['issues']) or ('arithmétique seulement' if fr else 'arithmetic only')))
        lines+=['','## '+('Entités et méthodes déclarées' if fr else 'Supplied entities and methods'),'']
        for entity in result['entities']:
            lines.append('- '+details([('Entité' if fr else 'Entity',entity['id']),('Type',entity['type']),
                ('Culture déclarée' if fr else 'Supplied crop',entity['crop_as_reported']),('Stade déclaré' if fr else 'Supplied stage',entity['stage_as_reported'])]))
        for item in result['observations']:
            original=item['original']
            lines.append('- '+details([('ID',original['id']),('Source',original['source_ref']),
                ('Mesure' if fr else 'Metric',original['metric']),('Méthode' if fr else 'Method',original['method']),
                ('Base' if fr else 'Basis',original['basis']),('Portée' if fr else 'Sampling scope',original['sampling_scope']),
                ('Consignation' if fr else 'Recorded',original['recorded_at']),
                ('Remplace' if fr else 'Supersedes',original['supersedes']),('Motif de correction' if fr else 'Correction reason',original['correction_reason'])]))
        lines+=['',('Les originaux et corrections sont conservés dans le JSON. Aucune interprétation agronomique.' if fr else 'Originals and corrections are retained in JSON. No agronomic interpretation.')]
    lines+=['','## '+('Vérifications restantes' if fr else 'Remaining checks'),'']
    lines+=['- '+esc(meaning(x,fr)) for x in result['required_reviews']]
    return '\n'.join(lines)+'\n'
