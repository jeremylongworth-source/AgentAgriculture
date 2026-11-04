---
name: farm-weather-evidence
description: Review supplied weather evidence for time, location, units, quality and
  uncertainty before a farm work-options brief; use for météo fournie and forecast/observation
  distinctions, without making agronomic thresholds or live-alert assurances.
---

# Supplied weather evidence

Build a short evidence table before explaining weather-dependent work options.
Reuse the task's location, planning interval and language. Establish whether each
item is an observation, forecast, alert or merely an undated statement; a download
time is not an observation or forecast-validity time. Keep missing/trace/estimated
states and original units visible. See [reference checks](references/weather-evidence.md).

Compare location identity and declared coverage; a city/station label is not proof
of field representativeness. Separate issued/observed, valid, retrieved and reviewed
times. Explain amendments and uncertainty without combining incompatible periods
or turning a modelled value into a measurement. Do not infer a crop-treatment or
safe-work threshold from a forecast number.

Output: evidence ID/source/date/location, kind/state/unit, represented interval,
what is missing/stale/conflicting, task implications stated conditionally, and the
next source or field check that would change the result. Preserve official source
meaning when translating labels; identifiers and quantities remain unchanged.

The repository's season helper reuses the existing synthetic weather lab for its
invented normalized inputs. It is not an ECCC XML/CAP parser or live alert consumer.
For real supplied information, review the actual source and applicable current
warnings manually within task authority; the helper's fixture flag is not evidence
that real information was checked. No network retrieval or recurring monitoring is
performed by this skill. Hand usable conditional evidence to work-options planning.
