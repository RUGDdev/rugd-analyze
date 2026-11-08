# RUGD Analyze 0.2 acceptance checklist

Updated: 2026-11-08. This maps the original version 0.2 acceptance criteria to the local prototype. It does not change the engine, the gates, or the official baseline.

The official baseline remains draft do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, human review pending, and `human_review_approved` false. No feasibility score is calculated.

## Browser acceptance criteria

| Criterion | Status | Note |
| --- | --- | --- |
| View the RUGD customer dashboard | Met | The local dashboard lists saved assessments, progress, and a next step. |
| Navigate Explore, Analyze, Validate, and Partner | Met | One navigation bar includes those destinations. Validate and Partner are labeled demonstration. |
| Open the existing RUGD Intelligence assessment | Met | The sample is loaded as the read-only official baseline. |
| See its blocking flags and incomplete status | Met | The baseline shows do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, internal readiness, and pending human review. |
| Create a new restaurant startup assessment | Met | A labeled hypothetical restaurant draft and new startup drafts can be created. |
| Enter and save business information | Met | Save and resume keep the values that were entered, including a blank field. |
| Receive guided intake assistance | Partially met | The intake shows the next missing item and a Demonstration Analyst. No external conversational AI is connected. |
| Run the deterministic financial engine | Met | Analyze calls the unchanged 0.1 engine. |
| View supported financial calculations | Met | Sources and uses, base and downside, and DSCR appear when the engine calculates them. |
| Compare available scenarios | Met | The comparison is the engine’s base and downside views. |
| Review a draft recommendation | Met | The recommendation stays a draft. Approval does not rewrite it. |
| See missing evidence requirements | Met | Missing required fields and `INSUFFICIENT_DEMAND_EVIDENCE` stay visible. |
| Open the report and audit | Met | Markdown report, JSON audit, and a read-only HTML audit page are available. |
| Explore market intelligence | Demonstration-only | One synthetic snapshot is shared. No live feed and no source dataset are connected. |
| View Validate and Partner | Demonstration-only | Validate can request review and cannot approve. Partner states that recurring monitoring is not active. |
| Return to saved assessments | Met | Dashboard history offers Continue and View results. |
| Baseline status unchanged | Met | do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, internal investor readiness, pending human review. |
| No unapproved score, final result, or investor-ready status | Met | No feasibility score is invented. `is_final` stays false. Investor-ready still requires every existing gate plus explicit human review approval. |

## Related 0.2 scope

| Area | Status | Note |
| --- | --- | --- |
| Four service tiers in one application | Met | Tier, recommendation, evidence, approval, and readiness are separate. Changing tier does not change a stored recommendation. |
| Startup intake with evidence labels | Met | User-supplied assumptions, verified data, and unmeasured placeholders stay distinct. |
| Acquisition and investor-commissioned purposes | Partially met | The purposes can be selected and are marked unsupported. They do not score. |
| Demonstration Analyst | Demonstration-only | It explains the current engine result and cannot change figures, flags, approval, or readiness. |
| Reviewer approval | Partially met | A local prototype session can record approval. It is not production authentication, and it cannot clear flags or grant investor-ready by itself. |
| Customer approval control | Met | An ordinary customer post that includes `human_review_approved` returns 403. |
| Reports identify draft status and limitations | Met | Results and the HTML audit include a limitations note. Reports do not overwrite the official 0.1 files. |
| Named pilots | Met | Bunny Hive and Small Town Pub are empty drafts. Only RUGD Intelligence is the official baseline. |
| Brand colors and local layout | Partially met | The stated brand colors are used. No official logo file is in this repository. |
| Local persistence and tests | Met | Drafts are in gitignored SQLite. The unittest suite covers the prototype path. |
| Billing, public deployment, live market data, matchmaking | Not in 0.2 | These were excluded from the prototype and remain owner decisions. |

## Owner decisions required before further work

Do not start these until an owner chooses them:

- Production authentication, including accounts, password hashing, OAuth, or an external identity provider
- Real market data sources, including Census, American Community Survey, BLS, BEA, or a commercial dataset
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
