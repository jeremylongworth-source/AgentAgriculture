# Supplied-assumption business helper

Run `.venv/Scripts/python.exe scripts/run_farm_workflow.py --context tests/fixtures/ecosystem/context/business-fr.json --input examples/ecosystem/business-fr.json --format markdown`.

Synthetic-only bounded JSON, one enterprise/period/currency and explicit cutoff.
Each amount retains ID/version/source/time/period/accounting basis/state. Numeric
actual_as_reported, budgeted, assumed and estimated values may be used as supplied
assumptions, without verifying reality. Missing/suppressed are null; state/value
contradictions and duplicate IDs are refused. Currency/basis/period mismatch,
unknown metadata, missing sources or future recording excludes a row. No conversion.

Known compatible revenue and variable-cost subtotals yield listed contribution.
All selected rows must be compatible and declared coverage/source complete for
complete_selected_contribution. This is still before excluded fixed/shared/owner/
financing/tax items: net_profit is always null. Missing every row yields null known
subtotal; an explicit compatible zero is zero. No total across scenario alternatives.

Cash receipts/payments are separate cash-basis rows and yield selected net movement;
whole_farm_cash_flow_established stays false. Sensitivity uses each explicit source-
linked/versioned revenue/variable-cost multiplier, recording cutoff and held
assumption, only for a complete
compatible selected scenario. It is conditional arithmetic, not a forecast/ranking.
EN/FR local handover retains originals/figures/states/gaps and sends nothing. Free
notes stay inert in JSON. No actual figures/source authenticity, profit/cash-flow,
tax/eligibility, investment/lending or practitioner/field validation is established.
No ledger correction, FX, valuation, shared-cost allocation or later stewardship
requirement branch is silently added. Prior workflows remain independent.

## Portable source boundary

The historical 2026-10-17 method increment used
[FCC's business-plan guide](https://www.fcc-fac.ca/en/knowledge/10-steps-to-a-solid-business-plan)
to distinguish broad financial statements/cash-flow planning from this limited
selected-assumption arithmetic. This link is historical, not a current source check
in this packaging work. No page/template content, finance product or actual prices
are imported. The original owner-side research note remains unchanged.

Contribution = compatible selected revenue minus selected variable costs, before
excluded fixed/shared/owner/finance/tax categories. Cash = selected cash receipts
minus payments, not contribution or whole-farm cash flow. Sensitivity uses stated
multipliers and held assumptions, not probabilities or advice. Retain exact source,
version, currency/basis/period/time/state and unknowns. Actual professional financial
decisions require appropriate context and review outside this helper's claims.
See [source-package setup](../../skillsets/business-stewardship-review/SOURCE-PACKAGE.md).
