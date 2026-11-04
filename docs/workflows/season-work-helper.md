# Season/work helper: supplied conditional windows

Read the [composition](../../skillsets/season-work-planning/README.md), then the
weather-evidence and work-options skills in its declared order. The helper accepts
explicitly invented JSON only. Never mark real farm records synthetic.

```powershell
python -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/season-en.json --input examples/ecosystem/season-en.json
python -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/season-fr.json --input examples/ecosystem/season-fr.json --format markdown
```

Use the Python executable from your prepared environment. These commands print
results; they do not save or send them. Matching task, enterprise, activity
jurisdiction and period are required. Context routing selects instructions, not
permission to perform work. Invalid input is refused rather than silently repaired.

The example returns two conditional candidates: A starts 09:30–10:30 UTC for 60
minutes and ends by 11:30; B starts 10:00 UTC for 90 minutes. They share a crew and
need a joint choice. B's predecessor is not automatically scheduled. C has unknown
resources; afternoon weather is stale under the invented age rule. Missing resource
availability is a gap, not zero capacity. An observation is not a future forecast.
More than 256 candidates is refused rather than truncated.

JSON retains context, source times/units/quality, declared condition intervals,
task constraints, calendars, gaps and review requirements. Markdown renders a
readable EN/FR view; supplied text is escaped. Canonical parsed-input hashes are
not original-file/source authenticity proofs. Outputs keep execution/advice/field
validation false. No alerts, live weather, numeric agronomic threshold, complete
optimal schedule, calendar action or safe-work clearance is provided.

For a selected local source bundle, follow
[the clean-environment path](../../skillsets/season-work-planning/SOURCE-PACKAGE.md).
The broader crop/season implementation history remains in the full checkout; it is
not a dependency of this season-only usage guide.
