# Prepare an adviser copy and retain control

Verify the committed source run, then prepare a new local copy:

```powershell
.venv\Scripts\agent-agriculture.exe verify "<run path>"
.venv\Scripts\agent-agriculture.exe handoff --run "<run path>" --output "<new local adviser folder>"
```

Read `index.md` and `handoff.json` before sharing. The copy includes the summary,
source-versus-interpretation table, calculations and exceptions. Its manifest lists
hashes, intended recipient scope and omissions. It omits raw CSVs, full normalized
JSON, task permissions and reviewer history. Source references remain traceable to
the farmer's full snapshot, but original evidence is not part of this minimal copy.

Inspect free text and scope for unnecessary personal or financial information.
Select additional evidence only when the question needs it and sharing authority
covers it. Do not alter the committed run to remove files; prepare a separate copy.
An adviser can read the Markdown and JSON without this tool. CSV uses ordinary
headers/decimals in the chosen language; machine JSON values and IDs stay stable.

These commands prepare files locally. They do not send, synchronize, file, certify
or obtain adviser approval. A partial package remains partial. Retain the original
snapshot and decision history for correction, export or exit to existing tools.
