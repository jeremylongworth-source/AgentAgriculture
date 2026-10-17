# Local CSV pipeline: current developer/research source path

Read the [initial preview scope, installation, recovery and release gates](../release/initial-preview.md).
The [English](../../examples/records-to-review/en.md) and
[French](../../examples/records-to-review/fr.md) walkthroughs use invented paper/CSV
fixtures and show correction, verification and local adviser-copy preparation.

The current MIT source candidate is 0.1.0a3, based on a2 behavior: `capture`, `reconcile`, `verify` and `handoff`;
one enterprise/period and at most two selected UTF-8 CSVs; explicit authority/mapping,
kg and currency; 16 MiB/source, 32 MiB/10000 logical records combined. Refusal never
accepts a truncated prefix. A successfully saved incomplete package remains incomplete.
Keep originals and explicit corrections separate. Verify returned run snapshots,
inspect exceptions/source-versus-interpretation/ledger, and review the intended
recipient before sharing any separately authorized copy. The tool sends nothing.

Use a fresh source folder/environment for current installation instructions. The
root development environment and old a1 preview may remain for rollback; the tested
a2 candidate has a separate private environment. Revised README/licence metadata
changes final wheel bytes even when runtime modules/schemas match a2. The exact
final public artifact must be identified and checked after licence/rights decisions.

The initial developer/research release does not await participants. The field study
is a separate post-launch project; terms/isolation/access govern actual sessions.
No farmer benefit, actual export completeness, domain/regulatory approval or broad
platform/region support follows from synthetic checks. See
[host responsibilities](host-responsibilities.md) and [security status](../../SECURITY.md).
