# Synthetic reference cases

AG-01 materializes these specifications in `cases/en-baseline/`,
`cases/fr-equivalent/` and `cases/partial-export/`. Each contains task context,
input manifest, original CSV files, explicit synthetic corrections and independent
expected results. `contracts/` contains illustrative contract instances. The
fixture integrity, contract states and arithmetic expectations are checked. AG-02
executes all three cases against those independent expectations, including an
installed-wheel CLI run. These are synthetic pipeline runs, not farmer tasks or
benefit evidence. All identities are invented. Do not add real exports here.

## Case 1: purchases and receiving, English

Scope: synthetic enterprise `ENT-001`, activity jurisdiction `CA-ON` for routing
tests only, 2026-09-01 through 2026-09-30 inclusive, CAD, purchase-record basis
(not payment/tax/profit basis). Quantities are kilograms only when stated.

Source A, purchase records:

| Source row | Reference | Date | Supplier | Quantity | Unit | Amount CAD |
| --- | --- | --- | --- | ---: | --- | ---: |
| A-01 | INV-001 | 2026-09-03 | Synthetic Supply A | 100 | kg | 250.00 |
| A-02 | INV-002 | 2026-09-08 | Synthetic Supply B | 40 | kg | 120.00 |
| A-03 | inv 002 | 2026-09-08 | Synthetic Supply B | 40 | kg | 120.00 |
| A-04 | INV-003 | 2026-09-10 | Synthetic Supply C | 5 | unknown | 75.00 |
| A-05 | INV-004 | 2026-09-12 | Synthetic Supply D | 25 | kg | 100.00 |

Source B, receiving records:

| Source row | Purchase reference | Date | Quantity | Unit |
| --- | --- | --- | ---: | --- |
| B-01 | INV-001 | 2026-09-04 | 100 | kg |
| B-02 | INV-002 | 2026-09-09 | 38 | kg |
| B-03 | INV-003 | 2026-09-11 | 5 | unknown |
| B-04 | INV-004 | 2026-09-13 | 25 | kg |

Independent expectations:

- Raw purchase amounts total CAD 665.00: 250 + 120 + 120 + 75 + 100.
- A-02/A-03 are possible duplicates, not an automatic deletion. Before review,
  display the raw total with the duplicate ambiguity; do not call it a confirmed
  unique-purchase total.
- In an explicit reviewed variant, a synthetic correction confirms A-03 duplicates
  A-02. Retain both original rows and the review decision. Included purchase
  amounts are CAD 545.00: 250 + 120 + 75 + 100; excluded duplicate is CAD 120.00.
  Included plus excluded reconciles to CAD 665.00.
- Confirmed-unit included purchases total 165 kg: 100 + 40 + 25. Corresponding
  receiving quantities total 163 kg: 100 + 38 + 25. INV-002 has receiving minus
  purchase difference -2 kg. Keep its CAD 120.00 purchase amount unchanged.
- The quantity 5 on INV-003 remains unallocated by unit. It must not enter kg
  totals or be dropped from exceptions. Equal bare numbers do not confirm units.
- Receiving rows provide comparison evidence only, no additional monetary expense.
- An input change from B-02 quantity 38 to 39 makes the comparable receiving total
  164 kg and difference -1 kg, with a new input digest/output version. Prior
  evidence and results remain inspectable. Repeating either run creates no extra
  economic activity.

## Case 2: equivalent French task

Use the same enterprise/record identities, scope, dates, currencies and quantities.
Use French labels and accented synthetic supplier names consistently across both
sources. Encode decimal commas explicitly (for example `250,00`) with a declared
semicolon delimiter so a comma does not split an amount into fields. Expected
amounts, exceptions, corrected totals and traceability are identical to Case 1.
This exercises language/format handling; it does not establish Quebec support.

## Case 3: declared partial export

Supply A-01, A-02 and A-04 only, with an export declaration that rows were omitted.
Leave A-02's enterprise unknown and replace its date with `09/08/2026`, without
confirming day/month order. Keep all amounts parseable in CAD.

The received numeric amount sum is CAD 445.00 (250 + 120 + 75), labelled solely as
the sum of supplied amounts, not an enterprise-period reconciled total. A-02's
enterprise and date remain unresolved; A-04's unit remains unresolved. The package
is incomplete and lists the omitted coverage. Do not infer the missing A-05,
deduce a complete September total or create a correction without confirmation.

## Additional integrity variants

`tests/test_contracts.py` defines rejection/unresolved outcomes for legitimate
related events sharing a reference, leading-zero identifiers, absent/suppressed
amounts, mixed currency or period, incompatible mass/volume units and conflicting
corrections. Run it with the project environment using
`python -m unittest discover -s tests`. `tests/test_pipeline.py` adds end-to-end
totals/provenance, source preservation, formula-like export text, corrections,
changed-input recalculation, identical-run reuse and interrupted-write recovery.
Do not add weather, synchronization or account fixtures until selected.

`tests/test_bundle.py` exercises the complete EN/FR checked-transcription path,
localized help/errors/exports, source-versus-interpretation review and minimal
adviser-copy omissions. The invented paper sheets and capture examples are in
`examples/manual/`; they do not replace the independent numeric reference cases.
An unresolved duplicate group does not hide checked quantities from other exact
pairs: before duplicate review the base comparable subset is 125 kg / 125 kg.
The complete unique-purchase monetary total remains unestablished in that variant.
