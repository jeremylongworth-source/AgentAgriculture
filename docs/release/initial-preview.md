# Initial developer/research preview: scope and release path

Strategy revision: 2026-10-17. Target: an initial open-source source preview before
participant recruitment. **Current state: MIT local source candidate 0.1.0a3.**
MIT applies to project-owned software/documentation; third-party rights remain
separate. See [licensing scope](licensing.md) and [reporting status](../../SECURITY.md). No public release, push
or new remote is authorized by this document or a passing technical check.

## What can ship without participants

Recommended first artifact: a small source release, rather than the entire current
working repository or private Git history. Include the deterministic Records to
Review package (`capture`, `reconcile`, `verify`, `handoff`), three portable project
skills, English/French templates/walkthroughs, invented contract/record examples,
schemas and regression tests. Include standalone CSV inspection, rights-inventory,
synthetic weather-envelope and study-effort arithmetic tools as developer/research
utilities, with no live feed or real participant processing. Draft source/coverage
registries remain labelled research seeds with no O-level operational source.

The runtime basis is the tested 0.1.0a2 private candidate: one enterprise/period,
at most two selected UTF-8 CSV sources, explicit mappings/authority, literal kg and
one currency, versioned corrections, original bytes, ledgers and portable exports.
Both capture and ingest enforce 16 MiB/source, 32 MiB combined and 10000 logical
records combined. Headers are excluded; quoted newlines are one logical row.
Refusal preserves originals and prior outputs, with no truncated result.

The [public provenance index](public-provenance.md) explains which registry claims
are historical and not independently reproduced in this source tree. Public export
changes three registries' evidence paths and narrowly broadens one registry schema's
report-location constraint; the private canonical data/schema and candidate artifacts
stay unchanged. This public metadata variant has a different schema digest and must
not be presented as the old candidate's exact binary identity. It does not clear
source rights, upgrade D/M/S/O states or invent missing research/qualification evidence.

These capabilities can be completed and honestly released without farmer/adviser
participants. Ordinary bug fixes, source/install/test improvements, synthetic
benchmarks, generic evidence/scenario tools and a justified developer-facing
interface can also progress without a blanket pilot requirement. Do not add every
planned adapter before the first release. No percentage of the whole agricultural
ambition is implied by completing this narrow preview.

## What the first release does not claim

No farmer benefit/time savings, intended-user comprehension, assistive-technology
conformance, actual farm-export completeness, professional approval or operational
national coverage. English/French equality is technically tested; human language
review is not complete. No live weather/alert coverage, private connector, MCP
server, agronomic/veterinary prescription, program eligibility, filing, clinical
or safety clearance, automated message/purchase, production write or multiuser sync.
An invented source/region or a research-mapped jurisdiction is not operational support.

Output is rich and can be much larger than CSV. The saved 10000-record clean case
produced 48596419 bytes from 680742 CSV bytes (71.387x); this is one snapshot,
not a worst-case bound. No output cap, memory/time guarantee or free-disk promise.
The existing CSV field parser limit and input scope rules still apply. Control JSON,
corrections and old snapshot verification have separate resource limits.

## Fresh source installation and checks

Use a fresh private draft checkout/folder with CPython 3.14.3 on Windows x64. Keep
existing qualified environments/artifacts separate. The lock is platform-specific;
Linux/macOS/other Python versions are not yet qualified. Dependency acquisition
needs PyPI or an approved local wheel cache; installed record processing is offline.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-validation.lock
.venv\Scripts\python.exe -m pip install --require-hashes -r requirements-build.lock
.venv\Scripts\python.exe -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir outputs\wheels .
.venv\Scripts\python.exe -m pip install --no-index --no-deps outputs\wheels\agent_agriculture-0.1.0a3-py3-none-any.whl
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe scripts\validate_contracts.py
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Source candidate 0.1.0a3 records approved MIT metadata and an engine version change,
with unchanged arithmetic/input policy/dependencies. Its wheel identity is separate
from the preserved a1/a2 artifacts. Retain the exact source/build/install/test receipts
and final hashes; qualification alone does not authorize publication.
Use the [English task](../../examples/records-to-review/en.md) or
[French task](../../examples/records-to-review/fr.md). Their checked worksheet flags
are assertions in synthetic examples, not software verification of real paper.
The reviewed reference retains raw CAD 665.00, includes CAD 545.00 after explicit
duplicate review, excludes CAD 120.00 and compares 165/163 kg, with missing/uncertain
records still visible. A successful `incomplete` package remains incomplete.

For a fast existing reference:

```powershell
.venv\Scripts\agent-agriculture.exe reconcile --task tests\fixtures\cases\en-baseline\task.json --manifest tests\fixtures\cases\en-baseline\manifest.json --corrections tests\fixtures\cases\en-baseline\corrections.json --output outputs\example
```

Inspect the returned run path, originals, source-versus-interpretation review,
exceptions and totals/ledger. `verify <run-path>` checks local consistency, not
external authenticity or adviser acceptance. `handoff --run <run-path> --output
<fresh-directory>` prepares a local copy and sends nothing. Retry identical inputs
to verify/reuse a snapshot; keep separate corrections and new evidence manifests.
Preserve incomplete/corrupt/pending output for diagnosis, rather than editing it to
force success. Real farm records, secrets and participant information belong outside
this repository and public issues; initial demonstrations use invented records only.

## Applicable public-release checks

| Gate | Needed before public release | Current distinction |
| --- | --- | --- |
| Project licence | Owner-approved exact code/document terms and attribution reflected in source/package | MIT approved for project-owned software/documentation; attribution basis and third-party limits are explicit. |
| Included-source/dependency rights | Review the actual file inventory and retained attribution; apply obligations for what is distributed | Source-only draft vendors no dependency wheels/raw research. A later binary bundle needs its exact dependency/native/notice review. |
| Privacy/security | Review final artifact and any proposed public Git history, selected-input/export behavior and honest host limits | Explicit allowlist excludes study/private/generated/history/raw research. It is not a secret-free or security-audit guarantee. |
| Technical reproducibility | Exact source/build/install/tests and EN/FR path; pinned versions, hashes, known platform/limits | P20 runtime evidence retained; final changed documentation/licence/packaging gets its own artifact checks. |
| Maintenance/reporting | Named responsible maintainer and actual private security-reporting route, contributor/recovery expectations | GitHub private reporting selected for the supplied private-empty repository; activation and triage/notifications remain unverified. |
| Claims/publication | Final scope/version/notes, destination/visibility and explicit authority for reviewed bytes | Local staging and strategy approval do not authorize pushing/publishing. |

Use `scripts/prepare_public_preview.py` to inspect the explicit source inventory or
`--stage-draft outputs/<fresh-name>` to create a **local source candidate**. Its report
always distinguishes technical selection from unresolved owner/publication gates.
`--verify-draft <path>` checks its declared bytes and membership. Do not publish the
source-qualification working copy containing generated outputs/environments.

## Separate post-launch study and later operational scope

The field study is a separate planned subproject after launch, not an initial
release dependency. Its own scoped protocol, terms, willing participants, reviewers,
session isolation and actual observations govern study activity/material release.
No study data, forms or private owner records are included in this initial source
draft. Later field-usefulness/benefit claims need real evidence; high-consequence
or jurisdiction-specific claims also require current applicable domain/regulatory/
community evidence. Neither code publication nor a future study automatically
establishes every operational claim.

## Français

Objectif : un premier aperçu développeur/recherche à code ouvert avec exemples
inventés, avant le recrutement. MIT couvre le logiciel et la documentation appartenant
au projet ; les droits des tiers restent distincts. Aucune publication distante n'est
autorisée ici. Le projet d’étude sera séparé, après le lancement, avec ses
propres accords, participants, réviseurs et environnement qualifié. Il n’est pas un
prérequis à l’aperçu synthétique. Les preuves d’utilité, de sécurité agronomique ou
de conformité ne sont pas supposées. Les limites techniques, droits, confidentialité,
installation reproductible et décisions explicites de publication restent requis.
