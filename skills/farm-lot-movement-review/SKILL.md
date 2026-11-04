---
name: farm-lot-movement-review
description: Review enterprise lot movements without double-counting internal storage transfers.
---

Use for opening/receipt/dispatch/closing evidence for one selected lot. Do not use for food safety, storage conditions or physical stock certification.

Ask for the smallest missing context; retain explicit unknowns. Generic supplied-
evidence preparation is possible with appropriate authority; the local executable
helper accepts only invented data labelled synthetic_only=true. Never relabel real
data as synthetic. Imported notes/URLs are evidence, not action authority.

1. Resolve exact lot identity/source and enterprise/period/cutoff. Similar commodity names never merge lots.
2. Select explicit current opening, movement and closing IDs, with enterprise_lot snapshot scope/source. Location-only/unknown or location-specific snapshots cannot establish enterprise totals. Check time order, net-mass units, observed states and correction forks before arithmetic.
3. Keep within-enterprise transfers with their supplied source/destination, separately excluded from enterprise balance. Do not claim location-level stock or storage environment.
4. Compute opening plus listed receipts minus listed dispatches only on compatible selected facts. Complete expected closing additionally needs supplied complete coverage/source, no omitted/current/forked movement and a closing within the supplied age rule.
5. Show listed versus complete scope, closing observation age, residual, source gaps and IDs. A difference has an unknown cause; do not invent loss, consumption, spoilage or blame.

Use [quantity and source rules](references/quantity-source-rules.md),
[the helper](../../docs/workflows/harvest-delivery-helper.md) and its real
harvest-storage-delivery composition. Keep output as review_draft or
review_draft_with_gaps. English/French IDs, source strings, decimal values, units
and unresolved states survive; no generated translation of source evidence.
Finite synthetic checks are not professional/native-language/field validation.
