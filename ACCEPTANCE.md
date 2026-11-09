# RUGD Analyze 0.2 acceptance checklist

Updated: 2026-11-09. This maps the original version 0.2 acceptance criteria to the local prototype. It does not change the engine, the gates, or the official baseline.

The official baseline remains draft do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, human review pending, and `human_review_approved` false. No feasibility score is calculated.

## Browser acceptance criteria

| Criterion | Status | Note |
| --- | --- | --- |
| View the RUGD customer dashboard | Met | The local dashboard lists saved assessments, progress, a next step, and a What’s new note for the indicative assessment and read-only sharing. |
| Navigate Explore, Analyze, Validate, and Partner | Met | The left sidebar includes those destinations. Validate and Partner are labeled demonstration. |
| Open the existing RUGD Intelligence assessment | Met | The sample is loaded as the read-only official baseline. |
| See its blocking flags and incomplete status | Met | The baseline shows do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, internal readiness, and pending human review. |
| Create a new restaurant startup assessment | Met | A labeled hypothetical restaurant draft and new startup drafts can be created. Start a new assessment asks whether this is a startup idea or an existing or expanding business. The choice is stored on the business profile. |
| Enter and save business information | Met | Save and resume keep the values that were entered, including a blank field. |
| Receive guided intake assistance | Partially met | The intake shows the next missing item. The analyst is the Demonstration Analyst unless `ANALYST_PROVIDER` and an API key are set. |
| Run the deterministic financial engine | Met | Analyze calls the unchanged 0.1 engine. |
| View supported financial calculations | Met | Sources and uses, base and downside, and DSCR appear when the engine calculates them. |
| Compare available scenarios | Met | The engine still shows its base and downside views. Results can also save the current result as Base and run one Downside or Upside case. That comparison does not change the official recommendation or a hard gate. |
| Review a draft recommendation | Met | The recommendation stays a draft. Approval does not rewrite it. |
| See missing evidence requirements | Met | Missing required fields and `INSUFFICIENT_DEMAND_EVIDENCE` stay visible. The Explore page, the draft, and results show an evidence checklist. Checking an item updates guidance and does not clear a hard gate. |
| Open the report and audit | Met | Markdown report, JSON audit, a read-only HTML audit page, a research package JSON and Markdown export, and a print-friendly Research Brief are available. Advisor Summary adds a JSON package and a printable HTML view. An owner or reviewer can also open a time-limited or revocable read-only share, including the Advisor Summary. That page cannot edit or approve. |
| Explore market intelligence | Partially met | The default is one labeled synthetic snapshot. `MARKET_PROVIDER=bls` can show a BLS QCEW extract, `MARKET_CENSUS=acs` can show ACS population and income, `MARKET_CBP=cbp` can show County Business Patterns by NAICS, `MARKET_BEA=bea` can show BEA Regional GDP and personal income, and `MARKET_LAUS=laus` can show the BLS unemployment rate and labor force. Explore shows a limited snapshot, Analyze adds the full view and a sourced summary, and Validate and Partner add extended metrics. Failure of any part falls back to the synthetic snapshot. The figures do not clear a flag. |
| View Validate and Partner | Demonstration-only | Validate can request review, shows a prototype Review Package, and cannot approve. Partner states that recurring monitoring is not active and shows an inactive Ongoing Intelligence demonstration. Market Pulse is a separate hypothetical demonstration. |
| Return to saved assessments | Met | Dashboard history offers Continue and View results. |
| Baseline status unchanged | Met | do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, internal investor readiness, pending human review. |
| No unapproved score, final result, or investor-ready status | Met | No feasibility score is invented. An indicative 0–100 score is shown on results and the HTML audit. A recommend-against flag forces band Blocked. `is_final` stays false. Investor-ready still requires every existing gate plus explicit human review approval. |

## Related 0.2 scope

| Area | Status | Note |
| --- | --- | --- |
| Four service tiers in one application | Met | Tier, recommendation, evidence, approval, and readiness are separate. Changing tier does not change a stored recommendation. |
| Startup intake with evidence labels | Met | User-supplied assumptions, verified data, and unmeasured placeholders stay distinct. A startup idea uses that full intake. An existing or expanding business skips the startup-only cost-build questions and still collects the monthly engine inputs and the evidence questions. |
| Acquisition and investor-commissioned purposes | Partially met | The purposes can be selected and are marked unsupported. They do not score. |
| Demonstration Analyst | Demonstration-only | It explains the current engine result and cannot change figures, flags, approval, or readiness. An optional external provider uses the same limit and falls back to this analyst. |
| Reviewer approval | Partially met | A reviewer account created by the bootstrap variables or by an existing reviewer can record approval. Self-registration creates a customer, and a customer role cannot approve. It is not production authentication, and it cannot clear flags or grant investor-ready by itself. |
| Customer approval control | Met | An ordinary customer post that includes `human_review_approved` returns 403. |
| Reports identify draft status and limitations | Met | Results and the HTML audit include a limitations note. Reports do not overwrite the official 0.1 files. |
| Named pilots | Met | Bunny Hive and Small Town Pub are empty drafts. Only RUGD Intelligence is the official baseline. |
| Brand colors and local layout | Partially met | The left sidebar uses the stated brand colors and a cropped wordmark. Official logo artwork is still an owner decision. |
| Local persistence and tests | Met | Drafts are in gitignored SQLite. The unittest suite covers the prototype path. |
| Billing, public deployment, live market feed, matchmaking | Not in this prototype | Optional BLS QCEW, ACS, County Business Patterns, BEA Regional, and LAUS extracts are available. Render files for `app.rugdintelligence.com` are prepared. Billing, a live feed, matchmaking, and rate limiting remain owner decisions. |

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

## Owner decisions required before further work

These remain open. Local accounts, email verification, password reset, the indicative assessment, read-only sharing, the two onboarding paths, and the prepared Render pilot are already in this prototype. They do not close the items below.

- Production authentication beyond local email and password, including OAuth or an external identity provider
- Real market data sources beyond the optional BLS QCEW, ACS, County Business Patterns, BEA Regional, and LAUS extracts, including a commercial or live feed
- An approved scoring methodology, including any feasibility score
- Billing, payment processing, and subscription pricing
- Investor matchmaking, securities solicitation, brokerage, or capital movement
- Recurring Partner monitoring, scheduled market jobs, and rate limiting
- An external AI provider for the analyst
- A LongArc or DVT connection, a change to the Webflow site, or a replacement frontend
- Supplying the official logo artwork. The sidebar uses a cropped wordmark
- Real completed intakes for Bunny Hive and Small Town Pub, and any investor summary, which still depends on the existing gate and an authorized review
