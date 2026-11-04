# AgentAgriculture ecosystem developer preview

Portable Canadian agriculture skills and workflow compositions for AI agents.
This is a local source release candidate, not yet authorized for publication.
Candidate identity: ecosystem-preview-2026-11-03-rc1. The record engine remains
0.1.0a3; the Python wheel contains that engine, not the portable skill catalog.

## Choose a workflow

| Job | Instructions |
| --- | --- |
| Selected record reconciliation | [Records to Review](skillsets/records-to-review/README.md) |
| Conditional work windows | [Season/work](skillsets/season-work-planning/README.md) |
| Crop observation history | [Crop review](skillsets/crop-production-review/README.md) |
| Animal/group/feed records | [Livestock/feed](skillsets/livestock-record-review/README.md) |
| Supplied procedures and handover | [Resource/team](skillsets/resource-team-coordination/README.md) |
| Mass, lots and declared dispatch | [Harvest/delivery](skillsets/harvest-storage-delivery/README.md) |
| Supplied financial assumptions | [Business scenarios](skillsets/business-stewardship-review/README.md) |

Read the selected composition, its ordered SKILL.md files and required references.
Use [routing guidance](agents/AGENTS.ecosystem.md); a structured route selects
instructions, not authority to execute actions. Helpers other than the record CLI
accept invented inputs only. Do not relabel real records synthetic. Manual skills
can guide appropriately authorized supplied-evidence preparation within their scope.
No automatic host discovery or one-command skill installer is qualified.

## Local setup and checks

CPython3.14.3 Windows x64 is the exercised baseline; other platforms are unqualified.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r requirements-validation.lock
.venv/Scripts/python.exe scripts/validate_ecosystem.py
.venv/Scripts/python.exe -m unittest discover -s tests
.venv/Scripts/python.exe -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/crop-en.json --input examples/ecosystem/crop-en.json
```

Dependency installation uses the package index unless --no-index --find-links
selects a local wheel directory. Keep hash checking. See [record setup](docs/workflows/local-pipeline.md)
for source/installed record CLI use and [release scope](docs/release/initial-preview.md).
The source catalog contains17 skills/seven compositions; finite deterministic
checks do not prove natural-language routing, incremental model benefit, language
conformance, real farm-export completeness or operational Canadian regional support.

No participant study/focus-group program is planned. No agronomic/veterinary
prescription, eligibility/compliance decision, safety clearance, live alert coverage,
field benefit or national operational support is claimed. Keep unknowns and review
requirements visible; appropriate sources/professionals govern corresponding decisions.
No external sending, purchase, production write or account action is authorized.

Read [contribution guidance](CONTRIBUTING.md), [security status](SECURITY.md),
[roadmap](roadmap.md), [MIT](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md).
Do not include private records, credentials or restricted research in source/history.
