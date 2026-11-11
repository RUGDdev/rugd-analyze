# HANDOFF

Resume RUGD Analyze 0.2 from this repository only: `c:\Projects\RUGD`.

Read `AGENTS.md`, `CURRENT_STATUS.md`, `DECISIONS.md`, and `ACCEPTANCE.md` before changing the engine or the prototype. `HANDOFF.md` does not override those files.

## What stays true

The official baseline in `intake/samples/rugd_intelligence.json` remains draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. The 0.1 engine in `engine/` and `scoring/` is authoritative. Do not change scoring weights, recommend-against criteria, or Investor Readiness Gate conditions. Do not invent a feasibility score. Do not open Longarc_Platform or the Webflow site.

A customer post whose body contains `human_review_approved` returns 403. Durable Value guidance is educational and is not a DVT evaluation. Market Pulse is a hypothetical demonstration. Monitoring is not active. Business profiles are local prototype records and do not authenticate a user.

Local accounts exist for pilot use. Self-registration creates a customer account only. The first reviewer is created from `RUGD_BOOTSTRAP_REVIEWER_EMAIL` and `RUGD_BOOTSTRAP_REVIEWER_PASSWORD` when no reviewer exists. A signed-in reviewer can create another reviewer. A customer cannot change role or approve. The cookie is HttpOnly and SameSite=Lax. It is marked Secure when `RUGD_ENV=production` or `SECURE_COOKIES=true`. On local HTTP it is not marked Secure. This is not production authentication. The shared prototype passphrase is no longer accepted.

The local app is `python -m app` with the Python 3.12 path in `README.md`. With `RUGD_ENV` unset it binds to 127.0.0.1:8765. `DEPLOYMENT.md` and `render.yaml` prepare the same command for Render at `app.rugdintelligence.com`. The service stays pilot-grade: one SQLite instance and prototype warnings. Sign-in and registration stop after 8 attempts from one network address in 15 minutes. The rest of the app is not limited. The customer shell is the left sidebar, the brand colors, and the cropped wordmark.

Current prototype capabilities:

- Local email and password accounts. Self-registration creates a customer. A reviewer is created from the bootstrap variables or by a signed-in reviewer. Email verification lasts 24 hours and password reset lasts one hour. With `SMTP_HOST` unset, the server log prints the message. Neither link changes a role.
- Start a new assessment asks whether this is a startup idea or an existing or expanding business. A startup idea uses the current Explore intake. An existing or expanding business skips the startup-only cost-build questions and still collects the monthly engine inputs. The choice is stored on the business profile.
- Analyze shows an indicative assessment for market validity, financial viability, and stewardship readiness. The rules are in `SCORING.md`. A recommend-against flag forces band Blocked. The feasibility line stays “Not calculated — methodology pending approval.”
- An assessment owner or a reviewer can create a read-only share for 24 hours, 7 days, or until it is revoked. The shared page cannot edit the assessment or approve it. The same link can open Advisor Summary.
- Advisor Summary shows the stored gate status, band, three component scores, key flags, market snapshot, and Durable Value notes. Download Advisor Package is JSON, and a printable HTML view includes provenance. Neither file runs the engine or changes the assessment.
- The Explore page, the open draft, and the results page show an evidence checklist for verified demand, missing financial inputs, and key Durable Value notes. Checking or completing an item updates guidance only. It does not clear a hard gate.
- Results can save the current engine result as Base and run one Downside or Upside case from the current inputs. The comparison does not change the official recommendation or a hard gate.
- Settings stores email preferences for assessment shared, review requested, and review recorded. The notice goes to the assessment owner when that account opted in. With `SMTP_HOST` unset, the server log prints it. Verification and password-reset messages stay available. A notice does not approve an assessment or clear a flag.
- Dashboard, Explore, the intake, results, and Market Intelligence show a short plain-language sentence beside the precise term. Learn more keeps the tighter definition. Results and the open draft include an assistant panel with eight starter questions, including what to work on next, what the gate means, and how this differs from a business plan. The assistant reads the current assessment through `get_analyst()` and does not change numbers, flags, or approval. The intake and results pages show an AI Business Adviser. It welcomes the reader and shows Intake guidance, Gap identification, Results explanation, and Next-step recommendation. Three questions and one link follow the current stage. One dismissible suggestion names a stored gap. Dismissing it does not clear a flag. The signed-in dashboard lists available modules and demonstration modules. Key engine figures keep the stored number and add a plain-language sentence. A signed-out home shows Welcome to RUGD Intelligence and does not list assessments. A signed-in home lists only that account, with a next-step link. Intake, results, and Advisor Summary show an informational Intake, Analyze, and Review marker. Assessment cards show the same three stages. Results and Advisor Summary open with three stored facts. Explore intake opens with three numbered steps that do not fill a field. Results then show the stored recommendation, the gate, the key engine figures, and the next step. Advisor Summary and a share link say Draft when the file is not approved. Market Intelligence puts source, period, and limits above the figures. Assessment cards, the progress bar, results, and Advisor Summary use the ivory, charcoal, and bronze layout. Explore intake shows example suggestions for development stage, products and services, target customers, and competition. The phrases come from the provided app/explore_suggestions.json and match the industry name, aliases, and keywords. Search terms stay in the file and are not used for matching. Unmatched text uses the general fallbacks. The examples stay hidden until that field is hovered or focused. Selecting one does not change the engine result. The stored gate, band, and engine figures are unchanged.
- Optional public extracts: BLS QCEW, ACS, County Business Patterns, BEA Regional, and BLS LAUS. A failed part falls back to the synthetic snapshot. The figures do not clear a flag.

Tests are `python -m unittest discover -s tests` from this directory. The current suite is 199 tests. Sign-in and public-retrieval decisions are written to `audit_events` without the password, the email, or the retrieved text. `RUGD_SOURCE_BATCH_LIMIT` and `RUGD_ACCOUNT_BATCH_LIMIT` can lower or raise the retrieval budgets inside a fixed range. Explore, Research, Analyze, the business plan, the pitch deck, Reports, Action Center, and the Adviser share one workflow navigation. Opening it does not change the assessment. A research summary compares saved sources and a research update is stored only after customer approval. A customer can retrieve one allowlisted BLS QCEW annual file or one allowlisted Federal Register search from Research, review the rows, and import a selection. A proposed rule or a notice is not an enacted requirement. A typed URL is still not fetched. Saved research, evidence, and Market Pulse developments stay beside the engine result. A monitoring topic does not record a check. The Claude adviser default is `claude-sonnet-5-5`, and `ANALYST_MODEL` can still override it. A failed adviser provider call keeps a safe category and does not show the provider body. Live provider connectivity is unverified. The adviser reads one authorized assessment, quotes stored engine figures, and stores a plan or deck suggestion only after the customer approves it. Live provider connectivity is unverified. A pitch deck copies a saved business plan for one audience, keeps edited slides, and exports PowerPoint and PDF from that copy. A financial preview calls the existing engines and does not save an official result. Charts show the engine contribution, cash flow, break-even, and Base versus Downside, and they do not invent an expense total or a monthly trend. A business plan copies stored figures into sixteen sections, keeps an edited narrative, and leaves the earlier plan in place after Analyze runs again. With no live adviser configured, the plan stays on the saved assessment text. Reports saves a snapshot from the stored assessment, and Action Center saves follow-up items without clearing a flag. History keeps the earlier report after Analyze runs again. An unclaimed draft stays unassigned and is visible to a reviewer. A visitor who is not signed in cannot open it. Seeded demonstrations stay readable and cannot be changed by a customer or a visitor. The home page asks what the customer wants to accomplish and opens a saved draft. Analyze checks the monthly fields, runs the 0.1 engine, and draws charts from that stored result. A blank monthly field stays missing, and a value that is not a finite number does not run the engine. The Downside chart uses a saved extra engine run and does not replace the official result. The adviser on that draft asks one question at a time and writes an answer only after Save this answer. With `ANALYST_PROVIDER` unset, no live model is called. A failed provider does not invent a reply. Continue to Analyze opens the monthly fields on the same draft. A customer can read and change only drafts that account owns. A reviewer can still open them. Another customer who changes the URL gets a generic refusal with no business name and no figures. An unclaimed draft stays unassigned: a signed-in customer cannot open it, and a visitor who is not signed in cannot open it either.

## Remaining gaps before a public launch

This local prototype is ready for an owner review. This work has not been published and has not been deployed. A public launch still needs the owner decisions in the next section: production authentication, a live or commercial market feed, an approved scoring methodology including any feasibility score, billing, investor matchmaking, scheduled monitoring, an external analyst provider, official logo artwork, and completed named-pilot intakes. Hard gates stay in force. Market figures and assistant replies cannot clear a flag or grant investor-ready status. The official baseline stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Ready for pilot users

A guided pilot can use this local prototype now. Start it with the Python 3.12 path in `README.md`: `python -m app`. With `RUGD_ENV` unset it binds to 127.0.0.1:8765. Every screen keeps the warning: Local prototype. Not production security. This screen does not grant investor-ready status.

A pilot user can:

- Register a customer account, verify the email, and reset the password. With `SMTP_HOST` unset, those messages are written to the server log.
- Start a startup or existing-business assessment, save it, and run Analyze.
- Read the indicative assessment, the evidence checklist, and one Base versus Downside or Upside comparison.
- Open Advisor Summary and download the package.
- Create a read-only share for 24 hours, 7 days, or until it is revoked.
- Store email preferences for assessment shared, review requested, and review recorded. The preference is stored on the account. With `SMTP_HOST` unset, a chosen notice is written to the server log.
- Read a plain-language sentence beside the precise terms, and ask the assistant about the current assessment. The assistant cannot change the assessment.
- Open Research on a business they can change, retrieve one allowlisted BLS QCEW annual file, and import a selected row. The row can be linked from a Market Pulse development. The retrieval does not change the official result.

The official RUGD Intelligence baseline stays draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. A pilot draft does not change that file.

Remaining owner decisions: production authentication beyond local email and password; real market data beyond the optional BLS QCEW, ACS, County Business Patterns, BEA Regional, and LAUS extracts; an approved scoring methodology, including any feasibility score; billing; investor matchmaking; recurring Partner monitoring, scheduled jobs, and platform-wide rate limiting; an external AI provider; a LongArc or DVT connection, a Webflow change, or a replacement frontend; official logo artwork; and real completed intakes for Bunny Hive and Small Town Pub, or any investor summary. The same list is below.

## Owner decisions required before further work

These remain open. The same list is in `ACCEPTANCE.md`. Local accounts, email verification, password reset, the indicative assessment, read-only sharing, the two onboarding paths, stored email preferences, and the prepared Render pilot are already in this prototype. They do not close the items below.

- Production authentication beyond local email and password, including OAuth or an external identity provider
- Real market data sources beyond the optional BLS QCEW, ACS, County Business Patterns, BEA Regional, and LAUS extracts, including a commercial or live feed
- An approved scoring methodology, including any feasibility score
- Billing, payment processing, and subscription pricing
- Investor matchmaking, securities solicitation, brokerage, or capital movement
- Recurring Partner monitoring, scheduled market jobs, and platform-wide rate limiting. Login and registration already stop after 8 attempts from one network address in 15 minutes. That limit does not cover the rest of the app.
- An external AI provider for the analyst
- A LongArc or DVT connection, a change to the Webflow site, or a replacement frontend
- Supplying the official logo artwork. The sidebar uses a cropped wordmark
- Real completed intakes for Bunny Hive and Small Town Pub, and any investor summary, which still depends on the existing gate and an authorized review

Optional BLS QCEW, ACS, County Business Patterns, BEA Regional, and BLS LAUS extracts can already be requested. BEA needs `BEA_USER_ID`. They do not close the real-market-data decision. `app/future.py` keeps production authentication, scoring methodology, deployment settings, and billing hooks disabled.

## After an owner decision

1. Record the decision in `DECISIONS.md`, including the owner input named there for that seam.
2. Replace only the matching function in `app/future.py`. Leave the other three disabled.
3. Do not let the new seam clear a recommend-against flag, set `human_review_approved`, or grant investor-ready by itself.
4. Run the full unittest suite. Confirm the official sample and `reports/output/rugd-intelligence-draft.md` are unchanged.
5. Update `CURRENT_STATUS.md` with the new test count and what the owner approved.

The feasibility score line remains “Not calculated — methodology pending approval.” The indicative score in `SCORING.md` does not replace that line, a recommend-against flag, or the Investor Readiness Gate.
