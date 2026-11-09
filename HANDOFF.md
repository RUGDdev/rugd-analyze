# HANDOFF

Resume RUGD Analyze 0.2 from this repository only: `c:\Projects\RUGD`.

Read `AGENTS.md`, `CURRENT_STATUS.md`, `DECISIONS.md`, and `ACCEPTANCE.md` before changing the engine or the prototype. `HANDOFF.md` does not override those files.

## What stays true

The official baseline in `intake/samples/rugd_intelligence.json` remains draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. The 0.1 engine in `engine/` and `scoring/` is authoritative. Do not change scoring weights, recommend-against criteria, or Investor Readiness Gate conditions. Do not invent a feasibility score. Do not open Longarc_Platform or the Webflow site.

The local app is `python -m app` with the Python 3.12 path in `README.md`. It binds to 127.0.0.1:8765. Tests are `python -m unittest discover -s tests` from this directory. The current suite is 104 tests.

## After an owner decision

1. Record the decision in `DECISIONS.md`, including the owner input named there for that seam.
2. Replace only the matching function in `app/future.py`. Leave the other three disabled.
3. Do not let the new seam clear a recommend-against flag, set `human_review_approved`, or grant investor-ready by itself.
4. Run the full unittest suite. Confirm the official sample and `reports/output/rugd-intelligence-draft.md` are unchanged.
5. Update `CURRENT_STATUS.md` with the new test count and what the owner approved.

The disabled seams are production authentication, scoring methodology, deployment settings, and billing hooks. Settings lists them as disabled. The scoring message remains “Not calculated — methodology pending approval” until a scoring decision is written.

The remaining owner-decision list is in `ACCEPTANCE.md`. Do not start an item on that list until an owner chooses it.
