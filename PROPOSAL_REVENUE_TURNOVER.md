# Proposal: table turns, service periods, and actual operating days in the seat revenue model

Status: **proposal only. Not authorized. No engine, scoring, or baseline file has been changed.**
Written for owner review. Nothing here takes effect until the owner approves a specific option in writing.

## 1. What the model does today

Source: `engine/financial.py`, `seat_occupancy_revenue` (unchanged from the 0.1-pilot).

```
occupancy = (weekday_occupancy × 5 + weekend_occupancy × 2) / 7
revenue   = round(seats × occupancy × average_ticket × operating_days, 2)
```

Inputs and checks:

| Input | Rule in the engine |
| --- | --- |
| `seats` | whole number, 0 or more |
| `average_ticket` | number, 0 or more |
| `weekday_occupancy`, `weekend_occupancy` | 0 to 1 |
| `operating_days` | more than 0, at most 366. A yearly count |

Consequences, stated plainly:

1. **One cover per occupied seat per operating day.** Occupancy cannot exceed 1, so revenue per day can never exceed `seats × average_ticket`. A restaurant that seats each chair twice (lunch and dinner, or two dinner seatings) cannot be represented by occupancy alone.
2. **There is no turnover input and no service-period input.** The model has no way to say "two seatings", "lunch at one ticket and dinner at another", or "a bar that turns four times an evening".
3. **Weekday and weekend weights are calendar weights.** The 5/7 and 2/7 weights apply to `operating_days` whichever days the business opens. A restaurant open Friday to Sunday still has 5/7 of its days treated as weekdays. A restaurant closed on weekends still has 2/7 treated as weekend days.
4. **Operating days are one yearly number.** The new weekly selector in the intake only suggests that number (days per week × weeks open, divided by 12 for a monthly view). It does not feed the engine except through the `operating_days` value the customer chooses to copy in.
5. **Optional startup lines are filled with coded placeholders when blank** (contingency 0.10, debt share 0.70, interest 0.08, amortization 20 years, downside multiplier 0.6; other optional lines 0). They are not industry standards. The intake help now says so for each field.
6. **The downside multiplier scales occupancy only.** It does not change ticket, seats, or days.

None of these is a defect against the documented model. They are limits. For a table-service restaurant that turns tables, the model will **understate** revenue. For a restaurant open only on days that do not match 5/7 and 2/7, it can misweight weekday and weekend occupancy.

## 2. Interim workaround (no engine change)

A customer can raise `seats` to a daily cover capacity (physical seats × turns). This works arithmetically but has costs:

- `seats` then no longer matches the floor plan, so the seat help and any later seat-based review read wrongly.
- Occupancy then means "share of daily cover capacity", which is a different idea from "share of seats filled".
- It hides the turn assumption inside another field, so a reviewer cannot challenge it.

The intake does not recommend this. It is listed here so the owner knows the workaround exists and why it is weak.

## 3. Options

### Option A. Add one optional `turns_per_day` input (recommended first step)

```
revenue = round(seats × occupancy × turns_per_day × average_ticket × operating_days, 2)
```

- Default when blank: `1.0`. Every existing assessment and the official baseline produce **identical numbers**.
- Validation: number, greater than 0, with a ceiling the owner chooses (for example 6).
- Definition the customer sees: "How many times, on an average operating day, each occupied seat is used by a new party. Occupancy is the share of seat-turns that are filled."
- Labelled a user-supplied assumption, like the other drivers.
- Smallest change. It does not model different tickets for lunch and dinner.

### Option B. Add optional service periods

A short list of periods. Each has `turns`, `occupancy`, and `average_ticket`. Revenue per operating day is the sum of `seats × turns × occupancy × ticket` across periods.

- Represents lunch and dinner with different tickets and fill rates.
- Larger change: a new input shape, new validation, a new intake step, and a new source record per period.
- If periods are present, they replace `average_ticket` and the single occupancy pair. The rule for mixing the two shapes must be decided.

### Option C. Count actual open days by day type

Replace the fixed 5/7 and 2/7 weights with weekday and weekend operating-day counts taken from the weekly selector:

```
revenue = seats × ticket × (weekday_days × weekday_occupancy + weekend_days × weekend_occupancy) × turns
```

- Fixes the misweighting for Friday-to-Sunday and weekdays-only schedules.
- Needs two day counts instead of one `operating_days`. The existing 5/7 and 2/7 behavior stays the default when the counts are absent.

Options can be combined. A reasonable order is A, then C, then B.

## 4. What an approved change would touch

Only after written owner approval, and each in its own commit:

- `engine/financial.py`: new optional parameters with defaults that reproduce today's results. `REVENUE_DRIVERS` and the source records must not change shape for assessments that do not use the new inputs, so the official baseline output stays byte-for-byte the same.
- `app/pages.py`, `app/field_help.py`, `app/guidance.py`: a new field, its help, and the corrected "Model limit" notes.
- `tests/`: golden tests that prove blank new inputs give the old numbers; new tests for the added path.
- `DECISIONS.md` and `CURRENT_STATUS.md`.

An approved change must not touch:

- `scoring/rules.py`, `scoring/industry_benchmarks.py`, scoring weights, recommend-against criteria, or Investor Readiness Gate conditions.
- `intake/samples/rugd_intelligence.json`. The official baseline stays a draft **do-not-proceed** with blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, readiness **internal**, and human review pending.
- The rule that customer-entered values are user-supplied assumptions, not verified data. Turn counts need no special status. A benchmark for turns, if ever loaded, is secondary and cannot clear or raise a recommend-against flag.

## 5. Questions for the owner

1. Approve Option A, B, C, or a combination, or defer all of them?
2. If A: what ceiling for `turns_per_day`?
3. Should customer-facing help keep the interim workaround out of the intake (current behavior)?
4. Should existing saved assessments be re-run when the engine changes? The recommended answer is no. They keep their stored results, and a new run is a new, labelled result.

## 6. What is in the app now

- The intake help for **Seats** states the one-cover-per-seat limit and that a change is proposed.
- The covers worksheet note says table turns are not a separate input.
- The weekly selector suggests `operating_days`. It never changes the field by itself.
- No financial formula changed.
