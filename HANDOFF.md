# HANDOFF

Resume RUGD Analyze 0.2 from this repository only: `c:\Projects\RUGD`.

Read `AGENTS.md`, `CURRENT_STATUS.md`, `DECISIONS.md`, and `ACCEPTANCE.md` before changing the engine or the prototype. `HANDOFF.md` does not override those files.

## What stays true

The official baseline in `intake/samples/rugd_intelligence.json` remains draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. The 0.1 engine in `engine/` and `scoring/` is authoritative. Do not change scoring weights, recommend-against criteria, or Investor Readiness Gate conditions. Do not invent a feasibility score. Do not open Longarc_Platform or the Webflow site.

A customer post whose body contains `human_review_approved` returns 403. Durable Value guidance is educational and is not a DVT evaluation. Market Pulse is a hypothetical demonstration. Monitoring is not active. Business profiles are local prototype records and do not authenticate a user.

Local accounts exist for pilot use. Self-registration creates a customer account only. The first reviewer is created from `RUGD_BOOTSTRAP_REVIEWER_EMAIL` and `RUGD_BOOTSTRAP_REVIEWER_PASSWORD` when no reviewer exists. A signed-in reviewer can create another reviewer. A customer cannot change role or approve. The cookie is HttpOnly and SameSite=Lax. It is marked Secure when `RUGD_ENV=production` or `SECURE_COOKIES=true`. On local HTTP it is not marked Secure. This is not production authentication. The shared prototype passphrase is no longer accepted.

The local app is `python -m app` with the Python 3.12 path in `README.md`. With `RUGD_ENV` unset it binds to 127.0.0.1:8765. `DEPLOYMENT.md` and `render.yaml` prepare the same command for Render at `app.rugdintelligence.com`. The service stays pilot-grade: one SQLite instance, prototype warnings, no rate limit, and no email verification. Tests are `python -m unittest discover -s tests` from this directory. The current suite is 123 tests. An indicative score is documented in `SCORING.md`. It does not replace the feasibility line below.

## Owner decisions required before 0.3 work

Do not start 0.3 work on any item below until an owner chooses that item. The same list is in `ACCEPTANCE.md`.

- Production authentication beyond the pilot's local email and password accounts, including OAuth, an external identity provider, or a production password policy
- Real market data sources beyond the optional BLS QCEW, ACS, County Business Patterns, and BEA Regional extracts, including a commercial dataset
- An approved scoring methodology, including any feasibility score
- Billing, payment processing, and subscription pricing
- Investor matchmaking, securities solicitation, brokerage, or capital movement
- Recurring Partner monitoring and scheduled market jobs
- An external AI provider for the analyst
- Public deployment beyond the prepared Render pilot. `DEPLOYMENT.md` covers `app.rugdintelligence.com`. Rate limiting and email verification are still open
- A LongArc or DVT connection
- A change to the Webflow site
- A replacement frontend, including React
- Supplying the official logo artwork
- Real completed intakes for Bunny Hive and Small Town Pub
- Releasing an investor summary for any assessment, which still depends on the existing gate and an authorized review

Optional BLS QCEW, ACS, County Business Patterns, BEA Regional, and BLS LAUS extracts can already be requested. BEA needs `BEA_USER_ID`. They do not close the real-market-data decision. `app/future.py` keeps production authentication, scoring methodology, deployment settings, and billing hooks disabled.

## After an owner decision

1. Record the decision in `DECISIONS.md`, including the owner input named there for that seam.
2. Replace only the matching function in `app/future.py`. Leave the other three disabled.
3. Do not let the new seam clear a recommend-against flag, set `human_review_approved`, or grant investor-ready by itself.
4. Run the full unittest suite. Confirm the official sample and `reports/output/rugd-intelligence-draft.md` are unchanged.
5. Update `CURRENT_STATUS.md` with the new test count and what the owner approved.

The feasibility score line remains “Not calculated — methodology pending approval.” The indicative score in `SCORING.md` does not replace that line, a recommend-against flag, or the Investor Readiness Gate.
