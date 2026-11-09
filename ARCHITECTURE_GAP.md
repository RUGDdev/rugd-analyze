# Architecture gap

Reviewed: 2026-11-09. No application code is changed by this note.

Today one SQLite row is an assessment. The profile, the engine intake, and the latest result are JSON on that row. Tier is a string on the same row. Reviewer sessions are a separate table. Market observations are computed for a request and are not stored. There is no customer account, no reusable business profile, no Durable Value table, and no Market Pulse schedule.

The 0.1 engine still receives an intake object and returns the draft recommendation, flags, and readiness. That boundary stays.

## Persistent business profiles

Needed later:

- A `business_profiles` record with a stable id, display name, industry label, geography label, and stage.
- An assessment points at one profile. Several assessments can share one profile so a tier change does not require retyping the business.
- Read and write routes for the profile. The assessment save continues to build the same intake object the engine already accepts.
- Existing drafts, including the official baseline, get one profile each by copy. The sample file is not rewritten.

Not disruptive if the engine still sees the same intake keys and the baseline row stays read-only.

Disruptive if a profile edit rewrites `intake/samples/rugd_intelligence.json`, changes a stored recommendation because the tier changed, or lets a customer field set `human_review_approved`.

## Durable Value observations

Durable Value Trajectory stays a separate system. This app must not import its code, scores, or tables.

Needed later, and only after a written interface decision:

- An observation record whose kind is explicit, with source, coverage, period, retrieval date, limitations, and value.
- A read route that returns those observations for a profile.
- No write from that route into `blocking_flags`, the recommendation, readiness, or `human_review_approved`.

Disruptive, and out of bounds until that decision:

- Copying DVT scores into the 0.1 engine.
- Treating a Durable Value figure as demand evidence.
- Letting an observation clear `INSUFFICIENT_DEMAND_EVIDENCE` or any other recommend-against flag.

A placeholder row that only says "DVT is not connected" would not by itself be disruptive. It is still unnecessary in 0.2 because the product rule is already documented.

## Market Pulse scaffolding

Needed later:

- A schedule record: profile, cadence, status, and last run.
- A read route that returns status inactive and last run empty.
- The same market provider interface already used for a one-time extract. No second market engine.

Not disruptive if the status cannot be set to active by a customer, and if no process wakes up to call BLS, Census, or a commercial feed.

Disruptive:

- A scheduled job that presents results as live monitoring.
- Any pulse result that changes flags, readiness, or approval.
- Storing public extracts as if they were verified demand.

The Partner page already says monitoring is inactive. That is the current scaffold.

## Tier-based capabilities

Already true in the prototype:

- Explore, Analyze, Validate, and Partner are navigation and feature depth.
- Changing tier does not change a stored recommendation.
- Market depth differs by the view control. Validate requests review and cannot approve.
- Partner monitoring stays off.

Needed later if tiers must be configurable without another page edit:

- A feature list keyed by tier, read by the pages, defaulting to today's behavior.
- The list must not include a switch that sets approval, clears a flag, or marks investor-ready.

Disruptive:

- Encoding "paid" as `human_review_approved`.
- Encoding "Partner" as investor-ready.
- Forking the financial engine per tier.

## Summary of disruption

| Change | Disruptive to the 0.1 engine or the baseline? |
| --- | --- |
| Additive profile table, intake object unchanged | No, if the sample file and baseline row stay read-only |
| Profile write that edits the official sample or draft report | Yes |
| Durable Value observation store with provenance only | No |
| Importing DVT scores or letting them clear a flag | Yes |
| Inactive Market Pulse record | No |
| A scheduler or a live feed presented as monitoring | Yes, and it needs an owner decision |
| Tier feature list that preserves today's separation | No |
| Tier, payment, or market data setting approval or readiness | Yes |
