from .common import safe_markdown as esc

LABELS={
 'selected_procedure_version_missing':('Selected procedure/version is missing','Procédure/version sélectionnée manquante'),
 'procedure_not_declared_approved':('Procedure is not declared approved','Procédure non déclarée approuvée'),
 'approval_source_missing':('Approval source is missing','Source d’approbation manquante'),
 'procedure_source_missing':('Procedure source is missing','Source de procédure manquante'),
 'approval_time_unknown':('Approval time is unknown','Date d’approbation inconnue'),
 'approval_recorded_after_cutoff':('Approval recorded after cutoff','Approbation consignée après la date limite'),
 'procedure_dates_unknown':('Procedure effective/review dates are unknown','Dates d’effet ou de révision inconnues'),
 'procedure_not_effective_at_cutoff':('Procedure is not effective at cutoff','Procédure non en vigueur à la date limite'),
 'procedure_review_due_before_cutoff':('Procedure review is overdue at cutoff','Révision de procédure échue à la date limite'),
 'procedure_language_mismatch_no_translation':('Source language differs; no generated translation','Langue de source différente ; aucune traduction générée'),
 'translation_fidelity_reference_missing':('Translation fidelity review reference is missing','Référence de révision de fidélité manquante'),
 'stop_escalation_source_missing':('Supplied stop/escalation pointer is missing','Référence fournie d’arrêt ou d’escalade manquante'),
 'task_recorded_after_cutoff':('Task record is after cutoff','Relevé de tâche après la date limite'),
 'resource_unknown':('Resource availability is unknown','Disponibilité des ressources inconnue'),
 'resource_unavailable':('Resource is reported unavailable','Ressource déclarée indisponible'),
 'next_owner_role_unknown':('Next owner role is unknown','Prochain rôle responsable inconnu'),
 'competence_evidence_missing':('Competence evidence reference is missing','Référence de preuve de compétence manquante'),
 'completion_claim_without_evidence':('Completion is claimed without an evidence reference','Achèvement déclaré sans référence de preuve'),
 'receipt_claim_without_evidence':('Receipt is claimed without an evidence reference','Réception déclarée sans référence de preuve'),
 'supplied_exceptions_need_review':('Supplied exceptions need review','Exceptions fournies à réviser'),
 'work_state_failed':('Work is reported failed','Travail déclaré échoué'),
 'work_state_unknown':('Work state is unknown','État du travail inconnu'),
 'open_due_date_before_cutoff':('Open task due date is before cutoff','Échéance de tâche ouverte antérieure à la date limite'),
 'handover_recipient_role_unknown':('Handover recipient role is unknown','Rôle destinataire du relais inconnu'),
 'verify_actual_source_approval_scope_version_and_fidelity':('Verify actual source approval, scope, version and fidelity','Vérifier approbation réelle, portée, version et fidélité'),
 'review_resources_exceptions_and_next_owner':('Review resources, exceptions and next owner','Réviser ressources, exceptions et prochain responsable'),
 'verify_completion_and_receipt_separately':('Verify completion and receipt separately','Vérifier achèvement et réception séparément'),
 'assess_actual_competence_separately':('Assess actual competence separately','Évaluer la compétence réelle séparément'),
 'inspect_local_packet_before_any_sharing':('Inspect the local packet before sharing','Vérifier le dossier local avant partage'),
}

def markdown(result):
    fr=result['language']=='fr';context=result['context']
    def show(x):return esc('?' if x is None else x)
    def meaning(code):
        if code.startswith('procedure_scope_'):
            status,field=code.split(':',1);label=('Portée inconnue' if 'unknown' in status else 'Portée différente') if fr else ('Unknown scope' if 'unknown' in status else 'Different scope')
            return label+': '+field
        return LABELS.get(code,(code,code))[fr]
    lines=['# '+('Fiches de révision et relais d’équipe' if fr else 'Review cards and team handover'),' ',
        ('Exercice synthétique ; approbation, achèvement, réception et compétence non vérifiés.' if fr else 'Synthetic exercise; approval, completion, receipt and competence are unverified.'),'',
        ('Tâche' if fr else 'Task')+': '+show(result['task_id'])+'; '+show(context['enterprise_id'])+'; '+show(context['jurisdiction']),
        'UTC: '+show(context['period']['start'])+' / '+show(context['period']['end'])+'; '+('Date limite' if fr else 'Cutoff')+': '+show(context['as_of']),
        ('Méthode' if fr else 'Method')+': '+show(result['method_version']),'']
    for card in result['cards']:
        task=card['original_task'];ref=card['selected_procedure_ref']
        lines+=['## '+show(card['task_id']),'',
            ('Procédure demandée' if fr else 'Requested procedure')+': '+show(task['procedure_id'])+' @ '+show(task['procedure_version']),
            ('Actif' if fr else 'Asset')+': '+show(task['asset_id'])+'; '+('Rôle assigné' if fr else 'Assigned role')+': '+show(task['assigned_role'])+'; '+('Prochain responsable' if fr else 'Next owner')+': '+show(task['owner_next_role']),
            ('Source de tâche' if fr else 'Task source')+': '+show(task['source_ref'])+'; '+show(task['recorded_at'])+'; '+('Échéance' if fr else 'Due')+': '+show(task['due_on']),
            ('État déclaré' if fr else 'Claimed work state')+': '+show(task['completion_state'])+'; '+('Preuve référencée' if fr else 'Referenced evidence')+': '+show(task['completion_evidence_ref']),
            ('Réception déclarée' if fr else 'Claimed receipt')+': '+show(task['acknowledgement_state'])+'; '+show(task['acknowledgement_ref'])+'; '+('Preuve de compétence référencée' if fr else 'Referenced competence evidence')+': '+show(task['competence_evidence_ref']),
            ('Disponibilité déclarée' if fr else 'Supplied resource availability')+': '+show(task['resource_availability'])+'; '+('Exceptions' if fr else 'Exceptions')+': '+show(', '.join(task['exception_refs']) or '[]')]
        if ref:lines += [('Procédure sélectionnée' if fr else 'Selected procedure')+': '+show(ref['id'])+' @ '+show(ref['version'])+'; '+show(ref['source_ref'])+'; '+show(ref['language']),
                         ('Approbation déclarée' if fr else 'Supplied approval')+': '+show(ref['approval_status'])+'; '+show(ref['approval_ref'])+'; '+show(ref['approval_recorded_at']),
                         ('Dates d’effet et de révision' if fr else 'Effective/review dates')+': '+show(ref['effective_from'])+' / '+show(ref['review_due']),
                         ('Portée de source' if fr else 'Source scope')+': '+show(ref['enterprise_id'])+'; '+show(ref['jurisdiction'])+'; '+show(ref['asset_id'])+'; '+show(ref['role']),
                         ('Traduction et fidélité référencées' if fr else 'Referenced translation/fidelity')+': '+show(ref['translation_of_ref'])+'; '+show(ref['fidelity_review_ref']),
                         ('SHA du document fourni analysé' if fr else 'Parsed supplied-procedure SHA')+': '+show(card['supplied_procedure_sha256'])]
        if card['quoted_steps']:
            lines+=['',('Texte fourni cité, approbation non vérifiée :' if fr else 'Quoted supplied text, approval unverified:')]
            lines+=['- '+show(step['id'])+': '+show(step['text']) for step in card['quoted_steps']]
        else:lines+=['',('Étapes non fournies sur cette fiche ; lacunes de source à résoudre.' if fr else 'No steps supplied on this card; resolve source/context gaps.')]
        lines+=['',('Référence d’arrêt ou d’escalade fournie' if fr else 'Supplied stop/escalation reference')+': '+show(card['stop_escalation_ref'])]
        lines+=['- '+show(meaning(code)) for code in card['issues']]
    h=result['handover']
    lines+=['','## '+('Relais local' if fr else 'Local handover'),' ',('Rôle destinataire' if fr else 'Recipient role')+': '+show(h['recipient_role'])+'; '+show(h['purpose']),
        ('Ouvertes ou incertaines' if fr else 'Open or uncertain')+': '+show(', '.join(h['open_or_unknown_task_ids']) or '[]'),
        ('Achèvement déclaré, non vérifié' if fr else 'Claimed complete, unverified')+': '+show(', '.join(h['claimed_complete_task_ids']) or '[]'),
        ('Aucun envoi ; aucune autorisation d’exécution.' if fr else 'Nothing sent; no permission to execute.'),'',
        '## '+('Vérifications restantes' if fr else 'Remaining checks'),'']
    lines+=['- '+show(meaning(code)) for code in [*result['issues'],*result['required_reviews']]]
    return '\n'.join(lines).replace('\n \n','\n\n')+'\n'
