---
name: farm-work-options
description: Prepare conditional farm work/calendar options from supplied tasks, resource
  availability and reviewed weather evidence; use for seasonal work planning or planifier
  les travaux, while preserving dependencies and unresolved operating conditions.
---

# Conditional work options

Help the operator compare possible work windows and remaining checks. Ask only for
the selected tasks, duration/basis, explicit availability, dependencies and constraints
that affect this plan. Retain who supplied each procedure/criterion and whether it
was reviewed; an asserted criterion is not authenticated operating authority.

Use the weather evidence relevant to this interval, not a national planting calendar.
Load [calendar rules](references/calendar-options.md) when calculating intervals.
Intersect task windows with declared resource calendars and the supplied candidate
condition windows. Keep unknown availability, stale evidence, insufficient duration
and missing procedure context as gaps. A recent observation alone does not establish
future work conditions. Do not invent a precipitation/temperature/soil threshold.

Return candidate intervals with earliest/latest possible starts, resources, predecessor
IDs, evidence references, excluded-window reasons and fallback questions. Show shared-
resource conflicts and dependency obligations. Several alternatives need a joint
selection; never imply that every candidate can run together or is safe to execute.

In the complete source checkout, `scripts/run_farm_workflow.py` can check invented
examples and render EN/FR working briefs. The current helper accepts synthetic-only
input and emits no operational permission. For an authorized real supplied-record
task, the portable procedure remains usable manually; do not relabel real data as
synthetic to use the prototype. If a helper is unavailable, return the constraint/
evidence table and clearly uncomputed intervals instead of inventing checked math.
Keep the farm's own procedure, professional interpretation and actual weather/field
conditions as the operational checks. This skill schedules/sends/controls nothing.
