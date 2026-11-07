# RUGD Assessment Report

**Engagement:** startup_feasibility  
**Business:** RUGD Intelligence  
**Date:** 2026-10-26  
**Model Version:** 0.1-pilot

## Executive Summary

Draft recommendation: do-not-proceed. Blocking flags: INSUFFICIENT_DEMAND_EVIDENCE. Gap flags: FINANCIAL_INPUTS_NOT_MEASURED, UNEVALUATED_OPERATOR_CAPACITY, UNEVALUATED_REGULATORY_OR_LIABILITY, UNEVALUATED_STEWARDSHIP. Review status: pending. This paragraph is assembled by scoring/rules.py from those flags. It is not a final recommendation and it is not a verified fact (Methodology § Core Principles; Methodology § Output Requirements).

**Recommendation:** do-not-proceed (go / conditional / do-not-proceed)  
*Human approval required before this recommendation is final.*  
**Review status:** pending — draft only, not a final recommendation

## Evidence Base and Assumptions

### Verified Data

- revenue_trailing_12m: not supplied
- current_cash: not supplied
- headcount: not supplied
- evidence_notes: The only sources read for this intake are docs/00-RUGD-Methodology.md, docs/03-Architecture-MVP.md, docs/04-Pilot-Scope.md, and docs/05-Cursor-Rules.md (all Version 1.0, October 2026). Those documents establish the pilot scope and the methodology. They do not state revenue, cash, headcount, prices, costs, or gross margin.
Verified fields are copied from the intake. Missing fields were left empty.

### Assumptions

#### Intake assumptions
Each item keeps the source stored on the intake (Methodology § Core Principles — evidence hierarchy).
- `approved_pilots` = ['RUGD Intelligence', 'Bunny Hive'] (source: verified). docs/04-Pilot-Scope.md, Approved Pilots. This is evidence of project scope. It is not evidence of customer demand.
- `pricing_and_process_viability` = 'open' (source: verified). docs/04-Pilot-Scope.md Success Criteria still calls for a clear statement of whether pricing and process are viable. No price is stated in /docs.
- `methodology_can_recommend_stop` = True (source: verified). docs/00-RUGD-Methodology.md Purpose: the methodology must be capable of recommending against a proposed action when evidence does not support proceeding.
- `initial_capital` = 0 (source: ai_interpretation). No capital amount is stated in /docs. Zero is a placeholder so the engine can run. It is not a measured cash balance. inputs_are_measured is false.
- `monthly_fixed_costs` = 0 (source: ai_interpretation). No cost amount is stated in /docs. Zero is a placeholder, not a measured cost.
- `gross_margin_pct` = 0 (source: ai_interpretation). No gross margin is stated in /docs. Zero means the margin is not established. It is not a measured margin of zero percent in the market.
- `projected_monthly_revenue_base` = 0 (source: ai_interpretation). No revenue forecast is stated in /docs. Pricing viability is still an open pilot question. Zero is a placeholder, not a forecast.
- `downside_revenue_multiplier` = 0.6 (source: ai_interpretation). 0.6 is the default argument on FinancialInputs in engine/financial.py. It is not a measured downside for this venture.
#### Method assumptions used by this run
- Marginal cash flow means monthly cash flow rounded half-even to cents is less than or equal to zero. No other marginal band is approved.
- NEGATIVE_OR_MARGINAL_CASH_FLOW is raised only when both the base case and the downside case meet that test.
- Any flag in the approved recommend-against set drafts do-not-proceed. No per-flag split between do-not-proceed and conditional-only is approved.
- A criterion with no user or verified input stays unevaluated. Unevaluated criteria draft conditional when no recommend-against flag fired, so a silent intake cannot draft go.
- Assumptions with source ai_interpretation are listed. They do not raise or clear recommend-against flags.
- demand_evidence true with source verified, or verified trailing revenue greater than zero, clears insufficient demand. Trailing revenue of zero does not. Trailing revenue is not a market-size score.
- demand_evidence true with source user leaves DEMAND_EVIDENCE_UNVERIFIED. That gap drafts conditional when no recommend-against flag fired. It does not draft do-not-proceed by itself.
- If demand support conflicts with demand_evidence false from a user or verified source, the insufficient-demand flag stays on.
- If operator capacity, regulatory exposure, or extraction has both true and false from user or verified sources, the recommend-against flag stays on.
- When financial_inputs is present and inputs_are_measured is omitted, the inputs are treated as measured. When the field is false, or financial_inputs is absent, the cash-flow criterion is not evaluated.
- months_to_break_even_base is months to recover initial capital at the base cash-flow rate. Break-even revenue is break_even_monthly_revenue.
- The overall feasibility score and the 1–5 dimension scores are not computed.
- No currency unit is defined on the intake. Amounts stay in the unit of the inputs.
- This module cannot record human approval. is_final stays false and human_review_status stays pending.
- The report date is the intake as_of_date or the --date argument. The runner does not read the system clock.
- Intake checks cover the fields this pilot uses. A full JSON Schema draft-2020-12 library is not a project dependency.
- Output files are written only under the project root.
#### AI interpretations (listed, not used to raise or clear recommend-against flags)
- initial_capital = 0. No capital amount is stated in /docs. Zero is a placeholder so the engine can run. It is not a measured cash balance. inputs_are_measured is false.
- monthly_fixed_costs = 0. No cost amount is stated in /docs. Zero is a placeholder, not a measured cost.
- gross_margin_pct = 0. No gross margin is stated in /docs. Zero means the margin is not established. It is not a measured margin of zero percent in the market.
- projected_monthly_revenue_base = 0. No revenue forecast is stated in /docs. Pricing viability is still an open pilot question. Zero is a placeholder, not a forecast.
- downside_revenue_multiplier = 0.6. 0.6 is the default argument on FinancialInputs in engine/financial.py. It is not a measured downside for this venture.

## Financial Summary

* Base monthly contribution: 0.00 (arithmetic on unmeasured inputs; not a cash-flow finding)
* Base monthly cash flow: 0.00 (arithmetic on unmeasured inputs; not a cash-flow finding)
* Downside monthly cash flow: 0.00 (arithmetic on unmeasured inputs; not a cash-flow finding)
* Break-even monthly revenue: not defined (arithmetic on unmeasured inputs; not a cash-flow finding)
* Months to recover initial capital at base cash flow: not defined — rounded base cash flow is not positive (arithmetic on unmeasured inputs; not a finding)
* Engine flags: NEGATIVE_OR_MARGINAL_CASH_FLOW, NO_GROSS_MARGIN
* Overall feasibility score: Not computed. Methodology § Scoring Approach defines the overall feasibility score as a weighted average and says weights are adjustable by engagement type. No weights are approved, and no 1–5 rubric is approved, so none of these dimensions received a score: Market & Demand Reality; Competitive Position & Differentiation; Financial Feasibility & Capital Requirements; Operational Readiness & Capacity; Risk Profile (market, execution, financial, regulatory); Stewardship Indicators (reinvestment capacity, resilience, continuity potential); Implementation Feasibility (for AI or operational improvements).

Definitions from the deterministic engine (Methodology § Output Requirements):
- base_monthly_contribution: projected_monthly_revenue_base × gross_margin_pct
- base_monthly_cash_flow: base_monthly_contribution − monthly_fixed_costs, rounded half-even to cents
- downside_monthly_cash_flow: (projected_monthly_revenue_base × downside_revenue_multiplier × gross_margin_pct) − monthly_fixed_costs, rounded half-even to cents
- break_even_monthly_revenue: monthly_fixed_costs / gross_margin_pct when gross margin is positive; otherwise undefined (Methodology § Output Requirements)
- months_to_break_even_base: initial_capital / unrounded base monthly cash flow when the rounded base cash flow is positive. This is months to recover initial capital at the base cash-flow rate, not a revenue-ramp forecast. Methodology § Output Requirements asks for break-even; that amount is break_even_monthly_revenue.
No currency unit is defined on the intake. Amounts stay in the unit of the inputs.
inputs_are_measured is false, or financial inputs were absent. The figures are arithmetic on the supplied numbers. Scoring did not treat them as a measured base case or downside case.

### Reasonableness check

Secondary industry benchmark. National Restaurant Association, 2025 Restaurant Operations Data Abstract, 2024 full-service medians. This comparison is not a scoring input.
- Labor %: not calculated, so it was not compared with the secondary industry benchmark (NRA median 36.5% of sales).
- Occupancy %: not calculated, so it was not compared with the secondary industry benchmark (NRA median 5.7% of sales).
- Pre-tax margin: not calculated, so it was not compared with the secondary industry benchmark (NRA median 2.8% of sales).

## Startup Capital and Projection

Methodology § Core Principles — deterministic calculations, and human approval before a final recommendation.
Methodology § Investor Readiness Gate — this path does not mark the assessment investor-ready.
human_review_approved: false
is_final: false
investor_ready: false
Construction cost was not supplied. The cost build and the three views were not calculated.

## Key Risks and Mitigations

Assembled from scoring flags by scoring/rules.py. This is not an independent qualitative risk essay.
- **INSUFFICIENT_DEMAND_EVIDENCE** (triggered). Methodology § Scoring Approach — insufficient evidence of demand. No verified trailing revenue above zero and no user or verified demand_evidence value of true. Mitigation: Gather verified demand evidence and record it as verified trailing revenue above zero, or as demand_evidence true with source verified. Re-run before reconsideration.
- **FINANCIAL_INPUTS_NOT_MEASURED** (gap). Methodology § Scoring Approach — negative or marginal cash-flow under base and downside cases. Methodology § Core Principles — verified data and assumptions stay distinct. Unmeasured financial inputs are not a base case or a downside case. Engine flags on these inputs: NEGATIVE_OR_MARGINAL_CASH_FLOW, NO_GROSS_MARGIN. Those flags were not applied as a recommend-against finding because the inputs are not a measured base case and downside case. Base monthly cash flow 0.0. Downside monthly cash flow 0.0. Mitigation: Replace unmeasured financial inputs with measured figures, set inputs_are_measured to true, and re-run.
- **UNEVALUATED_OPERATOR_CAPACITY** (gap). Methodology § Scoring Approach — founder/operator capacity inadequate for the proposed scope. No user or verified value for operator_capacity_adequate. Mitigation: Record operator_capacity_adequate as true or false with source user or verified.
- **UNEVALUATED_REGULATORY_OR_LIABILITY** (gap). Methodology § Scoring Approach — material unresolved regulatory or liability issues. No user or verified value for unresolved_regulatory_or_liability. Mitigation: Record unresolved_regulatory_or_liability as true or false with source user or verified.
- **UNEVALUATED_STEWARDSHIP** (gap). Methodology § Scoring Approach — stewardship indicators show extraction without reinvestment capacity. No user or verified value for extraction_without_reinvestment. Mitigation: Record extraction_without_reinvestment as true or false with source user or verified.

## Stewardship Observations

Methodology § Scoring Approach — stewardship indicators show extraction without reinvestment capacity.

Status: gap.

No user or verified value for extraction_without_reinvestment.

Methodology § Core Principles sets a stewardship orientation for every assessment: long-term enterprise strength over short-term extraction. That principle is the standard being applied. It is not evidence that this venture reinvests.

The intake has no additional stewardship narrative beyond the extraction criterion above.

## Recommended Next Actions

- Human reviewer must approve or reject this draft before it is used as a recommendation. This runner cannot record that approval.
- Stop. Do not proceed on this evidence. Methodology § Output Requirements includes stop as a valid next action.
- Gather verified demand evidence and record it as verified trailing revenue above zero, or as demand_evidence true with source verified. Re-run before reconsideration.
- Replace unmeasured financial inputs with measured figures, set inputs_are_measured to true, and re-run.
- Record operator_capacity_adequate as true or false with source user or verified.
- Record unresolved_regulatory_or_liability as true or false with source user or verified.
- Record extraction_without_reinvestment as true or false with source user or verified.

## Investor Readiness

**Status:** internal (internal / conditional / investor-ready)  
**human_review_approved:** false

- **Human review complete and release explicitly approved:** failed. Investor-ready requires human review complete, release explicitly approved, and human_review_approved true.
- **No recommend-against flags are active:** failed. Active recommend-against flags: INSUFFICIENT_DEMAND_EVIDENCE.
- **Conditional flags have accepted mitigations:** failed. Open conditional flags: FINANCIAL_INPUTS_NOT_MEASURED, UNEVALUATED_OPERATOR_CAPACITY, UNEVALUATED_REGULATORY_OR_LIABILITY, UNEVALUATED_STEWARDSHIP.
- **Base-case cash flow is non-negative:** failed. Base-case cash flow was not supplied as a measured engine result.
- **Downside DSCR meets the engagement minimum:** failed. Downside DSCR was not supplied by the deterministic engine. The engagement minimum is 1.00x.
- **Demand evidence is verified or has a verification plan:** failed. Demand evidence is not verified and has no verification plan.
- **Regulatory or liability issues are resolved or disclosed with mitigations:** failed. Material regulatory or liability issues are not resolved or disclosed with mitigations.
- **Stewardship does not show extraction without reinvestment capacity:** passed. Stewardship indicators do not show extraction without reinvestment capacity.

Release for investors still requires explicit human approval. This report does not grant that approval.

---

*Generated under RUGD Methodology v1.0. All financial figures from deterministic engine. Draft only until a person approves it.*
