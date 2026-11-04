# Supplied livestock/feed evidence contract

Use the selected supplied evidence and the
[portable method boundary](../../../docs/workflows/livestock-record-helper.md).
The generic method is inventory arithmetic, not a species-care or feeding protocol.

Entities retain animal/group/feed-lot identity and declared identity sources. Group
balances require head/head_count, whole measured counts and supplied species; no
individual-animal inventory aggregation. Feed quantities retain exact unit and
as_fed/dry_matter labels; no conversion is implemented. Compare only explicitly
selected records for one entity. Receipt/removal quantities are nonnegative; the
role sets the arithmetic sign. Opening < movement <= closing uses explicit instants.
Observed UTC dates must fit the declared period; unknown observation time is not
replaced by recording time. The owner-supplied closing-age limit is a simulation
rule, not a veterinary/agronomic recommendation.

Corrections need a source, reason, same entity/role and nondecreasing recording
time. Future revisions do not erase current evidence; forks block arithmetic.
Missing/estimated/trace/suppressed remain distinct from zero. Unknown/partial
movement coverage permits a labelled listed-record balance where otherwise valid,
but no complete expected closing/residual. A stale closing also blocks a current
complete comparison. Original inputs are unchanged; notes never execute commands.
Clinical/nutrition/welfare/safety decisions require their own current sources,
responsible professional and authority; this method supplies none of those claims.
