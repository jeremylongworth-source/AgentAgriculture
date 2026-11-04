# Records to Review composition

[Local source-package setup](SOURCE-PACKAGE.md) provides the complete selected
composition/engine path without requiring a preinstalled CLI.

Use this composition for one enterprise/period and up to two selected purchase/
receiving CSV sets or checked manual transcriptions. It composes the existing three
skills; it adds no new accounting, agronomy or clinical interpretation.

1. Read [intake](../../skills/farm-task-intake/SKILL.md). Establish the question,
   activity location, period, units/currency/basis, selected originals, omissions,
   language and intended local recipient scope. Capture confirmations are operator
   assertions, not proof that software read paper or enforced OS permission.
2. Read [reconciliation](../../skills/farm-record-reconciliation/SKILL.md). Run the
   checked record utility, inspect original/corrected evidence, ledger and exceptions,
   and verify the immutable run. Keep partial/incomplete status and unknowns.
3. Read [adviser package](../../skills/farm-adviser-package/SKILL.md). Verify before
   preparing the minimal local copy; inspect retained free text and omissions. No
   email/submission/transmission or adviser acceptance is performed.

[The manifest](manifest.json) declares order, dependency and output contracts.
[Foundation rules](../../docs/architecture/ecosystem-contracts.md) explain routing,
states and limits. Follow the existing [English](../../examples/records-to-review/en.md)
or [French](../../examples/records-to-review/fr.md) source/installed walkthrough.
Project-local routing example:

```powershell
.venv/Scripts/python.exe scripts/route_farm_task.py --context tests/fixtures/ecosystem/context/records-review-en.json
```

The router selects instructions; it does not execute this sequence. An operator or
agent follows the skills with actual selected-file authority. Existing code owns
arithmetic and exports. No broad schema rewrite, account or source connection.
