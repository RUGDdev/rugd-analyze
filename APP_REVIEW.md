# RUGD Analyze 0.2 application review

Reviewed: 2026-11-09. Scope is the local prototype on `main` at `e9d7b3da775fa02fbb6fd75306a138b19724b651`. This review does not change the engine, the gates, or the official baseline.

## 1. Executive summary

RUGD Analyze 0.2 is ready for a local demonstration and for a planning conversation about what 0.3 is allowed to do. Explore through Analyze, saved drafts, the 0.1 engine, reports, audits, and exports work on 127.0.0.1. Market Intelligence can show optional public extracts and falls back to a labeled synthetic snapshot. Validate, Partner, Market Pulse, reviewer sign-in, and the external analyst remain explicitly prototype or demonstration features. The official baseline is still a draft do-not-proceed. Further product work should wait for an owner decision rather than another feature slice.

## 2. Functional coverage

### Explore → Analyze path

Met. A customer can open Explore, enter an intake, save a draft, and run Analyze. Run Analyze submits the same intake as Save draft. The engine is the unchanged 0.1 code. Unanswered demand stays do-not-proceed with `INSUFFICIENT_DEMAND_EVIDENCE`. A verified demand record is applied only when the source is exactly `verified` and a rationale is present. Clearing that flag does not approve the file or make it investor-ready.

### Dashboard and assessment history

Met. The dashboard lists saved assessments with progress, recommendation, whether `INSUFFICIENT_DEMAND_EVIDENCE` is present, investor readiness, and human review. Each card offers Continue, View results, and Export draft as JSON. The official baseline is labeled separately from drafts. Bunny Hive and Small Town Pub remain empty named-pilot drafts. The seeded hypothetical restaurant stays labeled as not a real assessment.

### Market Intelligence (real BLS + Census + fallback)

Partially met, and correctly bounded. The default page is the synthetic snapshot and says no Census, BLS, or BEA feed is connected. `MARKET_PROVIDER=bls`, `MARKET_CENSUS=acs`, and `MARKET_CBP=cbp` can request a QCEW annual extract, an ACS 5-year population and income extract, and a County Business Patterns extract. Explore is a limited snapshot, Analyze adds the full view and a sourced summary, and Validate and Partner add extended metrics. An uncovered industry, an uncovered geography, or a failed request falls back to the labeled synthetic snapshot. Restaurant 722 and Accommodation 721 fall back on the CBP sector table. The Partner page itself does not call the public providers. These figures are not a live feed and do not clear a recommend-against flag.

### Market Pulse demonstration

Met as a demonstration. The page shows static internal examples (revenue trend, labor) and external examples (local demographics, competitive developments, operating-cost pressure, emerging opportunity). Every card says “Hypothetical demonstration — monitoring not active.” Monitoring active, live feed, scheduled jobs, connectors, and notifications stay off. Eight review questions are a static template. A query string cannot turn monitoring on.

### Durable Value educational guidance

Met as education only. The seven pillars are the methodology dimensions already in `scoring.rules.DIMENSIONS`. The visible label is “Educational guidance — not a DVT evaluation.” Explore shows introductory questions. Analyze places a practical prompt next to a matching flag or gap. Optional notes live in `guidance_notes`, not in the engine result. The official baseline refuses a note. No score is calculated. LongArc / DVT is not connected.

### External analyst (Claude) and Demonstration Analyst fallback

Met for the local prototype. With `ANALYST_PROVIDER` unset, the analyst’s first line is “Demonstration Analyst. No external AI service is connected.” `claude`, `openai`, and `grok` are optional and read keys from the environment. A missing key, an unknown provider, or a failed call is labeled as a fallback to the Demonstration Analyst. The safety instruction forbids changing numbers, clearing flags, setting `human_review_approved`, and changing investor readiness. The results page does not call the network merely because it renders.

### Reports, HTML audit, JSON audit, downloads, and exports

Met. Results link to the Markdown report, the JSON audit, the read-only HTML audit, the print-friendly audit, the research package (JSON and Markdown), and the Research Brief. Downloads use the same bytes as the on-screen views and do not overwrite `reports/output/rugd-intelligence-draft.md`. Export draft and export-all omit session tokens, passphrases, and cookies and do not run the engine. The HTML audit has no form and no approval control.

### Reviewer authentication (prototype-grade) and approval path

Partially met, and labeled as such. Sign-in accepts one source-constant identity and passphrase, stores a random token, and sets an HttpOnly cookie for 4 hours. Sign-out deletes the token. Sign-in, sign-out, and approve write a local audit event with a short session hash. The raw token is not shown. Validate can request review and cannot approve. Approval does not clear a flag, change the recommendation, mark the result final, or grant investor-ready by itself. The official baseline cannot be approved. This is not production authentication.

### Persistent business profile scaffolding

Met as local structure. A profile stores identity, industry, geography, and stage. More than one customer draft can share a profile, so a new assessment does not ask for those four fields again. Financial entries, evidence, and the engine result stay on the assessment. The baseline profile cannot be linked. Named-pilot and demonstration profiles stay isolated from customer profiles. Profiles do not authenticate a user.

## 3. Safeguard verification

Confirmed against the sample, the application code, and the 112-test suite on 2026-11-09.

- The official intake `intake/samples/rugd_intelligence.json` is unchanged. Trailing revenue is null, and there is no verified `demand_evidence` record. The baseline result remains draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, human review pending, and `human_review_approved` false. No feasibility score is calculated.
- Any POST whose body contains `human_review_approved` returns 403 before routing, including a request aimed at the reviewer URL. The customer Analyze path forces approval and final status false. Validate tells the customer that the screen cannot set `human_review_approved`.
- Market observations and the analyst explanation restate outside context. They do not write the stored engine result, clear a recommend-against flag, or set approval. Educational notes and Market Pulse are held to the same limit. `app/future.py` keeps production authentication, scoring, deployment, and billing disabled. The scoring line remains “Not calculated — methodology pending approval.”
- Customer pages carry the banner “Local prototype. Not production security. This screen does not grant investor-ready status.” Validate, Partner, Market Intelligence, and Market Pulse keep their demonstration labels. Market Pulse cards keep “Hypothetical demonstration — monitoring not active.”

## 4. Brand and UX review

The 2026-11-09 restyle is in place and is suitable for a wide local demo.

- A persistent left sidebar lists Dashboard, Explore, Analyze, Validate (demonstration), Partner (demonstration), My Assessments, Market Intelligence (demonstration), Market Pulse (demonstration), Reports, and Settings. The active section is highlighted from the page title. Below 800px the sidebar stacks above the page, which is enough for a local demo and is not a phone layout.
- The sidebar header shows the bison, mountains, and wordmark from `app/static/rugd-logo.png`, with the line “Analyze 0.2-prototype · local prototype · not investor-approved.”
- The palette is dark blue-gray `#263746`, aged bronze `#A88958`, warm ivory `#F5F2EB`, soft stone `#E8E5DF`, antique gold `#E9D8B7`, and charcoal slate `#27323B`. The workspace is ivory, the sidebar is charcoal slate, and warning banners use antique gold.
- Warning text and tier labels are consistent across the customer pages checked: dashboard, baseline results, Market Intelligence, and Market Pulse. Demonstration destinations stay labeled in the sidebar.
- On the official baseline results page, the recommendation, the demand flag, investor readiness, `human_review_approved: false`, demand provenance, and the limitations note are readable. The page correctly says the engine did not calculate sources and uses. Print view hides the sidebar and keeps the limitations note.

Usability gaps that do not require an owner decision:

- The results page is long. The sidebar removes the old top-nav problem, and a reader still scrolls to reach tables, flags, and provenance.
- The logo file is a prototype wordmark for this app. It does not close the owner decision “Supplying the official logo artwork.”
- A reader who opens only `HANDOFF.md` or the brand row in `ACCEPTANCE.md` will not see the current test count or the logo file. Those two documents lag the brand commit.
- Reviewer sign-in is easy to over-read in a demo unless the presenter says the passphrase is a source constant and the cookie is not production security.

## 5. Test and documentation status

The unittest suite is 112 tests, all passing, run on 2026-11-09. The latest commit is `e9d7b3da775fa02fbb6fd75306a138b19724b651`, “0.2: RUGD brand restyle with left sidebar navigation,” by RUGD Dev. The working tree was clean before this review file.

`CURRENT_STATUS.md` is the accurate status file. Its engine line and the 2026-11-09 brand note both say 112 tests, and the Capabilities by tier matrix matches `ACCEPTANCE.md`. `DECISIONS.md` records the operating rules, including demand evidence, reviewer sessions, optional market extracts, educational guidance, business profiles, and Market Pulse. The 2026-11-07 sentence that version 0.2 does not call Census or BLS is the earlier rule. Later decisions in the same file allow the optional extracts and keep them from clearing flags.

Two documents are slightly behind the brand commit:

- `HANDOFF.md` still says the suite is 110 tests. The resume steps, the owner-decision list, and the warning that optional extracts do not close the market-data decision are otherwise accurate.
- `ACCEPTANCE.md` still says no official logo file is in the repository. The prototype wordmark is now at `app/static/rugd-logo.png`. The acceptance criteria, the tier matrix, and the owner-decision list otherwise match the prototype. The historical “Current Platform Status” block in `CURRENT_STATUS.md` still says 99 tests. Later progress notes are the current record.

## 6. Remaining gaps and owner decisions

These still require an owner decision before 0.3 work. Optional BLS, ACS, and County Business Patterns extracts do not close the market-data item. The prototype wordmark does not close the logo item.

- Production authentication, including accounts, password hashing, OAuth, or an external identity provider
- Real market data sources beyond the optional BLS QCEW extract, including Census, American Community Survey, BEA, or a commercial dataset
- An approved scoring methodology, including any feasibility score
- Billing, payment processing, and subscription pricing
- Investor matchmaking, securities solicitation, brokerage, or capital movement
- Recurring Partner monitoring and scheduled market jobs
- An external AI provider for the analyst
- Public deployment
- A LongArc or DVT connection
- A change to the Webflow site
- A replacement frontend, including React
- Supplying the official logo artwork
- Real completed intakes for Bunny Hive and Small Town Pub
- Releasing an investor summary for any assessment, which still depends on the existing gate and an authorized review

Small polish that can be done without a decision:

- Update the suite count in `HANDOFF.md` from 110 to 112.
- Update the brand row in `ACCEPTANCE.md` so it names `app/static/rugd-logo.png` and still says the official-artwork decision is open.
- Add a one-line pointer in the historical platform-status block of `CURRENT_STATUS.md` so a reader does not stop at “99 tests.”

## 7. Recommended next action

Run the local demonstration from `DEMO.md` on this commit, then stop. The prototype is ready to show. The next build step should be an owner choice from the list above, not another feature slice.
