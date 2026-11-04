# Crop observation review helper

Use the [composition](../../skillsets/crop-production-review/README.md) to preserve
original observations, recording/event times, correction history and missing states.
The executable helper accepts invented JSON only; never relabel real records synthetic.

```powershell
python -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/crop-en.json --input examples/ecosystem/crop-en.json
python -X utf8 scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/crop-fr.json --input examples/ecosystem/crop-fr.json --format markdown
```

Run from the source root using a prepared Python environment. Output is stdout;
no external sending or input modification occurs. Matching context is required.
Comparisons require current observed/measured values and compatible entity, metric,
exact units, method, basis and sampling scope. Missing metadata remains a gap;
different methods are not equivalent because their numbers look similar.

The supplied example's compatible corrected pair yields 13.1 minus 12.4 = 0.7.
Missing-value and different-method pairs remain unresolved. Measured zero differs
from missing. Forked corrections remain conflicts; recording time cannot supply
an unknown observation time. Original versions and reasons remain inspectable.

Canonical JSON retains notes; the readable EN/FR view omits them and escapes supplied
text. Neither format proves source authenticity or safe disclosure. Keep physical
sampling validity, diagnosis, treatment and professional interpretation separate
from arithmetic. Execution, operational advice and field validation remain false.
No provider data, connector, farmOS compatibility or agronomic threshold is included.

Follow [the source-package path](../../skillsets/crop-production-review/SOURCE-PACKAGE.md)
for local setup and dependency boundaries.
