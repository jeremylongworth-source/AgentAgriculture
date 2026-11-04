# Livestock/feed supplied-basis record helper

Repository-local, explicitly invented input only. Example:

```powershell
.venv/Scripts/python.exe -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/livestock-fr.json --input examples/ecosystem/livestock-fr.json --format markdown
```

The helper preserves original records, observation vs recording times and as-of
corrections/forks. Each selected review references one animal group or feed lot,
opening, listed receipts/removals and closing. Group arithmetic requires whole
head/head_count values and a declared species; individual-animal balance is
unsupported. Feed lines require exact matching units and as_fed/dry_matter basis;
no conversion, moisture inference, ration or nutrition/safety conclusion.

Listed balance = opening + selected receipts - selected removals. Unknown/partial
movement coverage keeps complete expected closing/residual null; missing or
incompatible quantities block arithmetic. Closing freshness uses an explicitly
supplied maximum age, not a domain default; stale closing cannot imply current
stock. A count difference never invents a birth/death/consumption/waste event.
All coverage and identity claims remain supplied and physically unverified.

JSON and escaped EN/FR Markdown retain cutoff/period, identities, IDs, sources,
units/bases, declared coverage, revisions/reasons and remaining questions. Free notes
remain only in canonical JSON; inspect recipient scope before any sharing. CLI
checks context/intent before reading selected data, reads at most 256 KiB, never
modifies inputs or accesses accounts/network/equipment, and writes only stdout.
No global skill installation or changed wheel/private release is implied.

Closing age is reported explicitly in seconds from observation to the review
cutoff, not from a later transcription/correction time. Unknown dates keep age
unknown; future observations retain their signed age plus the future-evidence gap.
Forked parent/child versions are labelled conflicted, retained in full and excluded
from current_ids; no version is picked automatically. Free correction reasons are
preserved literally, not verified causal explanations. The independent invented
fixture exposed a copied future-revision reason inconsistent with its changed
numbers; original evidence is retained and the discrepancy remains a source question.

## Portable source boundary

The historical 2026-10-17 method check used the
[farmOS asset model](https://farmos.org/model/type/asset/) as a modeling reference for
separate animal/group identity, event history and adjustment quantities, and the
[NFACC dairy entry](https://www.nfacc.ca/codes-of-practice/dairy-cattle) to retain
species/source/version scope. These are historical links, not current requirements
rechecked by this packaging change. No provider code/data, farmOS integration,
species-care instructions, feed conversion or clinical authority is included.
The original research increment remains owner-side and unchanged.

Use actual supplied entity/source/unit/basis/time metadata; keep unknowns explicit.
A numeric record balance cannot authenticate physical completeness, explain a
birth/death/feed loss, prescribe a ration or establish welfare. Those are separate
questions requiring appropriate actual evidence and authority.
Follow [source-package setup](../../skillsets/livestock-record-review/SOURCE-PACKAGE.md)
for local dependencies and complete invented examples.
