# Registry seeds

For the public-source export, [the provenance index](../docs/release/public-provenance.md)
resolves shipped evidence references without distributing the original historical
research or private qualification reports. It explicitly marks carried D/M/S/context
assertions as not independently reproduced. Export changes evidence-path fields only;
identities, historical dates/states, findings, null rights and unvalidated support stay.
The private canonical registries/schema remain untouched; the draft's registry schema
accepts the public index path as a narrow backwards-compatible location alternative.

These YAML files use schema version 1.0.0 and validate offline with
`scripts/validate_contracts.py` in the project environment.

- `sources.yaml`: 38 acquisition routes transcribed from the preserved R04 report
  and evidence attachment. Documentation, metadata and small samples retain their
  separate D/M/S states. Whole-file parsing, operational reliability and entitlement
  are not inferred. No route has O evidence.
- `coverage.yaml`: all ten provinces and three territories, research-mapped only.
  Supported workflow lists are empty and practitioner-review dates unknown.
- `terminology.yaml`: 16 draft English/French terms plus identifier/format rules.
  They are development wording awaiting appropriate language/user review.
- `workflows.yaml`: Records to Review is synthetic-tested for the bounded local
  English/French task, including checked transcription and adviser copies. The
  linked runtime evidence establishes this state; contract validity alone does not.
  The bounded local v0.1 technical preview is qualified under AG-04. Practitioner
  approval, participant evidence, farmer benefit and supported release remain open.

The baseline date describes the original research, not a new retrieval. Unconfirmed
rights, units, missing-value codes, coverage details, owners and operating behaviour
remain null. Recheck changing material at the exact route before implementing a
dependent adapter; do not fetch sources merely to populate unknown fields.

Source-access and workflow-readiness are independent. The source/coverage schemas
currently describe these initial research seeds; extend them with versioned evidence
when a later pack actually qualifies additional states. Preserve canonical reports
and put new findings in separate dated records.

Strategy revision 2026-10-17: an initial developer/research source preview may be
published after its applicable technical/rights/privacy/claims and owner checks,
without participant recruitment. The field study is separately planned after launch.
No registry evidence state changes: these are dated research seeds, all 13
jurisdictions remain operationally unvalidated and no source is O-level. Supplied
raw research snapshots are not part of the initial source draft. See the
[release scope](../docs/release/initial-preview.md).
