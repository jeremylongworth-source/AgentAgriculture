# Synthetic mass, lot and declared-delivery helper

Run `.venv/Scripts/python.exe scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/harvest-fr.json --input examples/ecosystem/harvest-fr.json --format markdown`.

Strict bounded JSON; synthetic_only=true. One enterprise/period, explicit lot IDs,
as-of corrections and same exact kg/g/lb gross/tare units. No unit conversion or
count-to-mass. Measured zero remains numeric; missing/estimated/trace/suppressed or
gross below tare yield no confirmed net. Origins and unsupported readings remain.

Each lot review selects opening/movements/closing and explicitly declares
enterprise_lot snapshot scope/source. Location-only, unknown, unsourced or location-
specific opening/closing snapshots cannot establish enterprise balance; even listed
lot arithmetic is withheld. The invented aggregate snapshots have no location ID.
This is a scope claim, never proof that actual sources cover all locations. Missing/incompatible selected
records conservatively suppress even listed arithmetic, including an unresolved
internal-move quantity; raw facts remain. Opening + receipts - dispatches excludes
declared within-enterprise transfers. It does not calculate location stock.
Unselected relevant current movements/forks, partial/unknown coverage or stale
closing suppress complete expected closing/difference. Coverage is a supplied
claim. Age uses observation time and an explicit supplied maximum, never a farm
threshold. No loss or cause is inferred from a residual.

Commitments are exact supplied ID/version declarations, not parsed contracts.
Current selected same-lot/unit/destination dispatch records within the due date
support listed arithmetic. Unknown/partial coverage, missing coverage source or
reused dispatch allocation suppress complete dispatch-minus-declared difference.
All originals and parsed-input hashes remain; free notes stay inert in JSON.
Readable EN/FR retains raw values/states/source/time/correction/selection and
review gaps. Human review and separately scoped recipient disclosure are required.
Local handover sends nothing. Source authenticity, physical/measurement accuracy,
food/grade/shelf-life, actual delivery/acceptance and legal fulfilment stay unverified.
No real data, integration, shipping or publication. Prior workflows stay independent.

## Portable source boundary

The historical 2026-10-17 method increment used
[farmOS inventory](https://farmos.org/model/logic/inventory/) as a design reference
for distinct asset/unit inventories and
[CFIA net quantity](https://inspection.canada.ca/en/food-labels/labelling/industry/net-quantity)
to distinguish arithmetic from physical/label verification. These links are not
current rules rechecked by this packaging change. No farmOS documentation/code,
provider payload or regulatory threshold/rounding rule is imported. An unknown
opening is never silently zero. The original research increment remains unchanged.
Source authenticity, representative sampling, compliant labels, food safety and
legal fulfilment remain separate evidence questions, not results of this helper.
See [source-package setup](../../skillsets/harvest-storage-delivery/SOURCE-PACKAGE.md).
