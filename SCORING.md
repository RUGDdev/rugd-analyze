# Indicative score

This score is a reading aid. It is not the feasibility score in `scoring/rules.py`. That score stays uncalculated, and `overall_feasibility_score` stays null. `app/future.py` `scoring_methodology()` stays disabled and still returns “Not calculated — methodology pending approval.”

The indicative score does not clear a recommend-against flag, change the engine recommendation, change investor readiness, or set `human_review_approved`.

The label on the results page and the HTML audit is:

> Indicative Score — combines market validity, profitability, and Durable Value principles. Does not override engine flags or human review.

## Weights

The overall score is an integer from 0 to 100:

```text
(market × 40 + profitability × 35 + durable × 25) // 100
```

The division drops the remainder. Each component is an integer from 0 to 100.

| Component | Weight |
| --- | --- |
| Market Validity | 40 |
| Profitability and Financial Viability | 35 |
| Durable Value and Stewardship | 25 |

## Bands

A recommend-against flag forces **Blocked** even when the number is high. The flags are the engine set:

- `INSUFFICIENT_DEMAND_EVIDENCE`
- `NEGATIVE_OR_MARGINAL_CASH_FLOW`
- `INADEQUATE_OPERATOR_CAPACITY`
- `UNRESOLVED_REGULATORY_OR_LIABILITY`
- `EXTRACTION_WITHOUT_REINVESTMENT`

When none of those flags is active:

| Band | Overall score |
| --- | --- |
| Strong | 75 to 100 |
| Conditional | 50 to 74 |
| Weak | 0 to 49 |

The engine recommendation is shown as the engine stored it. Blocked does not rewrite that field. In the 0.1 engine, any of these flags already drafts do-not-proceed.

## Market Validity

| Input | Points | Rule |
| --- | --- | --- |
| Demand evidence | 0, 25, or 60 | `demand.status` `cleared` is 60. `unverified` is 25. Anything else is 0. |
| Market size or growth | 0 or 20 | 20 only when a stored public observation has a positive numeric value and its measure names employment, population, establishment, GDP, personal income, payroll, or wage. Synthetic examples and “Not disclosed” add nothing. The results page does not fetch a market provider. |
| Competitive density | 0 | Not measured. This portion stays 0. |

A market figure cannot clear a flag. If a hard gate is active, the band stays Blocked.

## Profitability and Financial Viability

Figures come from the engine `financial` object and, for DSCR, from `projection.views.downside.dscr`. Missing figures are not invented.

| Input | Points | Rule |
| --- | --- | --- |
| Contribution | 0, 10, or 30 | Positive base monthly contribution is 30. Zero is 10. Negative or missing is 0. |
| Cash-flow coverage | 0, 10, or 30 | Positive base monthly cash flow is 30. Zero is 10. Negative or missing is 0. `NEGATIVE_OR_MARGINAL_CASH_FLOW` forces this portion to 0. |
| Downside DSCR | 0, 5, 10, or 20 | At least 1 is 20. Zero up to but not including 1 is 5. Negative is 0. Missing is 10, because the ratio was not calculated. This 1.0 line is only for the indicative score. It is not the Investor Readiness Gate. |
| Capital recovery | 0, 6, 12, or 20 | `months_to_break_even_base` of 24 or less is 20. 60 or less is 12. Longer is 6. Missing, or base cash flow that is not positive, is 0. |

## Durable Value and Stewardship

Notes are the optional educational notes already stored on the assessment. They are not a DVT evaluation.

| Input | Points | Rule |
| --- | --- | --- |
| Floor | 70 | Missing notes stay at 70. They are not a heavy penalty. |
| Pillar notes | 4 each | One stored note on a known pillar adds 4. Seven pillars can add 28. The component is capped at 100, so the highest note total in this rule is 98. |

A blank note does not count. The official baseline does not store these notes.

## What the score does not do

- It does not change `recommendation`, `blocking_flags`, `readiness_status`, `is_final`, or `human_review_approved`.
- It does not make a result investor-ready. Investor-ready still requires every existing gate plus authorized human review.
- It does not call the market provider and it does not call the analyst.
- It is computed when the results page or the HTML audit is rendered. It is not written into the stored engine result.
