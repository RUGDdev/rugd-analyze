# Benchmarks, revenue worksheet, and feasibility scenarios

Status: local pilot, 2026-11-12. Nothing here changes the 0.1-pilot engine, scoring weights, recommend-against criteria, Investor Readiness Gate, or the official baseline. Nothing here is deployed.

## What exists

| Capability | Route | Code |
| --- | --- | --- |
| Benchmark and planning figures | `/assessments/<id>/benchmarks` | `app/benchmarks.py`, `app/advisory_pages.py` |
| Contextual suggestion cards beside intake fields | intake page and guided save | `app/advisory.py` |
| Proposed restaurant revenue worksheet | `/assessments/<id>/revenue-worksheet` | `app/revenue_worksheet.py` |
| Feasibility improvement scenarios | `/assessments/<id>/improve` | `app/improve.py` |
| Storage for scenarios, decisions, recorded figures, and worksheets | table `advisory_records` | `app/advisory_store.py` |

Everything above is read-only against the official result. None of it calls a paid model, scrapes a site, or runs Analyze.

## Benchmark framework

Every stored figure carries: industry and subsector, service style, geographic applicability, venue size or scale, metric and unit, value or range, source, publication date, retrieval date, methodology and limitations, and confidence and applicability notes. A figure with a missing property says so on the page.

### Figures actually loaded

Twelve National Restaurant Association secondary medians are stored as national figures for restaurants. They are:

- context only (labeled "secondary industry benchmark"),
- national, not specific to the customer's county,
- without a recorded retrieval date (shown as not recorded),
- unable to clear or raise a recommend-against flag, and
- never written into a customer field.

One conflict is listed instead of resolved: the full-service food and beverage cost (30% of sales in one stored figure versus 32.0% in another). The page shows both and does not pick one. No geography-specific, size-specific, or average-check figure is loaded. The page says "No average-check benchmark for <place>" and does not estimate one.

For a non-restaurant industry nothing is loaded. The page says so, says RUGD does not estimate one, and offers the editable assumption-building worksheet.

### Where to look

The page links public, legally accessible sources: BLS Occupational Employment and Wage Statistics, BLS Quarterly Census of Employment and Wages, Census County Business Patterns, Census American Community Survey, National Restaurant Association research, and SBDC advisers. RUGD does not scrape them. Source names appear on the Benchmarks page only, not in field help.

### Recording a figure

The customer can record a figure with its source, publication date, retrieval date, and notes. A recorded figure is a customer-supplied, unverified entry. It is flagged stale when the publication date is more than 730 days old, flagged as conflicting when entries for the same metric differ by more than 15%, and used for suggestions only when it matches the draft's service style. Limit: 40 recorded figures per assessment.

## Contextual suggestion cards

Cards sit beside the intake fields for service style, seats, average ticket, weekday occupancy (turns), construction cost, contribution margin, staffing, pre-opening working capital, debt share, contingency, interest rate, available cash, and venue size. Each card has Use, Adjust, and Dismiss, and a "Source and reasoning" disclosure.

- A card never edits the draft by itself. Use fills the field in the browser. If the customer already entered a value, a confirm dialog asks before replacing it. Autosave then runs as for any typed entry.
- Decisions (accepted, adjusted, dismissed) are stored separately in `advisory_records` and survive reload. A dismissed card can be shown again.
- A card shows a value only when it can be computed from figures the customer recorded. Otherwise it says what is missing or what to record.
- The contribution-margin card is a calculator: the customer enters cost shares and the card computes the margin. NRA medians appear as context only.

## Proposed restaurant revenue worksheet

Separate from the official calculation. The official seat model caps revenue at one cover per occupied seat per day and has no turnover input (see `PROPOSAL_REVENUE_TURNOVER.md`, not authorized).

Inputs: service periods, seats, seat turnover per period, actual operating days (by weekday), utilization, average transaction value, other revenue streams. The worksheet shows each step, the annual total, and a comparison with the official calculation. Covers per seat per day above 1 is flagged as beyond the official cap. The same contribution margin is applied to other streams, which is a stated simplification.

Saving the worksheet changes nothing. "Apply" sets only `projected_monthly_revenue_base` after an explicit confirm, records the previous value, and writes an audit event. Applying does not run Analyze.

## Feasibility improvement scenarios

For a startup draft with startup numbers, the page explains the official issues (evidence flags versus financial findings, using the existing next-action text), shows base and downside coverage against two targets (1.00× readiness default, 1.25× lender oriented), and shows the funding gap, revenue gap, and debt capacity.

Preset alternatives: put in the cash the project needs (solved), lower the build cost, raise the average ticket (solved), lower fixed costs, smaller venue (what-if), longer repayment term (what-if). A solved option shows the arithmetic. A what-if uses a step the customer can change (`step=0.2`). Preset links only fill the form. A custom scenario can change seats, construction, equipment, soft costs, working capital, contingency, debt share, interest, amortization, ticket, occupancy, operating days, fixed costs, margin, downside multiplier, and cash. A smaller venue can scale build costs with seats. Fixed costs do not shrink on their own, and the page says so.

Every scenario lists what changed, what was recalculated, what the customer must verify (for example a written contractor bid), and states "This is a projection from assumptions you would need to verify. It is not approved."

### Approval and persistence

- Saving a scenario stores it in `advisory_records` (limit 12 per assessment). Saved scenarios are shown side by side with the current draft, with a chart and a table.
- Apply to working draft requires the customer to tick "I approve changing these fields in my draft." Without the tick nothing changes. Apply touches only the fields that differ, records from and to values in the scenario, and writes an audit event.
- Apply does not run Analyze, and does not alter flags, scoring, readiness, `human_review_approved`, or the stored result.
- The scenario code never calls the review, analysis, or save-profile paths. Any POST containing `human_review_approved` returns 403 on every route.
- Records are visible only to the assessment's owner or reviewers (and the author for private items). Baseline, hypothetical, and public records are view and compute only.

## Limitations

- Scenarios cover the startup build. Existing-business (monthly engine) scenarios are not implemented.
- No benchmark below the national level is loaded. The NRA medians have no recorded retrieval date.
- Recorded figures are customer-supplied and unverified.
- The revenue worksheet applies one contribution margin to all revenue streams.
- Fixed costs do not scale with venue size automatically.
- New drafts prefill some engine defaults (contingency 0.10, debt share 0.70, interest 0.08, amortization 20, downside multiplier 0.6). A customer-typed value identical to a default cannot be told apart and is listed as a placeholder to confirm.
- The deterministic Adviser does not yet read saved scenarios.

## Next owner pilot

1. Start `python -m app`, sign in, open the restaurant draft, and open Benchmarks. Record any figure the owner has with its source and date.
2. Walk the intake with the suggestion cards. Use, adjust, and dismiss at least one card each. Reload and confirm the choices persist.
3. Fill the revenue worksheet with real service periods and turns. Compare it with the official calculation. Apply only if the owner agrees.
4. Open Improve. Try the cash and build-cost options, save two scenarios, compare them, and apply one only with the approval box ticked.
5. Run Analyze and confirm flags, readiness, and review status did not change because of any scenario.
