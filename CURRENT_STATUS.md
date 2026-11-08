# Current status

Updated: 2026-11-08

## Engine

RUGD Business Engine 0.1-pilot is the analytical authority. The unittest suite is 96 tests, all passing.

The official baseline in `intake/samples/rugd_intelligence.json` is unchanged: draft do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, human review pending, `human_review_approved` false, no feasibility score. `reports/output/rugd-intelligence-draft.md` still records that draft. The local app reads the sample and does not overwrite it.

## Repository

Git is on `main`. Commits use a per-command author identity (`RUGD Dev <dev@rugd.local>`). Global Git configuration is unchanged. The latest commit before the README and named-pilot note is `47052a8`. Drafts live in gitignored `data/analyze.sqlite`. The 0.1 sample and `reports/output/rugd-intelligence-draft.md` stay in the repository and are not overwritten by the local app.

## Analyze 0.2

A local browser app runs at http://127.0.0.1:8765 (`python -m app`). Explore and Analyze are operational. Validate can record a review request and cannot approve. Partner stays a labeled demonstration. Market Intelligence stays on the synthetic snapshot unless `MARKET_PROVIDER=bls` is set. That setting can request a BLS QCEW annual extract and falls back to the synthetic snapshot when the selection is not covered or the request fails. The figures do not clear a flag. The analyst is the Demonstration Analyst unless `ANALYST_PROVIDER` and the matching API key are set. A missing key or a failed call falls back to the Demonstration Analyst. The analyst cannot change engine results. Drafts live in gitignored `data/analyze.sqlite`.

Verified in the browser and over HTTP:

- The baseline results page stays do-not-proceed, internal, and `human_review_approved` false.
- A hypothetical restaurant draft with user-supplied seat, ticket, occupancy, and cost-build inputs runs the startup projection. The draft stays do-not-proceed because demand evidence is unanswered. Sources and uses, base and downside views, and DSCR appear in the result. `investor_ready` stays false.
- By default, Market Intelligence is the synthetic snapshot and states that no Census, BLS, or BEA feed is connected. `MARKET_PROVIDER=bls` can show a BLS QCEW extract with provenance. Partner stays on the synthetic snapshot.
- Validate shows human review pending. A review request changes the copy to “A review has been requested.” and does not approve the file.
- A POST that includes `human_review_approved` returns 403.

Run Analyze submits the same intake form as Save draft, so unsaved entries reach the engine.

## Unfinished

Bunny Hive and Small Town Pub are empty named-pilot drafts and have no completed assessments. Only the RUGD Intelligence assessment is the official baseline. Partner monitoring is not running. The default market view is the synthetic snapshot. The optional BLS QCEW extract is an annual file for three industries and three geographies, not a live feed. No production accounts, billing, production reviewer login, public deployment, Webflow change, or LongArc/DVT integration. React remains deferred. The reviewer sign-in that exists is prototype-grade only.

## Git Checkpoint

- 0.1 baseline committed: `3be9719` — "checkpoint: 0.1 baseline before 0.2 platform" (28 files)
- 0.2 application files committed: `d2a088c` — "add RUGD Analyze 0.2 application files" (13 files)
- Branch: main
- Working tree: clean
- Author used for commits (local only, global config unchanged): RUGD Dev <dev@rugd.local>

## Current Platform Status (0.2)

- Server: stopped (Ctrl+C applied)
- Explore + Analyze: functional against 0.1 engine
- Validate / Partner: demonstration only
- Market Intelligence: synthetic snapshot by default; optional BLS QCEW extract with provenance and fallback
- Official baseline (unchanged): do-not-proceed, INSUFFICIENT_DEMAND_EVIDENCE, investor readiness internal, human_review_approved false
- All 96 tests passing
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

## Progress — 2026-11-07 reviewer session audit

- Successful sign-in and sign-out write events on the local reviewer trail, with reviewer identity, timestamp, authentication method, and a short session hash. The raw session token is not shown.
- The assessment audit JSON lists those events beside approvals. Actions are `sign-in`, `sign-out`, and `approve`. The reviewer screen shows the last sign-in, the last sign-out, and the current session status.
- Session events do not change the recommendation, `INSUFFICIENT_DEMAND_EVIDENCE`, or investor readiness. Expired and signed-out sessions still cannot approve. The official baseline stays unapprovable. Customer posts that include `human_review_approved` still return 403.
- Authentication remains prototype-grade. The unittest suite is 75 tests, all passing. The server is stopped.

## Progress — 2026-11-07 HTML audit view

- `/assessments/{id}/audit/html` is a read-only audit page. It shows the recommendation, recommend-against and gap flags, whether `INSUFFICIENT_DEMAND_EVIDENCE` is present, investor readiness, human review status, demand provenance, and reviewer events with timestamps and the short session hash.
- The page has no form and no approval control. Results, the Markdown report, and the reviewer screen link to it. The JSON audit at `/assessments/{id}/audit` is unchanged.
- Opening the HTML page does not write the assessment. The official baseline still renders do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE` present, investor readiness internal, and human review pending.
- Reviewer events on the page are labeled prototype-grade. The unittest suite is 77 tests, all passing. The server is stopped.

## Progress — 2026-11-07 dashboard, intake, and results presentation

- The dashboard lists each saved assessment with Continue and View results. Official baseline is labeled separately from drafts. Each card shows recommendation, whether `INSUFFICIENT_DEMAND_EVIDENCE` is present, investor readiness, and human review. Unrun drafts say not run and pending. None of those cards are styled as approved or investor-ready.
- Startup intake names user-supplied assumptions, verified data, and unmeasured placeholders. Missing required startup and monthly fields stay visible. A saved draft reloads the entered values, including a blank field and an edited worksheet default.
- Results show sources and uses, base and downside, and DSCR from the engine when the startup build calculates. Missing monthly inputs still say Insufficient verified information to calculate. The report and HTML audit links stay on the results page.
- The unittest suite is 80 tests, all passing. The server is stopped. The official baseline intake was not edited.

## Progress — 2026-11-08 analyst, market, and partner demonstration

- The Demonstration Analyst explains sources and uses, base and downside, DSCR, and active flags from the stored engine result. Each explanation is labeled Demonstration Analyst. It does not change figures, flags, approval, or investor readiness.
- Market Intelligence keeps one synthetic snapshot. Industry and geography are demonstration labels. Implications name a saved assessment’s industry and stage and do not add a market fact. Live feed and source dataset stay off.
- Partner states that recurring monitoring is not active. Navigation labels Validate, Partner, and Market Intelligence as demonstration. The dashboard next step names an unfinished item, such as missing demand evidence, and does not clear a flag.
- The unittest suite is 83 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 explore guidance and regression

- The open Explore draft shows “Guidance. Not a decision.” and the same next-step sentence as the dashboard. The note names `INSUFFICIENT_DEMAND_EVIDENCE` when that flag is present, or the next missing required item. Rendering it does not clear a flag or change the recommendation.
- Intake, results, the Markdown report, and the HTML audit use the same labels for recommendation, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness, human review, and demand provenance. A saved draft reloads the entered values. Results and the HTML audit include a Limitations note: this is a prototype, and demonstration data is not real market research.
- A new restaurant draft and the official baseline agree across results, the Markdown report, the HTML audit, and the JSON audit: do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE` present, investor readiness internal, and human review pending. Customer approval still returns 403. The baseline cannot be approved.
- The unittest suite is 85 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Development log

Local 0.2 work on `main`. Reviewer authentication remains prototype-grade. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

- `3be9719` checkpointed the 0.1 engine. `d2a088c` added the local Analyze application.
- `149a2c7` added the verified demand record under the documented clear rule.
- `887d50c` clarified results, kept the Demonstration Analyst from changing engine output, and labeled market and partner demonstrations.
- `521ac79` through `ed5adfa` added reviewer-only approval, prototype sign-in, a 4-hour session, sign-out, and the session audit trail.
- `2031ebf` added the read-only HTML audit page.
- `dcd50d5` listed dashboard history and presented startup sources, uses, and DSCR from the engine.
- `7f36770` explained those engine figures in the Demonstration Analyst and kept Market Intelligence and Partner synthetic.
- `47052a8` showed Explore next-step guidance and aligned intake, results, report, and audit terminology. The suite at that commit is 85 tests.

## Progress — 2026-11-08 README, named pilots, and development log

- `README.md` states the exact `python -m app` command, the local URL, the Ctrl+C shutdown, the unittest command, implemented capabilities, and demonstration or unfinished items. Authentication is described as prototype-grade.
- Bunny Hive and Small Town Pub are created as empty named-pilot drafts. The dashboard and the draft page label them that way. They are not the official baseline, they are not completed assessments, and their names are not read by the scoring engine.
- Only the RUGD Intelligence assessment is labeled the official baseline. Its sample file was not edited.
- The unittest suite is 86 tests, all passing. The server is stopped. Authentication remains prototype-grade.

## Final 0.2 prototype status — 2026-11-08

The local prototype is at a pause point. `ACCEPTANCE.md` maps the original 0.2 browser criteria: the Explore-to-Analyze path, saved drafts, engine results, reports, and the audit are met. Guided assistance is partial because the analyst is a labeled demonstration. Market Intelligence, Validate, and Partner remain demonstration-only. Customer approval still returns 403. The official baseline is unchanged.

Dashboard, Explore, Analyze, Validate, Partner, Market Intelligence, Reports, and the HTML audit share one warning: local prototype, not production security, and the screen does not grant investor-ready status. Authoritative financial numbers on Analyze and results come only from the 0.1 engine. Partner and Market Intelligence still show monitoring and the live feed as false.

Further work on production authentication, real market data, an approved scoring methodology, billing, investor matchmaking, recurring monitoring, an external AI provider, public deployment, LongArc or DVT, the Webflow site, or React requires an owner decision. The unittest suite is 88 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 hypothetical restaurant demonstration

- The seeded Hypothetical Restaurant Startup draft is filled with invented seat, ticket, occupancy, cost-build, and monthly figures. Demand evidence is unanswered, so Analyze stays do-not-proceed with `INSUFFICIENT_DEMAND_EVIDENCE`. The dashboard, intake, and results label it “Hypothetical demonstration — not a real assessment.”
- A second seeded draft supplies verified `demand_evidence` true with a rationale. It is not marked hypothetical, because a hypothetical demonstration does not apply a verified record. The demand flag clears. The draft stays unapproved and not investor-ready.
- `DEMO.md` is the show-the-platform script. The official baseline stays separately labeled and its sample file was not edited.
- The unittest suite is 89 tests, all passing. The server is stopped. Authentication remains prototype-grade.

## Progress — 2026-11-08 report and audit downloads

- Results and the HTML audit offer Download Markdown report and Download JSON audit. Each download returns the same bytes as the existing report or JSON audit view, with a filename that includes the assessment name and date. Opening a download does not rewrite the official 0.1 report files.
- `/assessments/{id}/audit/print` is a print-friendly audit view. Print styling hides navigation and keeps the recommendation, flags, investor readiness, human review status, reviewer events, and the limitations note visible.
- The unittest suite is 90 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 empty states and local export

- Incomplete drafts name the missing startup and monthly fields and say blank fields stay blank. Before Analyze has been run, the results page says so and does not fill missing inputs. A dashboard with no customer drafts says no drafts are saved and that baseline figures are not copied in.
- Export draft as JSON copies one saved assessment. Export all drafts copies every non-baseline assessment into one JSON file. Each export includes the profile, the engine intake, and the latest result when one is stored. Session tokens, passphrases, and cookies are omitted. Export does not run the engine.
- The unittest suite is 92 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 optional external analyst

- `get_analyst()` stays the replacement point. `ANALYST_PROVIDER` may be `claude`, `openai`, or `grok`, using `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `XAI_API_KEY`. `ANALYST_MODEL` is optional. No key is stored in source.
- The provider receives a summary of the current assessment and the engine result, with a system instruction that forbids changing numbers, clearing flags, setting `human_review_approved`, or changing investor readiness. A missing key or a failed call is labeled as a fallback to the Demonstration Analyst. Results and the analyst page name the provider and say the analyst cannot alter authoritative results.
- The unittest suite is 94 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 optional BLS market extract

- Market observations share one interface: source, geographic coverage, industry classification, measurement period, retrieval date, and limitations. The default provider is the synthetic snapshot.
- `MARKET_PROVIDER=bls` requests the BLS Quarterly Census of Employment and Wages annual file. No API key is required. `MARKET_YEAR` defaults to 2024. Restaurant, Professional services, and Retail map to NAICS 722, 54, and 44-45. Geographies are the United States, Alabama, and Colbert County, Alabama. A disclosed private cell shows employment, average weekly wage, and establishments. A suppressed cell is labeled not disclosed.
- An uncovered selection or a failed request is labeled as a fallback to the synthetic snapshot. Partner does not call the public provider. The figures do not clear `INSUFFICIENT_DEMAND_EVIDENCE` or any other flag.
- The unittest suite is 96 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.
