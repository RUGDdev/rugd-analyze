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

## Decision: Email verification and password reset for local accounts

- Date: 2026-11-09
- Status: Accepted for the local pilot only. This does not enable the production authentication seam in `app/future.py`.
- A new account starts unverified. Registration, the bootstrap reviewer, and a reviewer-created account each send a verification link that expires in 24 hours. The account can log in before that link is opened. The pages then show a banner that the email is not verified. Opening the link marks that email verified and does not change the role.
- Forgot password sends a reset link when the email is registered. The page uses the same sentence when the email is not registered. The link expires in one hour, works once, and stores a new scrypt hash. It does not change the role.
- Leave `SMTP_HOST` unset and the running server writes the message to its log. Set `SMTP_HOST` to send through SMTP. Optional settings are `SMTP_PORT` (default 587), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_USE_TLS`. `RUGD_PUBLIC_URL` is the base of the link. On Render that value is `https://app.rugdintelligence.com`. The message does not include a password. A failed SMTP send uses the log.
- A posted role on registration or on the reset form does not change the stored role. A customer still cannot approve or create a reviewer. The links do not set `human_review_approved` and do not grant investor-ready status. The official baseline stays unchanged. Rate limiting remains an owner decision.

## Decision: Read-only assessment sharing

- Date: 2026-11-09
- Status: Accepted for the local pilot only. A share link is not an approval and is not investor-ready.
- A new assessment records the signed-in account as `owner_user_id`. Assessments created before that, including the official baseline, have no owner. The owner or a reviewer can create a read-only link. Another customer cannot. The lifetimes are 24 hours, 7 days, and until revoked. Any of those links can be revoked by the owner or a reviewer.
- The raw token is shown once. SQLite stores only its hash. The shared page shows the engine result when Analyze has been run, the indicative assessment with its non-overriding label, the industry, geography, and stage stored on the assessment, a labeled synthetic market note, and an audit summary. It includes the prototype warning. It has no form, no save, no analyze, no review request, and no approval control.
- A POST to the share address returns 403, including a body that contains `human_review_approved`. The link does not change the recommendation, flags, readiness, or `human_review_approved`. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Decision: Startup and existing-business onboarding paths

- Date: 2026-11-09
- Status: Accepted for the local pilot. This does not change the 0.1 engine, scoring weights, or the Investor Readiness Gate.
- Start a new assessment asks whether the draft is a startup idea or an existing or expanding business. A startup idea uses the current Explore intake, including construction cost, seats, occupancy, and the worksheet lines. An existing or expanding business skips those startup-only questions. It still collects demand evidence, operator capacity, regulatory or liability, stewardship, and the four monthly engine inputs: initial capital, monthly fixed costs, gross margin, and projected monthly base revenue.
- The choice is stored as `venture_path` on the business profile, `startup` or `existing`, and copied onto the draft. Existing profiles and the official baseline default to `startup`. A named-pilot button that omits the question stays on the startup path. Selecting a customer profile uses the path already stored there. A later save cannot switch the path.
- Skipped startup fields stay blank. The engine reports that the startup cost build was not calculated. It does not receive invented construction or seat figures. The choice does not clear a recommend-against flag, change a recommendation, or set `human_review_approved`.

## Decision: Production polish and the remaining owner list

- Date: 2026-11-09
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The verification notice, read-only share, onboarding choice, and indicative assessment use the left sidebar, the brand colors, and the same cards as the rest of the prototype. The dashboard states what the indicative assessment and a read-only share do.
- `HANDOFF.md` and `ACCEPTANCE.md` list the capabilities already in the prototype and the owner decisions that remain open. Those open items are production authentication, real market data beyond the public extracts, an approved scoring methodology, billing, investor matchmaking, recurring monitoring and rate limiting, an external analyst provider, LongArc or DVT, the Webflow site, a replacement frontend, official logo artwork, and completed named-pilot intakes or an investor summary.

## Decision: Advisor Summary and export package

- Date: 2026-11-09
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- Advisor Summary reads the stored result. It shows gate status, band, the three component scores, key flags, the labeled market snapshot, and educational Durable Value notes. Download Advisor Package is JSON. The printable HTML includes the same content and the provenance lines.
- A read-only share can open that summary and those downloads. A POST to the share address stays refused. The package does not run the engine, does not clear a recommend-against flag, and does not set `human_review_approved`. A hard gate still forces band Blocked and the gate recommendation do-not-proceed. The stored engine recommendation is not rewritten. The feasibility line stays “Not calculated — methodology pending approval.”

## Decision: Evidence checklist and progress guidance

- Date: 2026-11-09
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The Explore page, the open draft, and the results page show an evidence checklist. The items name verified demand evidence, missing monthly financial inputs, missing startup inputs on the startup path, key educational Durable Value notes, and any other active hard gate.
- Checking an item stores that it was noted. A saved intake value or an educational note shows the matching item as recorded. The state is checklist JSON on the assessment. It is not an engine input.
- Checking or completing an item does not clear a recommend-against flag, change the stored recommendation, or set `human_review_approved`. The official baseline intake stays unchanged.

## Decision: Base and one alternative scenario

- Date: 2026-11-09
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- Results can save the current engine result as Base. One additional case, Downside or Upside, runs the same engine on the current inputs. Downside scales revenue and occupancy by the stored downside multiplier. Upside uses the inverse of that multiplier, and occupancy stops at 1 because the engine rejects a higher occupancy.
- The two cases are shown side by side with key metrics. The comparison is stored apart from the official result. It does not change the recommendation, a hard gate, or `human_review_approved`. The engine’s own base and downside views inside one result stay as they are. The official baseline intake stays unchanged.

## Decision: Email preferences and the pilot handoff

- Date: 2026-11-09
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- Settings stores three email preferences for the signed-in account: assessment shared, review requested, and review recorded. A new account starts with all three off. The preference is stored on the user row. It is not an engine input.
- When the owner has turned an event on, the existing mail path sends one notice to that owner. With `SMTP_HOST` unset, the running server writes the notice to its log. The raw share token is not included. Verification and password-reset messages stay available and are not gated by these preferences.
- A notice does not approve an assessment, clear a recommend-against flag, change a role, or set `human_review_approved`. An assessment with no owner, including the official baseline, sends no preference notice.
- `HANDOFF.md` records that the local prototype is ready for a guided pilot and lists the owner decisions that remain open. Those decisions stay open. The official baseline intake stays unchanged.

## Decision: Plain language and a conversational assistant

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- Dashboard, Explore, the intake, results, the indicative assessment, and Market Intelligence keep the precise term visible and add one plain-language sentence. Learn more holds the tighter definition. The prototype warning and the indicative-score warning stay on the page.
- The evidence checklist leads with an everyday sentence. The precise name and the existing guidance stay. Checking or completing an item still updates guidance only.
- Results and the open draft include an assistant panel with three starter questions. The panel calls `get_analyst()`. A missing provider or a missing key uses the Demonstration Analyst. An external provider, when configured, receives the question with the same safety prompt. Every reply begins with the assistance-only label.
- The assistant reads the current assessment, engine result, flags, and any market notes passed with the question. It does not save a result, clear a recommend-against flag, set `human_review_approved`, or grant investor-ready status. The official baseline intake stays unchanged.

## Decision: Auth attempt limit, welcome banner, and assistant starters

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- Sign-in and registration accept 8 attempts from one network address in 15 minutes. The address is the first value in `X-Forwarded-For` when that header is present, and otherwise the connection address. The ninth attempt in the window returns a plain wait message and does not sign anyone in. Explore, Analyze, drafts, and the rest of the app stay available. Password reset and the other screens are not limited. Platform-wide rate limiting and recurring Partner monitoring remain owner decisions.
- The dashboard shows a welcome banner to a signed-in account that has not created a draft and has not dismissed the banner. Dismissing it stores that choice on the account. Creating a draft hides it. A visitor who is not signed in sees the same banner until they dismiss it in that browser or start a draft. The banner does not approve an assessment or set `human_review_approved`.
- The Ask panel offers five starter questions and an empty state that says a question can be asked about the current assessment. Every reply still begins with the assistance-only label. The assistant does not save a result, clear a recommend-against flag, set `human_review_approved`, or grant investor-ready status. The official baseline intake stays unchanged.

## Decision: Customer dashboard and section welcomes

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The signed-out dashboard shows Welcome to RUGD Intelligence, a short explanation, and Log in and Register. It does not list assessments.
- The signed-in dashboard lists only assessments owned by that account. Each card shows the name, business stage, last updated time, Continue or View results, and, after Analyze, the indicative gate status and band. A status line repeats a stored engine flag, a stored base-case DSCR when the engine calculated one, or the stored recommendation. It does not invent a figure. An account with no assessments is pointed to Start a new assessment.
- Explore, Analyze, Validate, Partner, Market Intelligence, Market Pulse, and Reports each show a welcome heading and one or two plain-language sentences. Demonstration labels and the prototype warning stay on those pages.
- The official baseline intake stays unchanged. A customer path still cannot set `human_review_approved`.

## Decision: Guided next step and progress marker

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The signed-in dashboard and the open assessment show Your next step. The link is Continue Intake before Analyze and View Results after Analyze. The note says completing the step does not clear a hard gate.
- Explore intake, the results page, and Advisor Summary show Intake, Analyze, and Review. The highlighted stage follows the stored file: Intake before Analyze, Analyze after a stored result, and Review after a review has been requested. The marker does not change a flag or a recommendation.
- My Assessments uses the welcome heading Welcome to RUGD My Assessments. Assessment cards link to the Ask panel. The Ask panel adds “What should I work on next?” and still begins every reply with the assistance-only label.
- The official baseline intake stays unchanged. A customer path still cannot set `human_review_approved`.

## Decision: Results, advisor, and market clarity

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The results page leads with the stored recommendation, an everyday reading of the gate and band, the stored engine figures, and Your next step. The everyday sentences do not replace the stored gate, band, or recommendation.
- Advisor Summary and a read-only share say Draft when `human_review_approved` is false. The advisor view still has no form that can edit or approve the assessment.
- Market Intelligence shows source, period, and limits before any figure. The figures do not clear a recommend-against flag.
- The Ask panel can explain the gate. Every reply still begins with the assistance-only label. The official baseline intake stays unchanged.

## Decision: Visual hierarchy

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- Assessment cards, the Intake to Review progress bar, the results lead, and Advisor Summary use clearer spacing and the existing ivory, charcoal, and bronze colors. A badge repeats the stored gate and band. It does not replace them.
- The progress bar can mark an earlier stage done. That mark does not change a flag, a recommendation, or `human_review_approved`.
- The official baseline intake stays unchanged.

## Decision: Explore intake suggestions

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- Explore intake offers local example phrases for development stage, products and services, target customers, and competition. The list narrows from the saved industry and, when present, the development stage. The phrases are labeled examples. Selecting one writes that text into the field as a user-supplied assumption.
- A suggestion does not fill a financial field, invent a number, clear a recommend-against flag, change demand evidence, or change investor readiness. The demand evidence question is unchanged.
- The official baseline intake stays unchanged. A customer path still cannot set `human_review_approved`.

## Decision: Suggestion catalog

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The example phrases are stored in `app/explore_suggestions.json`. Each industry has a name, aliases, keywords, search terms, and example lists for products and services, target customers, and competition. A general block is the fallback.
- A strong match is a whole word or phrase from the name, an alias, or a keyword. Search terms stay in the file and are not used for matching. The chips update from the industry typed on the form. Selecting one still writes user-supplied text only.
- A suggestion does not fill a financial field, invent a number, clear a recommend-against flag, change demand evidence, or change investor readiness. The official baseline intake stays unchanged.

## Decision: Provided suggestion catalog

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- `app/explore_suggestions.json` is the provided version 0.3 database. Its industry lists and general fallbacks are examples only. The description in that file says the values do not affect engine results or flags.
- Matching uses the name, aliases, and keywords. Search terms stay in the file and are not used for matching. The longest whole phrase wins. An equal length prefers a name or alias over a keyword. Unmatched text uses the general fallbacks.
- The catalog does not contain a separate product list for each development stage, so a stage does not invent a narrower list. Selecting a chip still writes user-supplied text only. The official baseline intake stays unchanged.

## Decision: Hover suggestions

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The example list for development stage, products and services, target customers, and competition is hidden until that field is hovered or focused. It is labeled Examples only. Choosing an example fills the field and closes the list. The field still accepts free text.
- The list still follows the industry name, aliases, and keywords, or the general fallbacks. It does not change a flag, a recommendation, or investor readiness. The official baseline intake stays unchanged.

## Decision: Pilot review purpose

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, the indicative weights, or the Investor Readiness Gate.
- The signed-in dashboard, results, and Advisor Summary state what the review is for. A hard recommend-against flag keeps the recommendation at do-not-proceed. An indicative number, a market figure, and an assistant reply cannot clear that flag or grant investor-ready status.
- Results name the industry and geography entered on the draft and show the labeled synthetic market examples. Optional public extracts stay on Market Intelligence. Those examples do not clear a recommend-against flag.
- The assistant can explain how this differs from a business plan. The reply does not change the stored recommendation. The official baseline intake stays unchanged.

## Decision: Guided patterns from a public review

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, a recommend-against flag, or the official baseline.
- Public pages for LivePlan and Upmetrics were reviewed for guidance only. No text, image, or code was copied.
- Each assessment card shows Intake, Analyze, and Review so the current stage is visible on the dashboard. Results open with three stored facts: recommendation, gate status, and the next step. Advisor Summary opens with recommendation, gate status, and investor readiness. Explore intake opens with three numbered steps. None of these write a result or clear a gate.

## Decision: Assistance workflow

- Date: 2026-11-10
- Status: Accepted for the local pilot. This does not change the 0.1 engine, a recommend-against flag, or the official baseline.
- The intake and results pages show four assistance stages: Intake guidance, Gap identification, Results explanation, and Next-step recommendation. The current stage is read from the stored file. A suggested next action links to the intake, the evidence checklist, or the stored result.
- The same panel offers two questions for that stage. `get_analyst()` still answers them. If Analyze has not been run, the reply says so and points back to the intake. The reply does not invent a figure, clear a flag, or set `human_review_approved`.
