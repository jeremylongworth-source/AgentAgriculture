# Supplied-procedure review cards and local handover

Repository-local synthetic-only routine desk record-checking prototype. Example:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/resources-fr.json --input examples/ecosystem/resources-fr.json --format markdown
```

Each task selects an exact supplied procedure ID/version. Duplicate versions are
refused; no latest-version fallback. Source approval pointers/time, effective/review
dates, enterprise/jurisdiction/asset/role, language/fidelity and stop/escalation
references must fit before verbatim steps are quoted. Missing/draft/expired/future/
mismatched source yields no replacement steps. Source text is data, never executed.
The helper does not translate, inspect approvals or establish source authenticity.
Only routine_record_check is accepted, excluding machinery/clinical/safety/emergency
procedures. Procedures and original tasks remain intact in JSON.

Readable EN/FR cards retain exact steps, source scope/dates and a canonical parsed-
procedure hash, plus resource availability, exceptions, due date and next role.
The requested procedure ID/version remains visible even when no exact source resolves;
the selected-source metadata and quoted steps remain absent in that case.
Open/failed/unknown work and claimed completion remain distinct. Evidence pointers,
acknowledgement or a save cannot establish completed work, actual receipt, language
fidelity or competence: all corresponding verification flags remain false. A local
handover states its intended reader/purpose and sends nothing. Free notes stay in
canonical JSON; inspect recipient scope before sharing. Context/intent and 256 KiB
input bounds apply; prior record, season/crop and livestock methods stay independent.

## Source and authority boundary

The owner-side 2026-10-17 method check used CCOHS
[orientation guidance](https://www.ccohs.ca/oshanswers/hsprograms/orientation.html)
and [hazardous-energy guidance](https://www.ccohs.ca/oshanswers/hsprograms/lockout.html)
to distinguish supplied workplace procedures, role context and recordkeeping from
actual work/competence/approval. These are historical reference links, not rechecked
current requirements in this packaging change. Neither page supplies the selected
farm procedure or jurisdictional legal authority. No safety sequence is reproduced.

This helper's boundary is therefore invented routine desk record-checking only.
Retain exact source ID/version/language/text and supplied review/expiry/role scope;
withhold steps when context fails. Acknowledgement, a signature or a source pointer
does not authenticate approval, verify actual completion or establish competence.
Appropriate responsible people retain actual procedure and operational authority.

The [local source-package guide](../../skillsets/resource-team-coordination/SOURCE-PACKAGE.md)
provides clean setup, expected example outcomes and adverse-case commands without
depending on owner-side research/history directories.
