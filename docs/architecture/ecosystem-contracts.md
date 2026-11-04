# Ecosystem foundation contract 1.0.0

Repository-local development interface; no installed host/router service or field
support. Three separate JSON Schemas under schemas/ecosystem/v1 preserve the
existing 12 record schemas and record-engine provenance unchanged.

Context declares task, workflow, goal, enterprise, activity jurisdiction, period,
language, intent/consequence and requested action. Unknowns are explicit; country
and region support are not inferred. A structured router cannot discover concealed
natural-language intent: intake must classify the actual request and distinguish
imported content from authority. All fixtures are explicitly synthetic.

Catalog skills resolve real SKILL.md identities. Composition steps resolve declared
dependencies in listed acyclic order and declare outputs, required context and
review requirements. No arbitrary code/tool/command is executed from metadata.
The digest includes manifest data, skill bytes and schemas, not only catalog paths.

Result states distinguish invalid input, missing context, absent capability, blocked
scope and ready for preparation. Ready means a selected instruction sequence, not
completed processing, authenticity, enforced permission or operational approval.
Every routing result retains execution_allowed=false, operational_advice_allowed=false,
permissions_enforced=false and field_use_validated=false. Existing capture/ingest
authority/mapping checks still govern actual selected record reads.

Domain-helper results have their own strict workflow-result schema. They retain
execution_allowed=false, operational_advice_allowed=false and field_use_validated=false;
they do not include the router's permissions_enforced field. Neither helper output
nor a supplied source/approval pointer enforces permissions or verifies authority.

External actions and clinical/agronomic prescriptions/certification are outside
this interface even when consequence is incorrectly labelled informational. A
preparation task near an operational decision can still route to local evidence
preparation while retaining qualified-domain review. Do not block that useful work.
An unimplemented workflow returns no fabricated skill list or operational support.

The CLI reads one explicitly selected JSON control document, at most 256 KiB, with
duplicate keys/nonfinite JSON refused. It writes only stdout/diagnostics; it does
not open farm source paths, contact services, change state or execute a task. This
new control-file bound does not alter the existing CSV/resource policy. JSON keys,
IDs, numbers and route codes are stable across EN/FR; human messages are localized.

Manifest readiness is draft until evidence is recorded. Structural checks, synthetic
scenario/execution evidence, actual paired agent behavior and field review are
different states. Scenario prompts and expected routes support future live-agent
evaluation; deterministic mapping checks alone cannot demonstrate natural-language
discovery, skill benefit or a no-skill baseline. No public/private push is authorized.

An explanation-only route does not require enterprise/location/period or selected-file
authority. It authorizes no record processing; collect that context only for the actual task.
