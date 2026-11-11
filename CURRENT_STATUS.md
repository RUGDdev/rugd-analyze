# Current status

Updated: 2026-11-09

## Engine

RUGD Business Engine 0.1-pilot is the analytical authority. The unittest suite is 173 tests, all passing.

The official baseline in `intake/samples/rugd_intelligence.json` is unchanged: draft do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, human review pending, `human_review_approved` false, no feasibility score. `reports/output/rugd-intelligence-draft.md` still records that draft. The local app reads the sample and does not overwrite it.

## Repository

Git is on `main`. Commits use a per-command author identity (`RUGD Dev <dev@rugd.local>`). Global Git configuration is unchanged. The latest commit before the README and named-pilot note is `47052a8`. Drafts live in gitignored `data/analyze.sqlite`. The 0.1 sample and `reports/output/rugd-intelligence-draft.md` stay in the repository and are not overwritten by the local app.

## Analyze 0.2

A local browser app runs at http://127.0.0.1:8765 (`python -m app`). Explore and Analyze are operational. Analyze results add Evidence Gaps, Key Assumptions, a Risk Summary, and Suggested Next Research Steps from the engine flags, missing fields, and the demonstration market snapshot. Validate can record a review request, shows a prototype Review Package, and cannot approve. Partner stays a labeled demonstration and adds an inactive Ongoing Intelligence panel. Market Intelligence stays on the synthetic snapshot unless `MARKET_PROVIDER=bls`, `MARKET_CENSUS=acs`, `MARKET_CBP=cbp`, or `MARKET_BEA=bea` is set. Those settings can request a BLS QCEW annual extract, an ACS 5-year population and income extract, a County Business Patterns extract, and a BEA Regional GDP and personal income extract. The market view control shows a limited snapshot on Explore, the full view and a sourced summary on Analyze, and extended metrics on Validate and Partner. A failed or uncovered part falls back to the synthetic snapshot. The figures do not clear a flag. The analyst is the Demonstration Analyst unless `ANALYST_PROVIDER` and the matching API key are set. A missing key or a failed call falls back to the Demonstration Analyst. The analyst cannot change engine results. Educational Durable Value guidance shows the seven methodology dimensions as questions and prompts. The label is “Educational guidance — not a DVT evaluation.” Optional notes are stored apart from the engine result and cannot change a recommendation, a flag, readiness, or a score. A local business profile holds identity, industry, geography, and stage, and more than one draft can share it so a new tier does not require those fields again. The official baseline and named-pilot profiles stay isolated. Profiles do not authenticate a user. Market Pulse is a hypothetical demonstration dashboard with internal and external example cards, a static list of eight review questions, and educational Durable Value pillar labels. Every card says “Hypothetical demonstration — monitoring not active.” No job, connector, or notification is configured. A results page can download a research package as JSON or Markdown, and open a print-friendly Research Brief. The package omits session secrets and does not change the stored assessment. Drafts live in gitignored `data/analyze.sqlite`.

Verified in the browser and over HTTP:

- The baseline results page stays do-not-proceed, internal, and `human_review_approved` false.
- A hypothetical restaurant draft with user-supplied seat, ticket, occupancy, and cost-build inputs runs the startup projection. The draft stays do-not-proceed because demand evidence is unanswered. Sources and uses, base and downside views, and DSCR appear in the result. `investor_ready` stays false.
- By default, Market Intelligence is the synthetic snapshot and states that no Census, BLS, or BEA feed is connected. `MARKET_PROVIDER=bls` can show a BLS QCEW extract. `MARKET_CENSUS=acs` can show ACS 5-year population and median household income. `MARKET_CBP=cbp` can show County Business Patterns. `MARKET_BEA=bea` can show BEA Regional GDP and personal income when `BEA_USER_ID` is set. Explore is the limited snapshot. Partner stays on the synthetic snapshot.
- Validate shows human review pending and a prototype Review Package. A review request changes the copy to “A review has been requested.” and does not approve the file. Partner shows an inactive Ongoing Intelligence demonstration.
- A POST that includes `human_review_approved` returns 403.

Run Analyze submits the same intake form as Save draft, so unsaved entries reach the engine.

The consolidated product architecture was reviewed on 2026-11-09 against this prototype. A file with that title was not in the repository, so the review used the governing 0.2 architecture: four tiers, shared business information, Market Intelligence, a future Market Pulse, and Durable Value kept outside this app. COMPETITIVE_MATRIX.md, ARCHITECTURE_GAP.md, and ZERO_POINT_TWO_PLAN.md record that review. No application code was changed.

## Capabilities by tier

Changing tier does not change a stored recommendation. None of these views grant investor-ready status. Durable Value guidance is educational and is not a DVT evaluation. Market Pulse is a hypothetical demonstration and monitoring is not active.

| Capability | Explore | Analyze | Validate | Partner |
| --- | --- | --- | --- | --- |
| Intake and saved draft | Yes | Yes | Yes | Yes |
| Engine result | When Analyze has been run | When Analyze has been run | When Analyze has been run | When Analyze has been run |
| Research sections | Flag list | Evidence Gaps, Key Assumptions, Risk Summary, and Suggested Next Research Steps | Same as Analyze | Same as Analyze |
| Market Intelligence | Limited snapshot | Full view and Market Research Summary | Full view, summary, and extended metrics | Full view, summary, and extended metrics |
| Review | Cannot approve | Cannot approve | Request only. Review Package is prototype-labeled | Cannot approve |
| Monitoring | Not active | Not active | Not active | Inactive demonstration only |
| Research package and brief | Yes | Yes | Yes | Yes |
| Durable Value guidance | Introductory questions | Considerations next to flags and gaps | Same educational content | Same educational content |
| Business profile | Shared identity, industry, geography, stage, and onboarding path | Shared identity, industry, geography, stage, and onboarding path | Shared identity, industry, geography, stage, and onboarding path | Shared identity, industry, geography, stage, and onboarding path |
| Indicative assessment | After Analyze has been run | After Analyze has been run | After Analyze has been run | After Analyze has been run |
| Read-only share | Owner or reviewer. The shared page cannot edit or approve | Owner or reviewer. The shared page cannot edit or approve | Owner or reviewer. The shared page cannot edit or approve | Owner or reviewer. The shared page cannot edit or approve |
| Advisor Summary | Stored gate, band, components, flags, market snapshot, and Durable Value notes. The download does not change the assessment | Same | Same | Same |
| Evidence checklist | Guidance for demand evidence, missing inputs, and Durable Value notes. A check does not clear a hard gate | Same on the draft and on results | Same on the draft and on results | Same on the draft and on results |
| Scenario comparison | After Analyze, one saved Base and one Downside or Upside case. The comparison does not change the official result | Same | Same | Same |
| Email preferences | Stored on the signed-in account. A chosen notice is written to the server log when SMTP_HOST is unset. The notice does not approve or clear a flag | Same | Same | Same |
| Plain language and assistant | Short explanations sit beside the precise terms. The assistant answers from the current assessment and cannot change it | Same | Same | Same |
| Market Pulse | Hypothetical demonstration | Hypothetical demonstration | Hypothetical demonstration | Hypothetical demonstration |

## Unfinished

Bunny Hive and Small Town Pub are empty named-pilot drafts and have no completed assessments. Only the RUGD Intelligence assessment is the official baseline. Partner monitoring is not running. The Ongoing Intelligence panel is a labeled demonstration. Market Pulse is a hypothetical demonstration with no scheduled job, connector, or notification. The default market view is the synthetic snapshot. The optional BLS QCEW extract is an annual file for seven industries and seven geographies. The optional ACS extract is 2024 5-year population and median household income for those geographies, with overlapping-vintage population change and an income-bracket note as extended metrics. The optional County Business Patterns extract defaults to 2023. A NAICS code missing from that sector table, including Restaurant 722 and Accommodation 721, is requested from the Census CBP API for that code. The optional BEA Regional extract defaults to 2024 and needs `BEA_USER_ID`. It reads current-dollar GDP and personal income for a mapped geography. The year for each extract comes from `MARKET_YEAR`, `ACS_YEAR`, `CBP_YEAR`, or `BEA_YEAR`. None of them is a live feed. Local email and password accounts exist for pilot use. Passwords are stored as scrypt hashes. A new account can log in before its email is verified, and the pages show an unverified banner. Registration sends a 24-hour verification link. Forgot password sends a one-hour reset link. With `SMTP_HOST` unset, the server log prints the message. Neither link changes a role. Self-registration creates a customer account only. The first reviewer comes from the bootstrap environment variables, and later reviewers are created by a signed-in reviewer. An assessment owner or a reviewer can create a 24-hour, 7-day, or until-revoked read-only link. The shared view shows the result, the indicative assessment, market context, and an audit summary. It has no edit control and no approval control. A customer role cannot approve or change its own role. This is not production authentication: there is no OAuth provider and no external identity provider. The session cookie is HttpOnly and SameSite=Lax, and it is marked Secure when `RUGD_ENV=production` or `SECURE_COOKIES=true`. Render files for `app.rugdintelligence.com` are prepared in `DEPLOYMENT.md`. The service stays pilot-grade. No billing, Webflow change, or LongArc/DVT integration. Educational guidance is not that integration. React remains deferred.

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
- Market Intelligence: synthetic snapshot by default; optional BLS QCEW and Census ACS extracts with provenance and fallback
- Official baseline (unchanged): do-not-proceed, INSUFFICIENT_DEMAND_EVIDENCE, investor readiness internal, human_review_approved false
- All 99 tests passing
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

## Progress — 2026-11-08 broader QCEW extract

- The same BLS provider also shows private total annual wages, average annual pay, and establishment size coverage when the annual file includes them. Size code 0 is labeled all size classes combined. A missing extra column is omitted. A suppressed cell stays “Not disclosed.”
- Industries now include Construction (NAICS 23), Manufacturing (31-33), Accommodation (721), and Health care (62), with the original Restaurant, Professional services, and Retail. Geographies are unchanged. The page names the active provider and year. No new environment variable is required.
- An uncovered selection or a failed request still falls back to the labeled synthetic snapshot. The figures do not clear a recommend-against flag.
- The unittest suite is 96 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 Census ACS population and income

- `MARKET_CENSUS=acs` reads American Community Survey 5-year tables B01003 (total population) and B19013 (median household income) from the public data.census.gov extract. `ACS_YEAR` defaults to 2024. No API key is used. Geographies remain the United States, Alabama, and Colbert County, Alabama.
- With BLS also enabled, both extracts appear on Market Intelligence and each provider and year is named. If Census or BLS fails, only that part falls back to the labeled synthetic snapshot.
- The figures are demographic survey estimates. They do not clear a recommend-against flag and they do not set `human_review_approved`.
- The unittest suite is 97 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 more market geographies

- BLS QCEW and Census ACS both cover Tennessee and Hamilton County, Tennessee, in addition to the United States, Alabama, and Colbert County, Alabama. A geography outside that list stays on the labeled synthetic snapshot.
- The Market Intelligence page names the active year for each provider. `MARKET_YEAR` selects the QCEW file and `ACS_YEAR` selects the ACS vintage. Each defaults to 2024. The page says the year is controlled by those environment variables.
- The figures do not clear a recommend-against flag. The unittest suite is 98 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-08 market summary and export

- Market Intelligence has a combined summary of the current BLS and ACS figures, or the synthetic examples when those are what the page shows. Each line includes the source, coverage, and period, and the page names the active provider and year.
- Download market observations (JSON) saves that same view. The file does not include an assessment, a session token, or a passphrase. A synthetic view is labeled synthetic.
- The summary and the file say the figures do not clear a recommend-against flag. The unittest suite is 99 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 multi-source market research view

- `MARKET_CBP=cbp` reads County Business Patterns establishments, employment, and annual payroll from data.census.gov. `CBP_YEAR` defaults to 2023. No API key is used. Restaurant 722 and Accommodation 721 are outside that sector table, so that part falls back and the other sources remain.
- BLS over-the-year percent changes, ACS population change between overlapping 5-year vintages, and the ACS B19001 income-bracket note are extended metrics. Georgia and Fulton County, Georgia, are added to the existing geographies.
- Market Intelligence opens on Explore, a headline snapshot. Analyze adds the full current view and a Market Research Summary that says it is derived from the cited public sources and is not a recommendation. Validate and Partner add the extended metrics. The view control does not change a flag, a recommendation, or `human_review_approved`. Partner monitoring stays off.
- The unittest suite is 100 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 evaluation outputs by tier

- Analyze results add Evidence Gaps, Key Assumptions, a Risk Summary, and Suggested Next Research Steps. The text restates engine flags, missing fields, intake assumptions, and the demonstration market snapshot. Explore keeps the flag list and does not show those four sections. No new score is calculated.
- Validate shows a prototype Review Package: current flags, market context, evidence gaps, and a reviewer-notes placeholder. The customer screen can request review and cannot approve. Approval stays on the prototype reviewer screen.
- Partner adds an Ongoing Intelligence panel with hypothetical trend alerts and hypothetical management actions. The panel says monitoring is inactive. Recurring monitoring is not active.
- The unittest suite is 101 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 research package and brief

- Download Research Package saves a JSON file with the assessment summary, stored engine result, market observations and their provenance, evidence gaps and flags, the analyst explanation, and tier and prototype disclaimers. Download research Markdown saves the same package as Markdown.
- Research Brief is a print-friendly HTML view of that package, with source citations and a limitations section.
- The package does not run the engine, clear a flag, or set `human_review_approved`. Session tokens, passphrases, and cookies are omitted.
- The unittest suite is 102 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 future seams and handoff

- `app/future.py` holds disabled replacement points for production authentication, scoring, deployment, and billing. Settings lists them as disabled. They do not authenticate, score, deploy, or charge. The scoring seam says methodology pending approval.
- Customer pages share the local-prototype warning and the statement that the screen does not grant investor-ready status. `HANDOFF.md` explains how to resume after an owner decision.
- The unittest suite is 104 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 educational Durable Value guidance

- Explore shows introductory questions for the seven methodology dimensions. Analyze shows a practical prompt next to an engine flag or gap when that pillar is related to the flag, and labels the other pillars as not next to a flag. Validate and Partner show the same questions and prompts in their demonstration views.
- An optional note is stored on the assessment in a separate table. It is labeled non-authoritative. Saving it does not change the stored result, the profile, the recommendation, the flags, readiness, or `human_review_approved`. The official baseline refuses the note. No score is calculated. LongArc / DVT is not connected.
- The unittest suite is 106 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 business profile scaffolding

- A business profile stores identity, industry, geography, and stage. A draft can be linked to one profile, and more than one draft can share a customer profile. Starting another assessment copies those four fields and leaves financial entries and evidence on the original draft.
- The official baseline has its own profile and cannot be linked to a draft. Named-pilot and demonstration profiles stay separate from the baseline and from customer profiles. This is local prototype structure. It does not authenticate a user.
- The unittest suite is 108 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 Market Pulse demonstration

- Market Pulse is a demonstration dashboard. Internal examples include revenue trend and labor. External examples include local demographics, competitive developments, operating-cost pressure, and an emerging opportunity. Every card is marked “Hypothetical demonstration — monitoring not active.”
- Eight actionable recommendation questions are a static template. They are questions, not answers. Durable Value pillar names appear as educational labels. The dashboard does not schedule a job, connect a feed, send a notification, clear a flag, or set `human_review_approved`.
- The unittest suite is 110 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 consolidation and handoff

- `ACCEPTANCE.md` and this file use the same Capabilities by tier matrix, including Durable Value guidance and the Market Pulse demonstration. `HANDOFF.md` lists the owner decisions still required before 0.3 work.
- Customer pages, including Market Pulse, carry the local prototype warning. The warning states that the screen does not grant investor-ready status.
- The unittest suite is 110 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 brand sidebar

- Customer pages use a persistent left sidebar with the existing destinations, an active-section highlight, and the RUGD Intelligence wordmark at `app/static/rugd-logo.png`. The palette is the dark blue-gray, aged bronze, warm ivory, soft stone, antique gold, and charcoal slate set.
- Prototype warnings, demonstration labels, financial tables, flags, and provenance stay on the pages. The official baseline is unchanged.
- The unittest suite is 112 tests, all passing. The server is stopped. Authentication remains prototype-grade. The official baseline intake was not edited.

## Progress — 2026-11-09 local accounts

- Register and login use an email and a scrypt password hash in the local `users` table. The session cookie is `rugd_session`, HttpOnly, SameSite=Lax, and the raw token is not stored. The old shared passphrase no longer signs anyone in.
- Approval requires an active reviewer-role session. A customer-role session and a missing session receive 403. A POST that contains `human_review_approved` still returns 403. Approval records the account email and still does not clear a flag, change the recommendation, or grant investor-ready. The official baseline cannot be approved.
- The screens keep the local-prototype warning. Self-service registration on this localhost pilot can create a reviewer account. That is not production role administration.
- The unittest suite is 114 tests, all passing. The server is stopped. The official baseline intake was not edited.

## Progress — 2026-11-09 controlled reviewer creation

- Self-registration creates a customer account. A posted role of reviewer is refused and does not create an account. An existing customer email cannot be promoted.
- The first reviewer is created when `RUGD_BOOTSTRAP_REVIEWER_EMAIL` and `RUGD_BOOTSTRAP_REVIEWER_PASSWORD` are set and no reviewer exists. A signed-in reviewer can create another reviewer at `/reviewer/accounts`. A customer and a signed-out request receive 403.
- Approval still records the signed-in reviewer email. It does not clear a flag, change the recommendation, or grant investor-ready status. The official baseline cannot be approved.
- The unittest suite is 115 tests, all passing. The server is stopped. The official baseline intake was not edited.

## Progress — 2026-11-09 Render production prep

- `app/config.py` reads `RUGD_ENV`, `SECURE_COOKIES`, `SECRET_KEY`, `RUGD_DATABASE`, and `PORT`. Production binds `0.0.0.0` and marks the session cookie Secure, HttpOnly, and SameSite=Lax. Responses send `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`. Local runs stay on 127.0.0.1:8765 with the cookie unmarked for HTTPS.
- `render.yaml`, `Procfile`, `requirements.txt`, and `DEPLOYMENT.md` describe the Render service for `app.rugdintelligence.com`. Secrets stay in the dashboard. The service stays one SQLite instance and stays pilot-grade. Prototype warnings stay. `app/future.py` stays disabled.
- The unittest suite is 118 tests, all passing. The server is stopped. The official baseline intake was not edited.

## Progress — 2026-11-09 BEA and County Business Patterns

- `MARKET_BEA=bea` reads BEA Regional current-dollar GDP (CAGDP2 line 1) and personal income (CAINC1 line 1) for the mapped geographies. `BEA_USER_ID` is required for that request and is not shown on the page. `BEA_YEAR` defaults to 2024.
- County Business Patterns still reads the sector table. A NAICS code missing from that table, including Restaurant 722 and Accommodation 721, is requested from the Census CBP API for that code. No Census API key is sent. A failed part falls back to the synthetic snapshot.
- The Market Intelligence combined summary lists the figures beside BLS and ACS and states that they do not clear a recommend-against flag. The official baseline intake was not edited.
- The unittest suite is 119 tests, all passing. The server is stopped.

## Progress — 2026-11-09 indicative score

- Results and the HTML audit show an indicative 0–100 score. The weights are market validity 40, profitability 35, and Durable Value 25. The rules are in `SCORING.md`.
- Any recommend-against flag forces band Blocked. The engine recommendation, investor readiness, and `human_review_approved` stay as the engine stored them. The feasibility score stays uncalculated.
- The unittest suite is 122 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 LAUS and indicative assessment layout

- `MARKET_LAUS=laus` reads the BLS unemployment rate and labor force for the mapped geographies. The United States row uses the Current Population Survey national series. The figures have full provenance, fall back to the synthetic snapshot, and do not clear a recommend-against flag.
- The results page and HTML audit lead with gate status and band, then Market Validity, Financial Viability, and Stewardship Readiness. Weights are 45, 40, and 15. The overall number is labeled indicative only. A hard gate forces Blocked and the gate recommendation do-not-proceed.
- The unittest suite is 123 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 email verification and password reset

- Registration sends a verification link that expires in 24 hours. An unverified account can log in and sees a banner. Forgot password sends a reset link that expires in one hour and works once. With `SMTP_HOST` unset, the running server writes the message to its log. `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_USE_TLS` send through SMTP when set. `RUGD_PUBLIC_URL` is the link base.
- A verification or reset link does not change a role, approve an assessment, or grant investor-ready status. A posted role on registration or reset is ignored. A customer still cannot approve. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.
- The unittest suite is 125 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 read-only sharing

- An assessment owner or a reviewer can create a read-only link for 24 hours, 7 days, or until it is revoked. The raw token is shown once and is not stored. The shared view shows the engine result, the indicative assessment, stored market context, and an audit summary, with the prototype warning and the indicative-score warning.
- The shared view has no save, analyze, review-request, or approval control. A POST to the share link returns 403 and does not change the assessment. An expired or revoked link does not open the assessment. A customer cannot share an assessment they do not own, including the official baseline.
- The unittest suite is 127 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 startup and existing-business onboarding

- Start a new assessment asks whether this is a startup idea or an existing or expanding business. A startup idea opens the current Explore intake, including the startup cost build. An existing or expanding business opens a shorter intake that skips those startup-only questions and still asks for demand, operator capacity, regulatory and liability, stewardship, and the four monthly engine inputs.
- The choice is stored on the business profile and on the draft. An omitted choice stays on the startup path, so the named-pilot buttons keep the current Explore form. Selecting an existing customer profile uses the path already stored on that profile. A later save cannot change the path or set `human_review_approved`.
- The unittest suite is 129 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. The sample intake was not edited.

## Progress — 2026-11-09 production polish and handoff

- The verification notice, read-only share panel, onboarding choice, and indicative assessment use the same cards, brand colors, and left sidebar as the rest of the prototype. The indicative components use the bronze score bars. The dashboard has a What’s new note for the indicative assessment and read-only sharing.
- `HANDOFF.md` and `ACCEPTANCE.md` record the current capabilities. The remaining owner decisions are production authentication, real market data beyond the public extracts, an approved scoring methodology, billing, investor matchmaking, recurring monitoring and rate limiting, an external analyst provider, LongArc or DVT, the Webflow site, a replacement frontend, official logo artwork, and completed named-pilot intakes or an investor summary.
- The unittest suite is 130 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 advisor summary

- Advisor Summary shows the stored gate status, band, three component scores, key flags, the labeled market snapshot, and Durable Value notes. Download Advisor Package is JSON, and the printable HTML includes the same content plus provenance.
- A read-only share can open the summary and the downloads. The package does not run the engine, does not clear a flag, and does not set `human_review_approved`. A hard gate still forces band Blocked.
- The unittest suite is 132 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 evidence checklist

- The Explore page, the open draft, and the results page show an evidence checklist. The items follow the draft: verified demand evidence, missing monthly financial inputs, missing startup inputs on the startup path, and key Durable Value notes. An active hard gate stays listed.
- Checking an item stores that it was noted. Filling an intake field or saving an educational note shows the matching item as recorded. Neither action clears a recommend-against flag, changes the stored recommendation, or sets `human_review_approved`.
- The unittest suite is 134 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 scenario comparison

- Results can save the current engine result as Base and run one Downside or Upside case from the current inputs and the stored downside multiplier. The two cases are shown side by side with key engine metrics.
- The comparison is stored apart from the official result. It does not change the recommendation, a hard gate, or `human_review_approved`.
- The unittest suite is 136 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-09 notification preferences and pilot handoff

- Settings stores email preferences for assessment shared, review requested, and review recorded. The preference starts off. A notice is sent only to the owner of that assessment, and only when that account opted in. With `SMTP_HOST` unset, the running server writes it to the log. Verification and password-reset messages stay available.
- The notice does not approve an assessment, clear a recommend-against flag, change a role, or set `human_review_approved`. A share notice does not include the raw token.
- `HANDOFF.md` has a Ready for pilot users section. The remaining owner decisions stay open: production authentication, real market data beyond the public extracts, an approved scoring methodology, billing, investor matchmaking, recurring monitoring and rate limiting, an external analyst provider, LongArc or DVT, the Webflow site, a replacement frontend, official logo artwork, and completed named-pilot intakes or an investor summary.
- The unittest suite is 138 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 plain language and conversational assistant

- Dashboard, Explore, the intake, results, the indicative assessment, and Market Intelligence keep the precise terms and add a short plain-language sentence. Learn more holds the tighter definition. The prototype warning and the indicative-score warning stay visible.
- The evidence checklist leads with an everyday sentence. The precise item name and the guidance stay on the page. Checking an item still does not clear a hard gate.
- Results and the open draft include an assistant panel. It reuses `get_analyst()`. With no external provider it is the Demonstration Analyst. Each reply is labeled assistance only. The reply reads the current assessment and does not save, clear a flag, set `human_review_approved`, or grant investor-ready status.
- The unittest suite is 140 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 continue intake

- The assessment overview shows a primary Continue Intake button that opens that draft's Explore intake. After Analyze has been run, the label is Edit Intake, and the note says editing does not clear a recommend-against flag. The unittest suite is 141 tests, all passing.

## Progress — 2026-11-10 sidebar hover explanations

- Each sidebar link shows a one-sentence hover explanation. Demonstration labels stay on the link. The links and their destinations are unchanged. The unittest suite is 142 tests, all passing.

## Progress — 2026-11-10 auth limit, welcome, and assistant starters

- Sidebar links already show a one-sentence hover explanation. Demonstration labels stay visible.
- Sign-in and registration stop after 8 attempts from one network address in 15 minutes. The wait message is plain language, and the rest of the app stays available. Platform-wide rate limiting remains an owner decision.
- A person who has not created a draft sees a dismissible welcome on the dashboard, with a Start a new assessment button. Dismissing it, or creating a draft, hides it for that account.
- The Ask panel has five starter questions and an empty state that says a question can be asked about the current assessment. Every reply still starts with the assistance-only label.
- The unittest suite is 146 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 customer dashboard and section welcomes

- A signed-out dashboard shows Welcome to RUGD Intelligence, Log in, and Register. It does not list assessment data.
- A signed-in dashboard lists only that account's assessments, with stage, last updated, the indicative gate and band when Analyze has been run, and Continue or View results. A status line uses a stored engine flag or a stored DSCR. An account with no assessments is pointed to Start a new assessment.
- Explore, Analyze, Validate, Partner, Market Intelligence, Market Pulse, and Reports each open with a welcome heading and a short explanation. Demonstration labels and the prototype warning stay.
- The unittest suite is 149 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 guided customer path

- The signed-in dashboard and the open assessment show Your next step, with a link to Continue Intake or View Results. The note says completing the step does not clear a hard gate.
- Explore intake, results, and Advisor Summary show an Intake, Analyze, and Review marker. The current stage is highlighted. The marker does not change a flag or a recommendation.
- My Assessments opens with Welcome to RUGD My Assessments. The other section welcomes stay. Assessment cards link to Ask about this assessment. The Ask panel adds “What should I work on next?” The assistance-only label is unchanged.
- The unittest suite is 150 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 results, advisor, and market clarity

- Results open with the stored recommendation, an everyday reading of the gate and band, the key engine figures, and Your next step. The figures still come only from the stored engine result.
- Advisor Summary is a single draft sheet when the file is not approved. A read-only share uses the same Draft label. Neither view can approve the assessment.
- Market Intelligence shows source, period, and limits before the figures. Those figures still cannot clear a flag.
- The Ask panel adds “What does this gate mean?” The assistance-only label is unchanged.
- The unittest suite is 150 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 visual hierarchy

- Signed-in assessment cards put the name, stage, gate and band badges, one stored status line, the last updated time, and one primary button in that order. An empty account still points to Start a new assessment. The signed-out welcome is unchanged.
- The Intake, Analyze, and Review marker reads as a progress bar. The current stage is highlighted. Earlier stages are marked done. The marker still does not change a flag or a recommendation.
- Results separate the recommendation and the gate from the key engine figures. Advisor Summary sits in one shareable page. Spacing and buttons use the existing ivory, charcoal, and bronze colors. Prototype warnings and demonstration labels stay.
- The unittest suite is 150 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 intake suggestions

- Explore intake shows local example suggestions for development stage, products and services, target customers, and competition. The examples narrow when an industry, and a development stage, are already saved. A suggestion fills that field as a user-supplied assumption. It does not invent a number or fill a financial field.
- The demand evidence question is unchanged. Using a suggestion does not clear a recommend-against flag, change demand evidence, or change investor readiness.
- The unittest suite is 154 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 suggestion catalog

- Explore suggestions are loaded from `app/explore_suggestions.json`. A match uses the industry name, aliases, and keywords. An unmatched industry uses the general fallbacks. The chips update when the industry changes on the form.
- The same four fields are covered. A selected example stays a user-supplied assumption. It does not fill a financial field or change a flag, demand evidence, or investor readiness.
- The unittest suite is 155 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 provided suggestion catalog

- `app/explore_suggestions.json` is the provided 0.3 local database. Industries cover restaurant, retail, professional services, health care, construction, manufacturing, and accommodation. Each list is examples only.
- A typed industry matches the name, aliases, and keywords. Search terms stay in the file and are not used for matching. The longest phrase wins. An unmatched industry uses the general fallbacks, including the mature stage. The catalog does not add a stage-specific product list.
- The unittest suite is 155 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 visible intake suggestions

- Explore intake shows an “Examples only.” list under development stage, products and services, target customers, and competition. The chips sit on a white strip with a bronze edge so they stay readable on the ivory page. They refresh from the industry field.
- Selecting a chip fills that field only. It does not change a flag, a recommendation, or investor readiness.
- The unittest suite is 155 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 hover suggestions

- The example lists for development stage, products and services, target customers, and competition stay hidden until that field is hovered or focused. The popover is labeled Examples only. Choosing one fills the field and closes the list.
- The examples still come from the industry name, aliases, and keywords, or the general fallbacks. They do not change a flag, a recommendation, or investor readiness.
- The unittest suite is 156 tests, all passing. The official baseline intake was not edited.

## Progress — 2026-11-10 pilot review

- The signed-in dashboard, results, and Advisor Summary state what the review is for. A hard recommend-against flag keeps do-not-proceed. An indicative number, a market figure, and an assistant reply cannot clear that flag or grant investor-ready status.
- Results name the industry and geography entered on the draft and show the labeled synthetic market examples. Optional public extracts stay on Market Intelligence. They do not clear a flag.
- The assistant can explain how this differs from a business plan. The reply does not change the stored recommendation.
- The unittest suite is 156 tests, all passing. The official baseline intake was not edited. This work has not been published.

## Progress — 2026-11-10 guided patterns

- Public pages for LivePlan and Upmetrics were reviewed for guidance only. No text, image, or code was copied.
- Assessment cards show Intake, Analyze, and Review. Results and Advisor Summary open with three stored facts. Explore intake opens with three numbered steps. Settings states that it stores preferences and does not approve an assessment.
- The unittest suite is 156 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Progress — 2026-11-10 agent workflow

- The intake and results pages show an assistance workflow: Intake guidance, Gap identification, Results explanation, and Next-step recommendation. The current stage and a suggested next action come from the stored file.
- Two questions and one link follow that stage. Every reply still starts with the assistance-only label. The reply does not change a number, a flag, readiness, or approval.
- The unittest suite is 157 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Progress — 2026-11-10 AI Business Adviser

- The intake and results pages open with an AI Business Adviser. It welcomes the reader, names the current assistance stage, and offers three questions for that stage. Every reply stays assistance only.
- One dismissible suggestion appears when demand evidence is missing, monthly fields are blank, or Analyze has not been run. Dismissing it does not clear a flag or change a figure.
- The signed-in dashboard explains which modules are available and which are demonstration only. Key engine figures keep their stored numbers and add a plain-language sentence.
- The unittest suite is 158 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Progress — 2026-11-10 Explore journey

- The home page asks what the customer wants to accomplish. Each choice opens a saved draft for that account. A signed-out visitor is asked to sign in before the workspace is created.
- The AI Business Adviser on that draft asks one question at a time. An answer is stored only after Save this answer. With `ANALYST_PROVIDER` unset, the screen says no external service is connected. A failed provider does not invent a reply.
- Preliminary notes name what was saved, the monthly blanks, and one educational Durable Value theme. No pillar score is calculated. Continue to Analyze opens the monthly fields. The official baseline stays do-not-proceed.
- The unittest suite is 160 tests, all passing. The checkpoint before this work is `ccd9b0e`.

## Progress — 2026-11-10 Interactive Analyze

- A saved draft shows the Explore notes above the monthly fields. A blank monthly field stays missing. An entered zero stays zero. A value that is not a finite number is refused, and the draft and the engine are left unchanged.
- Run Analyze still calls the 0.1 engine. The results page draws cash flow, calculated revenue and contribution, and break-even from that stored result. A separate expense total is not drawn. Running Analyze again redraws the charts from the new result.
- Downside remains one extra engine run. Its chart uses the saved engine metrics. The official recommendation and `INSUFFICIENT_DEMAND_EVIDENCE` stay in place. With `ANALYST_PROVIDER` unset, the reading says no live model was called.
- An owned draft can be changed by that customer or a reviewer. The Explore checkpoint is `49ad52e`.
- The unittest suite is 163 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Progress — 2026-11-11 Customer access checks

- A customer can open and change only a draft that account owns. Another signed-in customer who changes the URL receives “This assessment is not available to this session.” The page does not include the business name or the stored figures. The same check applies to the draft, results, export, report, audit, save, analyze, and scenario routes.
- Explore, Analyze, Market, Reports, and draft export list only records that session may read. A signed-in customer does not see another customer’s draft or an unclaimed draft. A reviewer still can.
- An unclaimed draft keeps its empty owner. It is not assigned and it is not deleted. A signed-in customer cannot open it. Someone who is not signed in still can, if they know the id. The official baseline stays readable and cannot be written, including checklist, guidance, and analyze.
- The unittest suite is 165 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. This work has not been deployed.

## Progress — 2026-11-11 Reports and Action Center

- Reports copies a saved assessment into a new snapshot. A later Analyze run leaves the earlier snapshot in place. Missing figures stay missing. Charts copy stored engine values.
- Action Center saves a follow-up, including one started from a stored flag. Completing an action does not verify evidence, clear a flag, or change the recommendation.
- History lists saved assessments, whether a financial result is stored, report timestamps, and action status.
- An unclaimed draft stays unassigned. A visitor who is not signed in cannot read or change it, and it is left off Explore, Analyze, Market, Reports, and export. A reviewer can open it. Seeded demonstrations stay readable and are read-only for customers and visitors. The official baseline stays read-only.
- The unittest suite is 167 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. This work has not been deployed.

## Progress — 2026-11-11 Interactive financial preview and business plans

- The intake places monthly assumptions beside a financial preview. Changing an assumption calculates through the existing monthly engine and, when the required startup fields are finite, the existing startup projection. The preview is labeled as unsaved. It does not write the assessment, an evidence flag, human review, investor readiness, or a recommendation. Run Analyze still stores the official result.
- A blank monthly field stays missing. A value that is not a finite number is refused and no preview figure is invented. Charts copy the engine numbers for that request.
- A signed-in customer can generate a business plan from a saved assessment, edit the narrative, save it, and export or print it. Financial figures in the plan are a snapshot. A later Analyze run leaves the earlier plan in place. Editing the narrative does not change the stored recommendation or `human_review_approved`.
- The unittest suite is 171 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. This work has not been deployed.

## Progress — 2026-11-11 Financial graphics and business plan sections

- Preview, saved reports, and business plans draw revenue, contribution, cash flow, break-even, and Base versus Downside from stored or just-calculated engine figures. Monthly revenue and fixed costs stay labeled as customer assumptions. No expense total is invented. A blank stays missing. A zero stays zero.
- Startup capital is a doughnut only when the stored sources and uses are complete. An incomplete worksheet says the allocation is not drawn. No cash-flow trend line is drawn, because the monthly engine does not return a period-by-period series.
- A business plan has the sixteen customer sections. An existing or expanding business omits startup capital and startup funding. Narrative text is assembled from the saved assessment. With no live adviser configured, Propose narrative says so and does not change the plan. A configured adviser can only propose text for review. Saving the plan is what stores that text. The copied figures stay with that plan.
- Supported exports are Markdown and the print view. No PDF library is included.
- The unittest suite is 173 tests, all passing. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. This work has not been deployed.
