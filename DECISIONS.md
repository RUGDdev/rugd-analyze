# Decisions

## 2026-11-07 — RUGD Analyze 0.2 stays inside this repository

RUGD Analyze 0.2 is a local browser application in `c:\Projects\RUGD`. It is not a new repository. Longarc_Platform and the Webflow site stay untouched.

## 2026-11-07 — One platform, four service tiers

Explore, Analyze, Validate, and Partner are service levels in one application. Service tier, draft recommendation, evidence status, human-review approval, and investor readiness are separate fields. Changing tier does not change a recommendation.

## 2026-11-07 — Python shell around the 0.1 engine

The customer application calls the existing Python engine. It does not rewrite calculations in another language. The first interface is local HTML served by Python on 127.0.0.1. React is deferred until this journey is stable. Drafts are stored in local SQLite under `data/`, which is gitignored.

## 2026-11-07 — No customer approval control

Version 0.2 has no accounts and no payment processing. The Validate screen can record a review request. It cannot set `human_review_approved`. Investor summaries remain behind the existing gate.

## 2026-11-07 — Market intelligence is labeled hypothetical

Version 0.2 does not call Census, BLS, BEA, or any paid data API. Market pages state that their examples are hypothetical.

## 2026-11-07 — Git author identity was not set

`git init` created this repository and the 0.1 files were staged. The checkpoint commit did not run because Git has no author name or email. Git configuration was not changed.

## Decision: Git Checkpoint Completed

- Date: 2026-11-07
- Status: Accepted
- Context: Root commit of 0.1 engine + follow-on commit of 0.2 application files required before further platform work.
- Decision: Commits made with temporary author identity (`-c user.name` / `-c user.email`) so global Git config remains unchanged.
- Consequence: Clean baseline now exists on `main`. Future sessions can resume from `d2a088c`.
- Update 2026-11-08: Later commits on `main` use the same temporary author identity. Resume from `CURRENT_STATUS.md`. The latest commit before the README and named-pilot note is `47052a8`. Reviewer authentication remains prototype-grade. The unittest count is recorded in `CURRENT_STATUS.md` (86 tests, all passing).

## Decision: Demand Evidence Remains the Hard Gate

- Status: Active / Unchanged
- The flag `INSUFFICIENT_DEMAND_EVIDENCE` continues to block any recommendation other than do-not-proceed and keeps investor readiness at `internal`.
- No new scoring, fabricated evidence, or AI-generated clearance is permitted.
- Clearance criteria will be defined in a subsequent decision before any implementation that can change the flag.

## Decision: Sufficient Demand Evidence

- Date: 2026-11-07
- Status: Accepted as documentation of the 0.1 rules. No new clearance path is implemented.
- Authority: Methodology § Core Principles (evidence hierarchy), Methodology § Scoring Approach (insufficient evidence of demand), and `scoring/rules.py` `_assess_demand` as committed in `d2a088c`. This decision does not change scoring weights, recommend-against criteria, or Investor Readiness Gate conditions.
- Context: `INSUFFICIENT_DEMAND_EVIDENCE` is an approved recommend-against flag. While it is active, the draft recommendation is do-not-proceed and investor readiness is internal. The official RUGD Intelligence intake does not meet any clear condition below, and this decision does not edit that intake.

### What counts as sufficient demand evidence

Sufficient demand evidence is verified support with no conflicting denial. It is one of these records, and neither may be accompanied by a conflicting false:

1. `verified_data.revenue_trailing_12m` is a finite number strictly greater than zero. Zero does not qualify. Null and a missing value do not qualify. The number is trailing revenue evidence, not a market-size score.
2. An assumption whose key matches `demand_evidence` after trimming whitespace and ignoring case, whose value is the boolean `true`, and whose source is exactly `verified`.

The match is exact on that key. `approved_pilots`, `demand_notes`, `evidence_notes`, `hypothetical_demonstration`, projected revenue, seat × occupancy × average ticket, a startup cost build, and a secondary industry benchmark are not demand evidence.

A conflicting denial is any assumption with that same key, source `user` or `verified`, and boolean value `false`. One denial keeps the flag on even when verified trailing revenue or a verified `true` is also present. Source `ai_interpretation` is not a denial and is not support.

### Exact conditions that clear `INSUFFICIENT_DEMAND_EVIDENCE`

The criterion status is `clear`, and the blocking flag is not raised, only when both are true:

- No conflicting denial, as defined above.
- At least one of the two sufficient-evidence records is present.

Non-boolean values on `user` or `verified` assumptions are ignored. The string `"true"`, the number `1`, and a customer form token are not the boolean `true`. A negative, non-numeric, or boolean `revenue_trailing_12m` is invalid intake, not a clear.

### Records that leave the flag in place

The blocking flag stays on when verified support is absent and there is no boolean `true` from source `user` or `verified`. That includes silence, a null or zero trailing revenue, an unanswered customer question, an AI interpretation of demand, and a verified statement on a different key.

A boolean `true` from source `user` only does not clear insufficient demand. The engine leaves gap flag `DEMAND_EVIDENCE_UNVERIFIED`. That gap can draft conditional when no recommend-against flag fired. It does not draft go by itself, and it is not verified evidence.

A verification plan does not clear this flag. Methodology § Investor Readiness Gate can accept verified demand or a verification plan at the readiness gate. In the 0.1 engine, `demand_verification_plan` true with source `user` or `verified` can satisfy only that readiness condition. It does not remove `INSUFFICIENT_DEMAND_EVIDENCE`. While the blocking flag is active, readiness stays internal.

### What clearance does not do

Clearing this flag does not set `human_review_approved`, does not mark the result final, does not compute a feasibility score, and does not produce investor-ready. Any other active recommend-against flag still drafts do-not-proceed and keeps readiness internal. The customer application stores a yes or no as source `user` and keeps `verified_data.revenue_trailing_12m` null, so a customer control cannot meet the clear conditions. No later change may clear the official baseline unless the intake itself contains one of the two sufficient-evidence records and an authorized review accepts it.

## Decision: Verified Demand Record in the Application

- Date: 2026-11-07
- Status: Accepted
- The customer yes/no question remains source `user`. It cannot clear `INSUFFICIENT_DEMAND_EVIDENCE`.
- A separate form, “Verified demand record,” may supply `revenue_trailing_12m` and boolean `demand_evidence` only when `verified_record_source` is exactly `verified` and a rationale is present. The 0.1 engine then applies the documented rule.
- A hypothetical demonstration does not apply that record. An AI interpretation is not an accepted source.
- The application still passes human review as pending. Clearing the flag does not set `human_review_approved` and does not mark the result investor-ready.
- The official baseline intake stays unchanged and read-only.

## Decision: Reviewer-only approval

- Date: 2026-11-07
- Status: Accepted
- Customer endpoints and the Validate screen cannot set `human_review_approved`. A customer POST that includes that field still returns 403.
- Approval is a separate local action at `/reviewer/assessments/{id}/approve`. It requires the local prototype gate. That gate is not production authentication and is not a customer control.
- The audit records the assessment identifier, reviewer identity, and timestamp. The prototype identity may be the placeholder “Local prototype reviewer.”
- Approval does not clear `INSUFFICIENT_DEMAND_EVIDENCE` or any other recommend-against flag, does not change the draft recommendation, does not mark the result final, and does not write an investor summary.
- Investor readiness still uses the existing gate. Approval alone cannot make the status investor-ready while any gate condition fails. The official baseline cannot be approved and stays `human_review_approved` false.

## Decision: Prototype reviewer authentication

- Date: 2026-11-07
- Status: Accepted for the local prototype only
- The shared gate value is no longer enough to approve. Approval at `/reviewer/assessments/{id}/approve` requires a reviewer session. A request with no session, a customer request, and any POST that includes `human_review_approved` still return 403.
- Sign-in is `POST /reviewer/session`. The only accepted identity is `Local prototype reviewer`. The passphrase is the source constant `local-prototype-reviewer`. A matching sign-in stores a random token in the local SQLite table `reviewer_sessions` and sets an `HttpOnly` cookie named `rugd_reviewer` (`Path=/`, `SameSite=Lax`). The role is `reviewer` and the authentication method is `local-session`.
- The reviewer screen shows that authentication state. The approve control is absent until the session exists. The customer Validate screen still only offers “Request review” and shows pending.
- A successful approval audit includes the assessment id, reviewer identity, timestamp, and authentication method `local-session`. Approval still does not clear `INSUFFICIENT_DEMAND_EVIDENCE`, change the recommendation, mark the result final, or grant investor-ready. The official baseline stays unapprovable.

### Prototype limitations

This is not production authentication. There is no OAuth provider, no external identity system, no password hash, and no account directory. The passphrase is written in source and in this decision, so anyone who can read the repository and reach the local server can sign in. The cookie is not marked `Secure` because the prototype is localhost HTTP. A customer has no reviewer account. Session lifetime and sign-out are recorded in the following decision. Replacing this mechanism with production authentication is a later decision.

## Decision: Reviewer session lifetime and sign-out

- Date: 2026-11-07
- Status: Accepted for the local prototype only
- A reviewer session lasts `SESSION_LIFETIME_HOURS` (4 hours), measured from sign-in and stored as `expires_at` on the SQLite session row. The cookie `Max-Age` matches that lifetime. The server expiry is what approval checks.
- Every approval reloads the token from `reviewer_sessions` and rejects a missing, deleted, or expired token with 403. An old cookie cannot approve after that lifetime.
- Sign-out is `POST /reviewer/session/sign-out`. It deletes the current token and clears the cookie with `Max-Age=0`. A later approve attempt with that cookie returns 403.
- The reviewer screen shows signed in, signed out, or expired, and the remaining lifetime while the session is active. The approve control is hidden when the session is missing or expired. Sign out is labeled prototype and not a customer feature. Validate still only offers “Request review” and shows pending.
- A successful approval audit still includes the assessment id, reviewer identity, timestamp, and authentication method `local-session`. Approval still does not clear `INSUFFICIENT_DEMAND_EVIDENCE`, change the recommendation, mark the result final, or grant investor-ready. The official baseline stays unapprovable.

### Prototype limitations

This lifetime and sign-out are still prototype-grade. There is no password hash, no OAuth or external identity provider, no per-person account, and no revocation list beyond deleting the local token. The passphrase remains the source constant. The cookie is still not `Secure`. A person who can read the source and reach the local server can sign in again until a later decision replaces this mechanism.

## Decision: Reviewer session audit events

- Date: 2026-11-07
- Status: Accepted for the local prototype only
- A successful sign-in writes a `sign-in` event. Sign-out writes a `sign-out` event. Approval writes an `approve` event in the same `reviewer_events` trail. Each event stores the reviewer identity, timestamp, authentication method, and a 12-character SHA-256 prefix of the session token (`session_id`). The raw token is not stored in the trail and is not shown in the audit JSON or on the reviewer screen.
- The assessment audit at `/assessments/{id}/audit` includes `reviewer_events` for that assessment and for session events that are not tied to one assessment. `sign-in`, `sign-out`, and `approve` stay distinguishable. The reviewer screen shows the last sign-in time, the last sign-out time, and the current session status, labeled prototype and not a customer feature.
- These events do not clear `INSUFFICIENT_DEMAND_EVIDENCE`, change the recommendation, mark a result final, or change investor readiness. A failed sign-in writes no event. An expired or signed-out session still cannot approve. The official baseline stays unapprovable, and `approvals` on that audit stays empty.

### Prototype limitations

This audit is still prototype-grade. It is a local SQLite log, not a production identity system. There is no password hash, no OAuth or external identity provider, and no per-person account. The passphrase remains the source constant. The session hash is a short display identifier, not a second secret. The cookie is still not `Secure`. A person who can read the source and reach the local server can sign in again until a later decision replaces this mechanism.

## Decision: Read-only HTML audit page

- Date: 2026-11-07
- Status: Accepted for the local prototype only
- `/assessments/{id}/audit/html` is a browser-readable audit view. It shows the current recommendation, recommend-against flags, gap flags, whether `INSUFFICIENT_DEMAND_EVIDENCE` is present, investor readiness, human review status, demand provenance (`verified`, `user`, or `placeholder`), and reviewer events. Each event shows its action, timestamp, and short session hash. The raw session token is not shown.
- The page is read-only. It has no form and no control that can change flags, approval, readiness, or the recommendation. A draft stays labeled draft. A recorded approval is labeled as approval only, and the page still shows the existing readiness status.
- Results, the served Markdown report, and the reviewer screen link to this page. `/assessments/{id}/audit` remains the JSON audit and its fields are unchanged. Opening the HTML page does not write the assessment. The official baseline still renders do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE` present, investor readiness internal, and human review pending.
- The reviewer-event section states that authentication remains prototype-grade and is not a customer feature. This page does not add production authentication.

## Decision: Dashboard, intake, and results presentation

- Date: 2026-11-07
- Status: Accepted for the local prototype only
- The dashboard lists saved assessments with Continue and View results. The official baseline is labeled separately from customer drafts and hypothetical drafts. A card shows the stored engine summary when a result exists. Before Analyze has been run, recommendation, demand evidence, and investor readiness say not run, and human review says pending. The list does not style a draft or the baseline as approved or investor-ready.
- The startup intake keeps three labels: user-supplied assumptions, verified data, and unmeasured placeholders. Missing required startup fields and missing monthly fields are stated on the form. Saving writes the posted values. Returning to the draft shows those values again, including a blank field and a worksheet default the customer changed. The form does not fill a blank with an invented number.
- The results page renders sources and uses, base and downside, and DSCR from the deterministic startup projection when that projection calculated. A simple bar compares the engine’s base and downside revenue. When monthly inputs are missing, the page says Insufficient verified information to calculate. The report and the HTML audit page stay linked from results. This presentation does not change scoring, flags, or the Investor Readiness Gate.

## Decision: Named pilots stay empty drafts

- Date: 2026-11-08
- Status: Accepted
- Only the RUGD Intelligence assessment is the official baseline. Its sample file stays unchanged: draft do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.
- Bunny Hive and Small Town Pub are created as empty named-pilot drafts. They are not completed assessments, they are not read-only, and they do not receive the baseline intake.
- Those names are application labels in the local store. `scoring/rules.py` and the 0.1 engine do not read them. Entering evidence later still does not approve the draft or make it the official baseline.
- Reviewer authentication remains the prototype mechanism recorded above. It is not production authentication. The unittest count is kept in `CURRENT_STATUS.md`.

## Decision: Optional external analyst

- Date: 2026-11-08
- Status: Accepted for the local prototype only
- `get_analyst()` remains the replacement point. With `ANALYST_PROVIDER` unset, the analyst is the Demonstration Analyst.
- `ANALYST_PROVIDER` may be `claude`, `openai`, or `grok`. The matching key is `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `XAI_API_KEY`. `ANALYST_MODEL` may override the default model. Keys are read from the environment and are not written into source.
- The provider receives only a summary of the current assessment and the engine result. Secret keys, including session tokens and the API key, are not placed in that summary. The request includes an instruction that the model must not change financial numbers, clear recommend-against flags, set `human_review_approved`, or change investor readiness.
- A missing key, an unknown provider, or a failed call falls back to the Demonstration Analyst and says that it is a fallback. The analyst still cannot mutate the stored engine result.
- This is not production AI integration. No key is committed. The explanation is not a decision, not evidence, and not approval.

## Decision: Optional public market extract

- Date: 2026-11-08
- Status: Accepted for the local prototype only
- Market observations use one interface. Each observation carries its source, geographic coverage, industry classification, measurement period, retrieval date, and limitations, plus the measure and value.
- The default provider is the existing synthetic snapshot. `MARKET_PROVIDER=bls` (aliases `qcew` and `bls-qcew`) requests the U.S. Bureau of Labor Statistics Quarterly Census of Employment and Wages annual file. No API key is required. `MARKET_YEAR` may select the annual file; the default is 2024.
- The first extract maps Restaurant to NAICS 722, Professional services to NAICS 54, and Retail to NAICS 44-45. The geographies are the United States (area US000), Alabama (area 01000), and Colbert County, Alabama (area 01033). The row used is private ownership. A disclosure code is shown as not disclosed, not as a measured zero.
- A selection outside that map, or a failed request, falls back to the labeled synthetic snapshot. Partner keeps that snapshot. Live feed and monitoring stay off.
- QCEW employment and wages are not demand evidence. They cannot clear `INSUFFICIENT_DEMAND_EVIDENCE` or any other recommend-against flag, and they cannot set `human_review_approved` or change investor readiness. The official baseline is unchanged.

## Decision: Broader QCEW extract

- Date: 2026-11-08
- Status: Accepted for the local prototype only
- The same BLS QCEW provider now reads, when the annual file publishes them, private total annual wages, private average annual pay, and establishment size coverage. Size code 0 is labeled all size classes combined. It is not a size-class breakout.
- The industry map adds Construction (NAICS 23), Manufacturing (NAICS 31-33), Accommodation (NAICS 721), and Health care (NAICS 62). Restaurant (722), Professional services (54), and Retail (44-45) stay. Geographies stay the United States, Alabama, and Colbert County, Alabama.
- A disclosed row shows each available measure with the same provenance. A suppressed row is one observation, value “Not disclosed,” and a zero in the file is not shown as a measured zero. A missing extra column is omitted. A missing industry row, an unmapped selection, or a failed request still falls back to the labeled synthetic snapshot.
- The page names the active provider and year. No new environment variable and no API key. The figures still do not clear a recommend-against flag or set `human_review_approved`.

## Decision: Census ACS beside QCEW

- Date: 2026-11-08
- Status: Accepted for the local prototype only
- `MARKET_CENSUS=acs` (aliases `census` and `census-acs`) reads American Community Survey 5-year total population (table B01003) and median household income (table B19013) from the public data.census.gov table extract. `ACS_YEAR` defaults to 2024, which is the 2020–2024 period. No API key is required or sent. The Census Data API at api.census.gov is not called.
- Geographies are the same three names: United States, Alabama, and Colbert County, Alabama. The figures are demographic. They are not a NAICS industry and they do not describe one business.
- With `MARKET_PROVIDER=bls` and `MARKET_CENSUS=acs`, the page shows both extracts and names each provider and year. If one request fails or the selection is outside its map, that part falls back to the labeled synthetic snapshot and the other part remains. If neither returns observations, the page is the synthetic snapshot.
- A negative Census sentinel is shown as not disclosed. These figures cannot clear `INSUFFICIENT_DEMAND_EVIDENCE` or any other recommend-against flag, and they cannot set `human_review_approved`. The official baseline is unchanged.

## Decision: More market geographies

- Date: 2026-11-08
- Status: Accepted for the local prototype only
- BLS QCEW and Census ACS both cover Tennessee (QCEW area 47000, ACS state 47) and Hamilton County, Tennessee (QCEW area 47065, ACS county 47065), in addition to the United States, Alabama, and Colbert County, Alabama.
- A geography outside that list still falls back to the labeled synthetic snapshot for the provider that cannot cover it.
- `MARKET_YEAR` selects the QCEW file and `ACS_YEAR` selects the ACS vintage. Each defaults to 2024. The Market Intelligence page names the active year for each provider and says the year is controlled by those environment variables. There is no year control on the page. The figures still do not clear a recommend-against flag.

## Decision: Market summary and observation export

- Date: 2026-11-08
- Status: Accepted for the local prototype only
- Market Intelligence shows a combined summary of the figures for the selected industry and geography. Each line names the source, coverage, and period. The summary also names the active provider and year, or says that no public provider is active.
- `/market/export` downloads those observations as JSON. A synthetic or failed view exports the labeled synthetic examples. The file does not include an assessment or session secrets. Opening it does not change a saved assessment or the official baseline.
- The summary and the file repeat that the figures do not clear a recommend-against flag.

## Decision: Multi-source market research view

- Date: 2026-11-09
- Status: Accepted for the local prototype only
- `MARKET_CBP=cbp` reads County Business Patterns from the public data.census.gov table for the mapped geographies. `CBP_YEAR` defaults to 2023. No API key is used. The table is sector grain. A NAICS code that is not in the table, including Restaurant 722 and Accommodation 721, falls back for that part only.
- BLS over-the-year percent changes, the difference between two overlapping ACS 5-year population vintages, the ACS B19001 income-bracket note, and CBP annual payroll are extended metrics. Establishments from County Business Patterns and the existing employment, population, and median-income figures stay in the headline snapshot.
- Geographies now also include Georgia and Fulton County, Georgia.
- Market Intelligence has a view control. Explore shows the headline snapshot. Analyze adds the full current view and a Market Research Summary. Validate and Partner add the extended metrics. The summary states that it is derived from the cited public sources and that it is not a recommendation. The control does not change a recommendation, a flag, investor readiness, or `human_review_approved`.
- The Partner screen still does not call these providers. Recurring monitoring is not active.

## Decision: Tiered evaluation outputs

- Date: 2026-11-09
- Status: Accepted for the local prototype only
- Analyze results show Evidence Gaps, Key Assumptions, a Risk Summary, and Suggested Next Research Steps. Those sections restate engine flags, missing fields, intake assumptions, and the demonstration market snapshot. They do not add a score, clear a flag, or set `human_review_approved`. Explore does not show the four sections.
- Validate shows a Review Package with current flags, market context, evidence gaps, and a reviewer-notes placeholder. The customer screen remains request-only. Approval stays on the prototype reviewer screen.
- Partner shows an Ongoing Intelligence demonstration. Trend alerts and management actions are marked hypothetical. Monitoring stays inactive.

## Decision: Research package export

- Date: 2026-11-09
- Status: Accepted for the local prototype only
- Download Research Package writes a JSON file for one assessment. It includes the assessment summary, the stored engine result, market observations with provenance, evidence gaps and flags, the analyst explanation, and the tier and prototype disclaimers. A Markdown copy and a print-friendly Research Brief show the same content.
- The export does not run the engine and does not change the stored assessment. It omits session tokens, passphrases, and cookies. It does not clear a recommend-against flag or set `human_review_approved`.

## Decision: Future seams stay disabled

- Date: 2026-11-09
- Status: Accepted for the local prototype only
- `app/future.py` holds four disabled replacement points: production authentication, scoring methodology, deployment settings, and billing hooks. Environment variables cannot enable them. The running server does not read the deployment seam and stays on 127.0.0.1. No score is calculated. The scoring seam returns “Not calculated — methodology pending approval.” No charge is created. No production identity provider is connected.
- Activating one seam requires a new written decision that names the owner input below. The other seams stay disabled. The official baseline, the recommend-against flags, and the Investor Readiness Gate stay unchanged.

Owner input required before replacing `production_auth_provider`:

- Name the provider: local accounts, OAuth, or an external identity provider.
- Say where account records will live and whether passwords will be hashed.
- Confirm a customer account cannot set `human_review_approved`.
- Confirm reviewer approval still cannot clear a flag or grant investor-ready by itself.

Owner input required before replacing `scoring_methodology`:

- Approve the score definition and its weights in writing.
- Confirm the score does not replace a recommend-against flag or the Investor Readiness Gate.
- Confirm the score cannot clear `INSUFFICIENT_DEMAND_EVIDENCE` or set `human_review_approved`.

Owner input required before replacing `deployment_settings`:

- Name the host, port, operator, TLS, and domain.
- Say whether the app may leave 127.0.0.1.
- Confirm a deployed app does not overwrite the official baseline files.

Owner input required before replacing `billing_hooks`:

- Name the payment provider, the products, and the prices.
- Confirm a payment cannot clear a flag, approve a review, or set investor-ready.

## Decision: Educational Durable Value guidance is not a DVT evaluation

- Date: 2026-11-09
- Status: Accepted for the local prototype only
- The seven pillars are the evaluation dimensions already named in the methodology and in `scoring.rules.DIMENSIONS`. The app shows them as educational questions and practical prompts. The visible label is “Educational guidance — not a DVT evaluation.”
- Explore shows the introductory questions. Analyze places a prompt next to an engine flag or gap only when that pillar lists the flag. Validate and Partner show the same educational content in their demonstration views.
- An optional note is stored in `guidance_notes`, not in the engine result and not in the intake. The note is non-authoritative. It cannot change the recommendation, flags, readiness, a score, or `human_review_approved`. The official baseline cannot store a note.
- No pillar is scored. No DVT table, score, or code is imported. A future Durable Value connection still requires a documented, versioned interface and an owner decision.

## Decision: Business profiles are local scaffolding

- Date: 2026-11-09
- Status: Accepted for the local prototype only
- A business profile stores identity, industry, geography, and stage. An assessment stores `business_profile_id`. More than one draft may share a customer profile. A new assessment for that profile copies those four fields so a move to another tier does not require them again. Financial entries, evidence, the engine result, and `human_review_approved` stay on the assessment.
- The official baseline profile is isolated. A draft cannot link to it. Named-pilot and demonstration profiles are isolated from the baseline and from customer profiles. A customer form cannot select them.
- Profiles do not authenticate a user. There is no production account, password, or identity provider. Changing tier still does not change a stored recommendation.

## Decision: Market Pulse stays a demonstration

- Date: 2026-11-09
- Status: Accepted for the local prototype only
- Market Pulse shows static internal and external example cards. The visible label on the dashboard and on every card is “Hypothetical demonstration — monitoring not active.” Monitoring active stays false. Live feed connected stays false. Scheduled jobs, connectors, and notifications stay empty.
- The eight actionable recommendation questions are a static template. The repository did not contain a prior list, so the template asks what changed, whether the example is internal or external, which assumption it would touch, whether an existing flag stays active, what evidence is missing, what a manager would check, who must review a change, and what would have to be connected before the card could leave the demonstration. The questions are not answers and are not a recommendation.
- Durable Value pillar names on a card are educational labels. They are not a DVT evaluation and they are not a score.
- A query string cannot turn monitoring on. The dashboard does not call a market provider. It does not clear a recommend-against flag or set `human_review_approved`. A scheduled Market Pulse job still requires an owner decision.

## Decision: Local email and password accounts for the pilot

- Date: 2026-11-09
- Status: Accepted for the local pilot only. This does not enable the production authentication seam in `app/future.py`.
- The owner asked for local email and password accounts on this machine. Account records live in the local SQLite `users` table. The password is stored as a scrypt hash. The password is not stored. Roles are `customer` and `reviewer`.
- Registration and login are local screens. A session cookie named `rugd_session` is HttpOnly, Path=/, and SameSite=Lax. The raw token is not written to SQLite. The cookie is not marked Secure because the server is HTTP on 127.0.0.1. A session lasts 4 hours. Logout deletes the stored session.
- A customer account cannot set `human_review_approved`. Approval requires an authenticated reviewer-role session. Approval still cannot clear a recommend-against flag, change the recommendation, mark a result final, or grant investor-ready by itself. The official baseline cannot be approved. The audit records the account email.
- The previous shared passphrase is no longer accepted. Anyone who can open this local server can register a reviewer account. That is a pilot limitation, not production role administration. OAuth, an external identity provider, production password policy, and TLS cookies remain an owner decision.

## Decision: Reviewer accounts are not self-service

- Date: 2026-11-09
- Status: Accepted for the local pilot only. This does not enable the production authentication seam.
- The public Register screen creates a customer account. A submitted role other than customer is refused and creates no account. Register does not change the role of an existing account.
- The first reviewer is created only when both `RUGD_BOOTSTRAP_REVIEWER_EMAIL` and `RUGD_BOOTSTRAP_REVIEWER_PASSWORD` are set and no reviewer account exists. The password is hashed and is not written into source. If a reviewer already exists, the variables do nothing. If that email is already a customer, the role stays customer.
- A later reviewer is created at `POST /reviewer/accounts` by a signed-in reviewer. A customer session and a missing session receive 403. There is no control that changes a customer's role to reviewer.
- Approval still requires that reviewer session, still records that reviewer's email, and still cannot clear a flag, change the recommendation, or grant investor-ready status. The official baseline cannot be approved. Existing reviewer rows remain valid.

## Decision: Render pilot configuration

- Date: 2026-11-09
- Status: Accepted as deployment preparation. The service remains pilot-grade. This does not enable billing, scoring, or the deployment seam in `app/future.py`.
- The owner asked to prepare RUGD Analyze for Render at `app.rugdintelligence.com` with HTTPS and secure session handling. `app/config.py` reads the environment. `RUGD_ENV=production` binds `0.0.0.0` to Render's `PORT`, uses `RUGD_DATABASE` for the SQLite file, requires `SECRET_KEY` of at least 32 characters, and marks the session cookie Secure. `SECURE_COOKIES=true` marks the cookie Secure without changing the bind address. Local runs leave both unset and stay on 127.0.0.1:8765.
- Every response sends `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: same-origin`. No secret is written into the repository. `.env` files stay gitignored.
- Render terminates HTTPS. The DNS step is a CNAME from `app.rugdintelligence.com` to the Render hostname. The apex domain stays on the public website. The process is `python -m app`, one instance, one SQLite file on the Render disk.
- Prototype warnings stay. There is no rate limit, no email verification, and no public self-service billing. A customer path still cannot set `human_review_approved`. Market data and the analyst still cannot clear a flag. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Decision: BEA Regional and NAICS County Business Patterns

- Date: 2026-11-09
- Status: Accepted for the local prototype only. This does not close the real-market-data owner decision and does not add a commercial dataset.
- `MARKET_BEA=bea` (aliases `regional` and `bea-regional`) reads the Bureau of Economic Analysis Regional Economic Accounts API. `BEA_YEAR` defaults to 2024. The request needs `BEA_USER_ID`, a free BEA API user id. The id is not written into source and is not shown on the page. Without it, that part falls back to the synthetic snapshot.
- The two BEA figures are CAGDP2 line 1, current-dollar GDP for all industries, and CAINC1 line 1, personal income. Both are published in thousands of dollars and are shown as published. They are geography totals for the United States (GeoFips 00000), Alabama, Colbert County, Tennessee, Hamilton County, Georgia, and Fulton County. They are not one NAICS industry and not revenue for one business. A suppressed cell is shown as not disclosed.
- County Business Patterns still reads the data.census.gov sector table when that table contains the NAICS code. Restaurant 722 and Accommodation 721 are not in that table. Those codes are requested from the Census CBP API filtered to the NAICS code, legal form 001, and employment size 001. No Census API key is sent. The figures remain establishments, employment, and annual payroll in thousands of dollars. A failed NAICS request falls back for that part only.
- Every observation keeps source, geographic coverage, industry classification, measurement period, retrieval date, and limitations. The combined summary lists BEA beside BLS and ACS. The figures do not clear a recommend-against flag and do not set `human_review_approved`. The official baseline is unchanged.

## Decision: Indicative score beside the engine

- Date: 2026-11-09
- Status: Accepted for display only. This does not approve a feasibility score and does not enable `scoring_methodology()` in `app/future.py`.
- The owner asked for a transparent 0–100 indicative score for market validity, profitability, and Durable Value. The weights are 40, 35, and 25. The exact inputs are in `SCORING.md`. The overall number is the weighted sum with the remainder dropped.
- Any recommend-against flag forces band Blocked. The engine recommendation stays do-not-proceed while that flag is active. A high number does not clear the flag, change investor readiness, or set `human_review_approved`.
- The component rules read the engine demand status, engine monthly contribution, cash flow, and capital-recovery months, downside DSCR when the projection calculated it, and optional educational notes. Missing notes stay at a floor of 70. Competitive density is not measured and adds 0. A stored public market figure can add 20 market points and still cannot clear a flag.
- The feasibility line remains “Not calculated — methodology pending approval.” `overall_feasibility_score` stays null. The results page and the HTML audit show the indicative score with the label that it does not override engine flags or human review.

## Decision: Indicative assessment leads with the gate

- Date: 2026-11-09
- Status: Accepted for display only. This does not approve a feasibility score and does not enable `scoring_methodology()`.
- The primary lines are gate status and band. The three component scores are Market Validity, Financial Viability, and Stewardship Readiness. The weights are 45, 40, and 15. Stewardship is the light weight. Missing optional notes stay at 90, and each stored pillar note adds 1 point.
- A recommend-against flag forces band Blocked and the gate recommendation do-not-proceed. The stored engine recommendation is not rewritten. The overall 0–100 number is labeled indicative only. It cannot clear a flag, set `human_review_approved`, or grant investor-ready status.
- `MARKET_LAUS=laus` reads BLS Local Area Unemployment Statistics for the mapped states and counties: unemployment rate (measure 03) and labor force (measure 06), annual average period M13. `LAUS_YEAR` defaults to 2024. No API key is sent. The United States row uses the Current Population Survey national series because LAUS is a local-area program. A failed request or an unmapped geography falls back to the synthetic snapshot. These figures do not clear a recommend-against flag.
