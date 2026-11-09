# Version 0.2 plan

Reviewed: 2026-11-09. This is the smallest remaining set. It does not change the 0.1 engine, the official baseline, scoring weights, recommend-against rules, or the Investor Readiness Gate.

A file titled "Consolidated Product Architecture directive" was not in the repository. The plan uses the architecture already governing 0.2 and the prototype described in CURRENT_STATUS.md.

## Already in 0.2

The local app already has four tiers, saved drafts, the 0.1 engine, evidence labels, a prototype reviewer path, customer refusal of `human_review_approved`, Market Intelligence with BLS, ACS, and County Business Patterns plus a synthetic fallback, tiered market depth, an inactive Partner panel, research sections on Analyze results, a research package, and a print brief. Disabled seams for authentication, scoring, deployment, and billing are in `app/future.py`.

No further 0.2 work is required to demonstrate those boundaries.

## Smallest additions still suitable for 0.2

Do these only if a later session is asked to keep building inside 0.2. They are optional. This planning commit does not implement them.

1. Save the market industry and geography chosen on Market Intelligence onto that draft as user-supplied labels. The research package then cites the saved selection. Do not treat the labels as verified, and do not let them clear a flag.
2. Keep Market Pulse as the inactive Partner panel. If a record is added, its only allowed status is inactive, with no scheduler and no network call.
3. Leave Durable Value unconnected. Do not add a score column or a DVT import.

Each of those items must keep the official sample and `reports/output/rugd-intelligence-draft.md` unchanged, and must leave the baseline at do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, internal, and `human_review_approved` false.

## Must wait for an owner decision

- Production authentication, including accounts, password hashing, OAuth, or an external identity provider.
- An approved scoring methodology, including any feasibility score.
- Real billing, payment processing, and subscription prices.
- DVT integration, including Durable Value scores or shared tables. A future connection needs a documented, versioned interface.
- Scheduled Market Pulse monitoring and any job that calls a market provider on a timer.
- Public deployment, or moving the server off 127.0.0.1.
- BEA or a commercial market, GIS, or benchmark license.
- Accounting actuals from QuickBooks, Xero, or similar.
- Business valuation.
- Pitch decks or other documents that could be read as investor-ready.
- Releasing an investor summary. That still requires the existing gate and an authorized review.
- Investor matchmaking, securities solicitation, brokerage, or capital movement.
- A change to the Webflow site, a React rewrite, the official logo, or completed Bunny Hive and Small Town Pub intakes.

`app/future.py` stays disabled until the matching decision is written in DECISIONS.md.
