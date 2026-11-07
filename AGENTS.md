# RUGD project instructions

Work only in `c:\Projects\RUGD` on the dedicated Windows PC. Do not create a replacement RUGD project.

Longarc_Platform is a separate codebase. Do not open, start, modify, or import it. Do not merge DVT scoring, data, or services into RUGD. A future connection requires a documented, versioned interface, not shared code.

The public website is a separate Webflow project. Do not modify or publish it.

Read `/docs` before changing the engine. The 0.1-pilot analytical code stays authoritative:

- `engine/financial.py`
- `engine/startup_projection.py`
- `engine/startup_capital_calculator.py`
- `scoring/rules.py`
- `scoring/industry_benchmarks.py`
- `run_assessment.py`
- `intake/samples/rugd_intelligence.json`

Do not change scoring weights, recommend-against criteria, or Investor Readiness Gate conditions. Do not invent a feasibility score. Customer-entered values are user-supplied assumptions, not verified data. A customer control must not set `human_review_approved`. Secondary industry benchmarks cannot clear or raise a recommend-against flag.

The official RUGD Intelligence baseline remains a draft **do-not-proceed**, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, readiness **internal**, and human review pending, until real evidence and an authorized review change it.

Resume from `CURRENT_STATUS.md` and `DECISIONS.md`. Update `CURRENT_STATUS.md` after each milestone.
