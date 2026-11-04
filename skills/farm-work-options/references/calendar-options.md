# Calendar option mechanics

The [season composition](../../../skillsets/season-work-planning/README.md) links
the input contract and complete invented EN/FR example. Intersect positive task,
condition and required-resource intervals; merge overlapping calendar intervals so
availability is not counted twice. Duration must fit without silent truncation.
Times carry explicit UTC offsets; calculated intervals use UTC while source time
strings remain retained. A missing resource/calendar or condition criterion is a gap.

Output intervals give alternative earliest/latest starts. Dependencies and shared-
resource overlaps need a joint selection; the helper does not solve a complete or
optimal schedule, authenticate procedures, check alerts or authorize work. The
prototype refuses more than 256 candidates rather than emitting a truncated plan.
Conditional options are mathematical consistency with supplied constraints only.
