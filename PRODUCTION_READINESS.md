# Production readiness — 2026-11-11

This report prepares a later owner deployment of RUGD Analyze. It does not deploy the service, does not change Render Auto-Deploy, and does not create a production account.

The official baseline stays draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. No feasibility score is calculated.

## Summary

The local pilot checks below passed. The Render process, mail delivery, load, and a second database instance were not run. There is no FAIL in the checks that were run. The service is not cleared for production.

## Checks

| Check | Result | What was done |
| --- | --- | --- |
| Unittest suite | PASS | `python -m unittest discover -s tests` on 2026-11-11: 199 tests, OK, 40.810 seconds. ResourceWarnings for unclosed sockets were printed. They are not test failures. |
| Customer isolation | PASS | `tests/test_access.py` and `tests/test_controls.py` refuse another customer's assessment, retrieval, and research records. The server returns the generic denial. |
| Public retrieval safety | PASS | Mocked tests cover the BLS QCEW and Federal Register allowlists, a rejected redirect, a body over the cap, a timeout, a private address, and the source and account budgets. A fourth source request and a ninth account request do not call the transport. |
| Historical live public requests | PASS, not repeated | One BLS QCEW request and one Federal Register request succeeded in earlier milestones. This readiness pass did not send another live request. |
| Session and production secret | PASS | The session cookie is HttpOnly and SameSite=Lax. It is Secure when `RUGD_ENV=production` or `SECURE_COOKIES=true`. Production startup refuses a missing or short `SECRET_KEY`. The stored session value is a hash. |
| Audit records | PASS | Sign-in, retrieval, import, rejection, and a research-update decision write a short category. The tests check that the detail does not contain the password or the retrieved text. |
| Financial baseline | PASS | `intake/samples/rugd_intelligence.json` SHA256 is `e7b3daafec3b63d3e45dd1d208a8b5c7b6d890a478b67f6e8ed579c3ea250a43`. That file is the intake. The draft result in `reports/output/rugd-intelligence-draft.md` remains do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, internal readiness, and `human_review_approved` false. Neither file was edited in this cycle. |
| Authenticated browser walk | PASS | On a temporary local database, a new customer registered, opened a startup draft, and reached Explore, Research, Analyze, Business plan, Pitch deck, Reports, Action Center, Adviser, and Market Pulse. Each response was HTTP 200 and included the workflow navigation and the sentence that a financial scenario does not replace the official result. Analyze said it had not been run. The signed-out home showed the local-pilot warning and “No feasibility score is calculated.” This was not a production account. |
| Dependency review | PASS | `requirements.txt` lists `python-pptx==1.0.2` and `fpdf2==2.9.0`. No package was added in milestones 7B through 10. |
| Repository hygiene | PASS | `.gitignore` ignores `.env` and `data/`. Those paths are not tracked. No secret was added in this commit. |
| Render runtime | NOT VERIFIED | The service was not deployed. The live health check, the persistent disk, and the dashboard environment were not observed. |
| Render Auto-Deploy | NOT VERIFIED | Auto-Deploy was not enabled and its dashboard state was not read. |
| SMTP delivery | NOT VERIFIED | Local registration can print the verification message. Delivery through an SMTP server was not tested. |
| More than one SQLite instance | NOT VERIFIED | The documented limit is one instance. A second writer was not run. |
| Load | NOT VERIFIED | No concurrent load test was run. |
| External penetration test | NOT VERIFIED | The security evidence is the local suite and the browser walk. |

## Authenticated browser notes

The walk used `http://127.0.0.1:8765` and a database under the local temporary directory. The temporary database was deleted after the walk.

An earlier attempt in the same session reached a process that had been started before the workflow navigation was saved. That attempt is not the result above. The walk was repeated against the current code. The temporary account from the first attempt was removed from the local prototype database. No production data was migrated.

## Rollback

See `DEPLOYMENT.md`. A later owner rollback is a manual Render deploy of an earlier commit. Do not force-push. A code deploy does not restore the SQLite file.

## Known limitations

- Local email and password accounts are the pilot sign-in. There is no paid identity provider and no billing.
- A proposed Federal Register rule or a notice is not an enacted requirement. A retrieved record does not clear `INSUFFICIENT_DEMAND_EVIDENCE`.
- Research synthesis quotes saved evidence. It does not add a market statistic.
- The adviser does not call a paid model unless a server-side key is configured, and a page view does not place that call. Live provider connectivity remains unverified in this report.
- Opening the workflow does not change the stored assessment.
