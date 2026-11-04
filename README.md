# AgentAgriculture

Portable skills for AI-assisted work with Canadian agriculture records and
observations. AgentAgriculture combines 17 focused skills into seven workflows
for organizing evidence, checking calculations, and preparing local review
packages.

**Developer preview** · Source-based setup · English and French examples

## Choose a workflow

| If you need to… | Start with |
| --- | --- |
| Reconcile purchase and receiving records for one enterprise and period | [Records to Review](skillsets/records-to-review/README.md) |
| Compare conditional work windows from supplied weather and resource evidence | [Season and work planning](skillsets/season-work-planning/README.md) |
| Organize crop observations, corrections, and adviser questions | [Crop observation review](skillsets/crop-production-review/README.md) |
| Review animal and group events and supplied feed-stock records | [Livestock and feed records](skillsets/livestock-record-review/README.md) |
| Turn supplied procedures into task cards and shift handovers | [Resource and team coordination](skillsets/resource-team-coordination/README.md) |
| Check net mass, trace lot movements, and review declared deliveries | [Harvest, storage, and delivery](skillsets/harvest-storage-delivery/README.md) |
| Compare business scenarios using supplied cost and cash assumptions | [Business scenario review](skillsets/business-stewardship-review/README.md) |

## Use a skill from source

1. Open the workflow guide and read its ordered `SKILL.md` files. For a single
   skill, start with the [catalog](router/catalog.json).
2. Give your agent the selected instructions, required references, and task
   context. Use the [routing guide](agents/AGENTS.ecosystem.md) when the task
   spans workflows.
3. Follow the workflow's input and output contract. Preserve original records
   and keep missing evidence, assumptions, and review decisions visible.

This manual setup works from the repository files. Python is needed to run the
helpers and checks. Automatic skill discovery and installation are outside the
verified setup.

## Run a synthetic example

The verified environment is CPython 3.14.3 on Windows x64. From the repository
root, run the crop observation example in PowerShell.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install --require-hashes -r requirements-validation.lock
.venv/Scripts/python.exe -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/crop-en.json --input examples/ecosystem/crop-en.json
```

The pinned dependency install uses a package index by default. An offline
install requires the matching local wheels and `--no-index --find-links`.

For record reconciliation, start with the [English walkthrough](examples/records-to-review/en.md)
or [French walkthrough](examples/records-to-review/fr.md) and use the current
[record CLI instructions](docs/workflows/local-pipeline.md). The record engine is
version `0.1.0a3`. Its Python wheel contains the record CLI and schemas. The
portable skill catalog is distributed as source.

## Preview scope

The record CLI works with selected local records. The other executable workflow
helpers accept invented inputs only. The preview covers evidence preparation
and review. Field efficacy, professional or regulatory decisions, live alerts,
and operational coverage across Canada require separate evidence.

Keep private farm records and credentials out of GitHub. Use invented data
when reporting a problem. See the [security policy](SECURITY.md) for sensitive
reports.

## Project links

- [Roadmap](roadmap.md) and [preview scope](docs/release/initial-preview.md)
- [Contributing and local checks](CONTRIBUTING.md)
- [MIT license](LICENSE) and [third-party notices](THIRD_PARTY_NOTICES.md)
