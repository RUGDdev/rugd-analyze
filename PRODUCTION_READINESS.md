# Production readiness — 2026-11-11, cycle 3

This report prepares a later owner deployment of RUGD Analyze. It does not deploy the service, does not change Render Auto-Deploy, and does not create a production account. It does not start a payment provider.

The official baseline stays draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false. No feasibility score is calculated.

## Summary

Local pilot checks for recovery, sessions, quotas, and simulated plans passed. One check failed: a full unittest run still prints unclosed-socket ResourceWarnings. Render, SMTP delivery, a vulnerability database, load, and a second SQLite process were not run. The service is not cleared for production.

The earlier readiness note in this file recorded 199 tests. This pass records 223 tests.

## Checks

| Check | Result | What was done |
| --- | --- | --- |
| Unittest suite | PASS | `python -m unittest discover -s tests` after the plan and usage work: 223 tests, OK, about 50 seconds. One retrieval assertion was updated to the UTC retrieval date after the clock passed 2026-11-11. |
| Unclosed socket warnings | FAIL | That same run printed ten unclosed-socket ResourceWarnings during garbage collection. The tests still passed. Request sockets are closed in `AppHandler.finish`, and discarded HTTP responses get a finalizer. The warnings are not gone. |
| Database recovery | PASS | `tests/test_reliability.py` covers a rolled-back write, restart persistence, concurrent writes in one process, backup and restore on a temporary file, refusal of `data/analyze.sqlite`, a corrupt file, and a failed copy that removes its partial file. |
| Second SQLite process | NOT VERIFIED | The documented limit is one process. A second writer was not started. |
| Customer isolation | PASS | Existing access tests refuse another customer's assessment. `tests/test_session_security.py` also refuses another customer's page and does not show the business name. |
| Session rotation and logout | PASS | Sign-in deletes that account's older sessions. Logout deletes the presented session and writes a `sign_out` audit row. An expired `expires_at` is treated as signed out. Password reset stores a new hash and deletes existing sessions. |
| Foreign-origin POST | PASS | A POST whose Origin host differs from Host returns 403 and an audit row `csrf_rejected`. A client that omits Origin is unchanged. There is no per-form synchronizer token. |
| Password recovery mail | PASS | The reset token is single-use, expires, and is captured in the local outbox. The server log records the subject and does not record the address or the link. |
| SMTP delivery | NOT VERIFIED | SMTP was not configured and no message was sent to a mail server. |
| Public retrieval safety | PASS | Mocked tests cover the BLS QCEW and Federal Register allowlists, a rejected redirect, a body over the cap, a timeout, a private address, and the source and account budgets. |
| Historical live public requests | PASS, not repeated | One BLS QCEW request and one Federal Register request succeeded in earlier milestones. This pass did not send another live request. |
| Account usage meters | PASS | Adviser replies and public retrievals are counted on the account. A new session did not reset the adviser quota. A second research project did not reset the retrieval quota. The default retrieval quota is the existing account batch limit of 8. The default adviser quota is 40. |
| Simulated plans | PASS | With `RUGD_BILLING_SIMULATION` unset, a signed event is stored and access stays the included local pilot. With simulation on, upgrade, downgrade, cancel, and renew apply in order. A repeated event id does not apply twice. An older sequence is stored and not applied. A card field is rejected and not stored. A simulated plan is not a paid subscription. `app/future.py` billing stays disabled and creates no charge. |
| Financial baseline | PASS | `intake/samples/rugd_intelligence.json` SHA256 is `e7b3daafec3b63d3e45dd1d208a8b5c7b6d890a478b67f6e8ed579c3ea250a43`. `reports/output/rugd-intelligence-draft.md` remains do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, internal readiness, and `human_review_approved` false. `engine/`, `scoring/`, `run_assessment.py`, and those two files have no diff since `53a682c`. |
| Authenticated browser, sessions | PASS | On a temporary database, a local customer registered, reached "Your assessments", logged out to "Welcome to RUGD Intelligence", and logged in again. |
| Authenticated browser, usage | PASS | A second temporary account opened Usage. The page showed "Included local pilot", "not a paid subscription", "0 of 40" adviser replies, "0 of 8" public retrievals, and no billing events. The signed-in home still explained `INSUFFICIENT_DEMAND_EVIDENCE`, internal investor readiness, and do-not-proceed. The temporary database was deleted. The real `data/analyze.sqlite` has no cycle 3 account. |
| Full workflow browser walk this cycle | NOT VERIFIED | Explore, Research, Analyze, Business plan, Pitch deck, Reports, Action Center, Adviser, and Market Pulse were not clicked again in this cycle. That walk passed in the earlier 199-test readiness note. Export behavior in this cycle is covered by the unittest suite. |
| Dependency inventory | PASS | `requirements.txt` still lists `python-pptx==1.0.2` and `fpdf2==2.9.0`. No package was added in this cycle. |
| Vulnerability database | NOT VERIFIED | No advisory feed or `pip-audit` run was performed. |
| Repository hygiene | PASS | `.gitignore` ignores `.env` and `data/`. Those paths are not in the cycle 3 commits. No API key or card number was added. |
| Render runtime | NOT VERIFIED | The service was not deployed. The live health check, the persistent disk, and the dashboard environment were not observed. |
| Render Auto-Deploy | NOT APPLICABLE | This cycle did not change Auto-Deploy. The dashboard switch was not read. |
| Load | NOT VERIFIED | No load test was run. The concurrent-write test is one process and a handful of threads, not a load test. |
| External penetration test | NOT VERIFIED | The security evidence is the local suite and the two temporary-account browser walks. |

## Rollback

See `DEPLOYMENT.md`. A later owner rollback is a manual Render deploy of an earlier commit. Do not force-push. A code deploy does not restore the SQLite file. The new `account_entitlements`, `usage_meters`, and `billing_events` tables are created with `CREATE TABLE IF NOT EXISTS` and do not delete existing rows.

## Known limitations

- Ten unclosed-socket ResourceWarnings remain in a full unittest run.
- A POST that omits Origin is not rejected by the foreign-origin check. The session cookie stays HttpOnly and SameSite=Lax.
- Local email and password accounts are the pilot sign-in. There is no paid identity provider.
- Production billing is off. A simulated plan is not a paid entitlement. Prices and a payment provider are not chosen.
- One SQLite file supports one application process.
- A proposed Federal Register rule or a notice is not an enacted requirement. A retrieved record does not clear `INSUFFICIENT_DEMAND_EVIDENCE`.
- The adviser does not call a paid model unless a server-side key is configured. Live provider connectivity was not checked again.
- SMTP was not configured. Reset and verification links stay in the local capture.

## Unresolved issues

| Severity | Evidence | Consequence | Corrective action |
| --- | --- | --- | --- |
| Medium | Ten ResourceWarnings in the 223-test run | A long process can keep client socket descriptors until garbage collection | Keep tracing the remaining client sockets. Do not describe the warnings as cleared. |
| Medium | No vulnerability database query | A pinned export library could have an advisory this pass did not see | Run an approved advisory check before an owner deploy. |
| Medium | Foreign-origin check ignores a missing Origin | A non-browser client can POST without that check. Browsers send Origin on cross-site form posts, and SameSite=Lax still applies | Keep the check. A synchronizer token is a later decision. |
| High, if a second process is started | Documented SQLite limit. Not exercised | A second process can fail a write or read a stale page | Keep Render at one instance. A different database engine needs an owner decision. |
