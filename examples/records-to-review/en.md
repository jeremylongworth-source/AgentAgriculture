# Records to Review — complete local walkthrough

This is an invented development task, not farmer evidence. You will compare
synthetic paper worksheets, prepare checked input copies, inspect an unresolved
result, apply one explicit duplicate decision and make a local adviser copy.
You need the installed `0.1.0a1` CLI and the Windows/Python setup in the
[pipeline guide](../../docs/workflows/local-pipeline.md).

## 1. Choose the task and check transcription

Question: which September purchase and receiving records for `ENT-001` need
clarification? Activity jurisdiction is `CA-ON` for synthetic routing only; dates
are 2026-09-01 through 2026-09-30 inclusive, currency CAD, purchase-record basis.
The intended recipient is a local synthetic adviser. This establishes no Ontario
or commodity support.

Read the [purchase worksheet](../manual/en/purchases-paper.md) and
[receiving worksheet](../manual/en/receiving-paper.md). Compare every field against
the supplied [purchase CSV](../manual/en/purchases.csv) and
[receiving CSV](../manual/en/receiving.csv). Notice that A-03 may copy A-02, one
quantity unit is blank, and receiving may disagree. Do not infer their resolution.
For a new task, copy [the blank template](../../templates/en/manual-entry.csv)
and use [intake](../../templates/en/intake.md) and [mapping](../../templates/en/mapping.md).

Only after comparison and confirmation of this synthetic scope, prepare inputs:

```powershell
.venv\Scripts\agent-agriculture.exe capture --purchase examples\manual\en\purchases.csv --receiving examples\manual\en\receiving.csv --output outputs\manual-en-inputs --task-id manual-en --enterprise ENT-001 --jurisdiction CA-ON --start 2026-09-01 --end 2026-09-30 --currency CAD --language en --question "Which records need clarification?" --recipient "Local synthetic adviser" --current-tool "Checked synthetic paper worksheet" --coverage complete --confirm-authority --confirm-mapping --confirm-transcription
```

The confirmation flags record actual checks; software does not read the paper.
`prepared_inputs` means copies and configuration exist locally, not that records
have reconciled. Existing output directories are refused. Choose a new directory
when repeating this preparation, rather than overwriting evidence.

## 2. Inspect the result before a duplicate decision

```powershell
.venv\Scripts\agent-agriculture.exe reconcile --task outputs\manual-en-inputs\task.json --manifest outputs\manual-en-inputs\manifest.json --output outputs\manual-en-runs
```

The command prints the committed run path. Open its `summary.md` and
`record-review.md`. Supplied original purchase amounts sum to CAD 665.00; a
confirmed unique-purchase total is not established because A-02/A-03 need identity
review. Unknown units remain visible. Do not convert that raw sum into profit or
a complete farm total.

## 3. Record one explicit reviewed decision

The supplied [correction file](../manual/en/corrections.json) is a synthetic review
variant confirming A-03 copies A-02. Inspect its exact prior reference, record
version, timestamp, reviewer alias and reason before applying it. This provided
decision is not permission to exclude a similar record in another task.

```powershell
.venv\Scripts\agent-agriculture.exe reconcile --task outputs\manual-en-inputs\task.json --manifest outputs\manual-en-inputs\manifest.json --corrections examples\manual\en\corrections.json --output outputs\manual-en-runs
```

The new run retains both originals, includes CAD 545.00 and excludes CAD 120.00.
The confirmed-unit comparable subset is 165 kg purchased and 163 kg received.
INV-002 has a receiving-minus-purchase difference of -2 kg. The two unknown-unit
records stay unallocated, so the package is still incomplete. Follow the source
rows and calculation references rather than taking these printed expectations as
evidence about another dataset.

## 4. Verify and prepare the local adviser copy

Use the reviewed run path printed in step 3:

```powershell
.venv\Scripts\agent-agriculture.exe verify "<reviewed run path>"
.venv\Scripts\agent-agriculture.exe handoff --run "<reviewed run path>" --output outputs\manual-en-adviser
```

Read the new `index.md`, `summary.md`, `record-review.md`, `calculations.json`,
`exceptions.json` and `handoff.json`. The copy is usable without this tool. It
states the question, checked results, unresolved questions, recipient and omitted
raw evidence. Full normalized JSON, permissions and reviewer history stay with the
farmer. Check free text before sharing; no transmission occurs.

An identical reconciliation reuses its snapshot. A confirmed source/correction
change creates a new one. Keep the verified full snapshot and separate decisions
when leaving the tool. See [export guidance](../../templates/en/export.md).

## Partial records and real paper

For a partial transcription, use `--coverage partial --omission "Selected pages
not supplied"`; use `unknown` when completeness cannot be established. This helper
applies one coverage declaration to both source sets. If their coverage differs,
confirm each source separately in the prepared manifest before reconciliation.
Keep the originals/digests and declared period consistent.

The [partial-export reference](../../tests/fixtures/cases/partial-export/) has an
ambiguous date, missing enterprise and omitted rows. It produces a useful incomplete
package with a supplied amount sum of CAD 445.00, not a full enterprise-period total.
The [exception template](../../templates/en/exceptions.md) records what evidence is
needed. If paper is unavailable or extraction is uncertain, retain a draft or an
unresolved row rather than claiming it was checked. Local CSV editing can be a
later-import fallback; the editor/host must actually save the file.
