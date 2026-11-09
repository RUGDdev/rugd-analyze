# Current status

Updated: 2026-11-09

## Engine

RUGD Business Engine 0.1-pilot is the analytical authority. The unittest suite is 136 tests, all passing.

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
