# Current status

Updated: 2026-11-07

## Engine

RUGD Business Engine 0.1-pilot is the analytical authority. The unittest suite is 74 tests, all passing.

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

Bunny Hive and Small Town Pub have no completed assessments. Partner monitoring is not running. Market data providers are not connected. No production accounts, billing, production reviewer login, public deployment, Webflow change, or LongArc/DVT integration. React remains deferred. The reviewer sign-in that exists is prototype-grade only.

## Git Checkpoint

- 0.1 baseline committed: `3be9719` — "checkpoint: 0.1 baseline before 0.2 platform" (28 files)
- 0.2 application files committed: `d2a088c` — "add RUGD Analyze 0.2 application files" (13 files)
- Branch: main
- Working tree: clean
- Author used for commits (local only, global config unchanged): RUGD Dev <dev@rugd.local>

## Current Platform Status (0.2)

- Server: stopped (Ctrl+C applied)
- Explore + Analyze: functional against 0.1 engine
- Validate / Partner / Market Intelligence: demonstration only
- Official baseline (unchanged): do-not-proceed, INSUFFICIENT_DEMAND_EVIDENCE, investor readiness internal, human_review_approved false
- All 74 tests passing
- Sample intake and reports/output/rugd-intelligence-draft.md preserved

## Progress — 2026-11-07 demand evidence criteria

- Sufficient demand evidence and the exact conditions that clear `INSUFFICIENT_DEMAND_EVIDENCE` are documented in `DECISIONS.md`. No clearance path was added. The official baseline intake was not edited.
- The Explore → Analyze journey still works over HTTP: create a draft, save it, run the engine, and open results, the report, and the audit. Unanswered demand stays do-not-proceed with `INSUFFICIENT_DEMAND_EVIDENCE`.
- New tests lock a verified `demand_evidence` statement as a clear, a verification plan or non-boolean claim as not a clear, a customer “yes” as `DEMAND_EVIDENCE_UNVERIFIED`, and the existing 403 on `human_review_approved`.
- Server remains stopped.

## Progress — 2026-11-07 verified demand record

- The intake form has a separate verified demand record. It is applied only when the source is exactly `verified` and a rationale is present. A customer yes, a hypothetical demonstration, and an AI interpretation do not clear the flag.
- Results, the report, and the audit show demand status `cleared`, `unverified`, or `uncleared`. A cleared draft stays unapproved and not investor-ready.
- The official baseline still renders do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, and demand status uncleared.
- The unittest suite is 67 tests, all passing. The server was checked and then stopped.

## Progress — 2026-11-07 view clarity and demonstration safety

- Results, the Markdown report, and the JSON audit share one view summary: recommendation, whether `INSUFFICIENT_DEMAND_EVIDENCE` is present, investor readiness, human review pending, and demand provenance (`verified`, `user`, or `placeholder`).
- The analyst is a replaceable Demonstration Analyst. No external AI API is configured. It explains a copy of the engine result and cannot change figures, flags, approval, or readiness.
- Market Intelligence and Partner render one demonstration snapshot. Live feed and monitoring stay off. Examples are labeled synthetic.
- Drafts can be saved, resumed, and listed. A tier change does not change the stored recommendation or flags. Pilot drafts stay separate from the official baseline.
- The unittest suite is 71 tests, all passing. The server is stopped.

## Progress — 2026-11-07 reviewer approval

- A local reviewer action can set `human_review_approved`. Customer posts that include the field still return 403. Validate only requests review. The reviewer screen is labeled as not a customer feature and not production authentication.
- Approval is stored with the assessment id, reviewer identity, and timestamp. It does not clear `INSUFFICIENT_DEMAND_EVIDENCE`, change the recommendation, mark the result final, or grant investor-ready.
- The official baseline cannot be approved. The unittest suite is 73 tests, all passing. The server is stopped.

## Progress — 2026-11-07 reviewer authentication

- Approval now requires a local reviewer session. The shared gate on the approve form is gone. Unauthenticated and customer requests to the approval endpoint still return 403.
- Sign-in is prototype-grade: one source-constant identity and passphrase, a SQLite session, and an HttpOnly cookie. It is not production authentication.
- The reviewer screen shows the authentication state and hides the approve control until sign-in. Validate still only requests review and shows pending.
- The approval audit adds authentication method `local-session`. Approval still does not clear `INSUFFICIENT_DEMAND_EVIDENCE` or grant investor-ready. The official baseline cannot be approved.
- The unittest suite remains 73 tests, all passing. The server is stopped.

## Progress — 2026-11-07 reviewer session lifetime

- A reviewer session lasts 4 hours (`SESSION_LIFETIME_HOURS`). Approval reloads the stored token and returns 403 when the session is missing, signed out, or expired.
- Sign-out is `POST /reviewer/session/sign-out`. It deletes the token and clears the cookie. That cookie cannot approve afterward.
- The reviewer screen shows signed in, signed out, or expired, plus the remaining lifetime while signed in. The approve control stays hidden when the session is missing or expired. Sign out is labeled prototype and not a customer feature. Validate still only requests review and shows pending.
- Approval still does not clear `INSUFFICIENT_DEMAND_EVIDENCE` or grant investor-ready. The official baseline cannot be approved. Customer posts that include `human_review_approved` still return 403.
- Authentication remains prototype-grade. The unittest suite is 74 tests, all passing. The server is stopped.
