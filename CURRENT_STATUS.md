# Current status

Updated: 2026-11-07

## Engine

RUGD Business Engine 0.1-pilot is the analytical authority. The unittest suite is 62 tests, all passing.

The official baseline in `intake/samples/rugd_intelligence.json` is unchanged: draft do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, human review pending, `human_review_approved` false, no feasibility score. `reports/output/rugd-intelligence-draft.md` still records that draft. The local app reads the sample and does not overwrite it.

## Repository

Git was initialized on `main`. The 0.1 files are staged. The checkpoint commit is blocked until a person sets their Git author identity. This session did not change Git configuration. The 0.2 application files are untracked and uncommitted.

## Analyze 0.2

A local browser app runs at http://127.0.0.1:8765 (`python -m app`). Explore and Analyze are operational. Validate can record a review request and cannot approve. Partner and Market Intelligence are labeled demonstrations. Drafts live in gitignored `data/analyze.sqlite`.

Verified in the browser and over HTTP:

- The baseline results page stays do-not-proceed, internal, and `human_review_approved` false.
- A hypothetical restaurant draft with user-supplied seat, ticket, occupancy, and cost-build inputs runs the startup projection. The draft stays do-not-proceed because demand evidence is unanswered. Sources and uses, base and downside views, and DSCR appear in the result. `investor_ready` stays false.
- Market Intelligence is labeled hypothetical and states that no Census, BLS, or BEA feed is connected.
- Validate shows human review pending. A review request changes the copy to “A review has been requested.” and does not approve the file.
- A POST that includes `human_review_approved` returns 403.

Run Analyze submits the same intake form as Save draft, so unsaved entries reach the engine.

## Unfinished

Bunny Hive and Small Town Pub have no completed assessments. Partner monitoring is not running. Market data providers are not connected. No production accounts, billing, reviewer login, public deployment, Webflow change, or LongArc/DVT integration. React remains deferred.
