# Confirm the field mapping

Show the original header/value beside its interpretation before confirmation.

| Capture column | Meaning and check |
| --- | --- |
| `source_record_id` | Stable unique row ID; preserve leading zeros. It is distinct from the invoice/reference. |
| `reference` | Original purchase/event reference. Similar text does not prove a duplicate. |
| `date` | Actual calendar date `YYYY-MM-DD`; `09/08/2026` remains unresolved. |
| `enterprise_id` | Actual selected enterprise; a mailing address is insufficient. |
| `supplier` | Source supplier text used for exact pairing; retain it. |
| `quantity`, `unit` | Numeric source quantity and original unit. Only literal `kg` is supported for confirmed comparisons. |
| `amount`, `currency` | Purchase amount and explicit currency; receiving amounts are not more expenses. |
| `paper_reference`, `transcription_note` | Optional source pointers/notes retained as evidence, never instructions. |

English capture uses comma columns and dot decimals. French capture uses semicolon
columns and decimal commas. Dates remain ISO calendar dates in both. No grouping,
exponent notation, currency exchange or guessed package/density conversion occurs.
Blank/`[missing]`, `[suppressed]` and `~number` distinguish missing, source-withheld
and estimated values. Other uncertain text remains unresolved, never zero.

Confirm the declared source coverage and actual row count. Capture flags must
reflect an actual check; they are not evidence of automatic paper verification.
Existing exports with other headers use an explicitly confirmed JSON mapping via
the [pipeline guide](../../docs/workflows/local-pipeline.md), rather than renaming
or overwriting the original file.
