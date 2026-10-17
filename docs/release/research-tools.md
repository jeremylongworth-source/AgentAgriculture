# Developer/research utilities included in the source draft

All examples are synthetic or user-selected local files. No background job or live
source connector runs. These helpers do not extend the core's supported farm tasks.

| Utility | Demonstrable capability | Boundary |
| --- | --- | --- |
| `scripts/inspect_csv.py` | Bounded structural inspection, explicit delimiter/read authority, UTF-8/width/quoted-row diagnostics and honest final-count state | No inferred mapping, completeness or semantic correctness; core has its own enforced limits. |
| `scripts/weather_evidence_lab.py` | Pure synthetic time/evidence/lifecycle checks | No live XML/GIS/weather retrieval, forecast competence or alert/safety coverage. |
| `scripts/study_measurement_lab.py` | Exact arithmetic over explicit synthetic effort/attempt data, retaining failures/support/overhead and participant-level denominators | No real participants/findings; no consent/session/data-access authority. The actual field study is separate after launch. |
| `scripts/inventory_preview_rights.py` | Inspect a user-selected hash-pinned local archive's retained wheel metadata/notices | Metadata is evidence, not a rights determination or licence/publication approval. |
| `scripts/validate_contracts.py` | Offline schema, registry and invented fixture checks | Research seed registries remain non-operational, all jurisdictions unvalidated. |
| `scripts/prepare_public_preview.py` | Explicit file/link/hash selection and verification for a local source candidate | No publishing command, legal clearance, secret-free guarantee or release authority. |

Use each command's `--help` where available and inspect the accompanying source and
tests. Some libraries are pure functions exercised by tests rather than end-user CLI
commands. In particular, the weather helper is a lab, not a farm-weather service.
The synthetic study example is `examples/study/synthetic-measurement.json`.

Do not feed real participant material into this tooling or an AI agent. Initial
release demonstrations use invented data; separate agreements and host controls
govern any later authorized real-record workflow. No current source-access route is
upgraded to O, and no source payload or raw research snapshot is shipped here.
