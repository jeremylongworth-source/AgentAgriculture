# Public provenance index: available evidence and explicit gaps

Authored: 2026-10-17. This index is a public-source reference map, **not a substitute
for the original R02/R04 research or excluded qualification reports**. It does not
grant rights, establish provider payload correctness or imply an operational source.
The [machine-readable index](public-provenance.json) covers all 38 source routes,
13 jurisdiction mappings and the one synthetic record workflow.

## Historical assertions remain historical

The original reports remain owner-side historical artifacts and are not distributed
in this source draft. The index records only their logical labels/digests and concise
authored scope summaries, without private Page IDs or copied report/provider payloads.
R04's D/M/S labels and legacy reference IDs are carried assertions, not independently
reproduced public evidence. R02's context descriptions do not establish current local
farm applicability. All jurisdictions remain operationally unvalidated; no source
is O-level. Missing provider permissions and attribution remain unknown rather than
being replaced with a fabricated clearance statement.

## Narrow public documentation checks

Readable web text was returned for these official documentation pages on 2026-10-17:

- [ECCC city weather documentation](https://eccc-msc.github.io/open-data/msc-data/citypage-weather/readme_citypageweather-datamart_en/).
- [ECCC alert documentation](https://eccc-msc.github.io/open-data/msc-data/alerts/readme_alerts-datamart_en/).
- [Statistics Canada Web Data Service documentation](https://www.statcan.gc.ca/en/developers/wds).

This verifies documentation availability only. It is not a check of live data,
forecast/alert accuracy, geographic matching, farm applicability, redistribution
rights or all 38 routes. Other URLs are explicitly historical listings not rechecked
in this pack. No HTTP status code is claimed from the web-text result, no source
state/date is upgraded and no provider data payload is copied.

## Shipped reproducible engineering methods

The source includes the [pipeline tests](../../tests/test_pipeline.py),
[bilingual/capture/handoff tests](../../tests/test_bundle.py),
[recovery and untrusted-input tests](../../tests/test_preview.py),
[invented reference cases](../../tests/fixtures/README.md) and
[contract checker](../../scripts/validate_contracts.py). Run the commands in the
[initial preview guide](initial-preview.md) for a local observation. Test code is
shipped evidence of the method; it is not an execution receipt or farmer result.
Earlier private qualification logs/artifacts are not reproduced by this index.

## Honest export boundary

The private canonical registries and schemas remain unchanged. The public-draft
export deterministically changes only three registries' evidence-path fields and
one registry schema's report-location constraint. That export schema accepts both
the historical report path and this index path; it adds no O-level or rights claim.
The old schema path remains a backwards-compatibility alternative, not an active
public evidence pointer. Identifiers, historical dates/states, source URLs, findings,
null rights and unvalidated coverage are retained. Public-index summaries do not
resolve the owner review of inherited wording, provenance or terminology.

This metadata-only public schema variant has a different schema digest from the
tested a2 private candidate. Existing candidate artifacts are preserved, not relabelled
as a new build. A final licensed package needs its own exact identity and applicable
checks. Structured-path validation demonstrates that public references resolve in
the selected draft; it cannot turn inaccessible evidence into reproduced findings.
