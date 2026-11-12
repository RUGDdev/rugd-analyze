# Pilot readiness — 2026-11-12

This note records whether the owner can use the local pilot. It does not deploy the service, does not enable Render Auto-Deploy, and does not connect a payment provider.

The official baseline stays draft do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

## Summary

The owner can launch the app on this computer, register without a subscription, create a blank business, enter assumptions, run Analyze, and continue through research, a plan, a deck, reports, actions, and the deterministic adviser. A fictional automated case completed that path, signed out, and resumed. A second account was refused.

A private hosted pilot is not cleared. Render was not deployed.

## Checks

| Workflow | Result | Evidence |
| --- | --- | --- |
| Local start | PASS | `Start-RUGD-Pilot.ps1` started `python -m app` on `data\analyze.sqlite`, printed `http://127.0.0.1:8765`, and the home page returned 200 with “Welcome to RUGD Intelligence”. A second start refused the busy port. After Ctrl+C was not available from the check, the process was stopped. The local database still had the same 6 accounts and 15 assessments. The script creates no account. |
| Registration and sign-in without payment | PASS | The registration page says the local pilot does not ask for a subscription or a payment method. A browser registration reached “Your assessments”. The home repeats that no subscription is required. |
| Included access | PASS | An account with no simulated plan keeps the included local pilot. `RUGD_BILLING_SIMULATION` stays unset. Billing hooks create no charge. |
| Create a business | PASS | The browser created a blank draft named Owner Pilot Case on a temporary database. The automated case created Harbor Lane Coffee the same way. The real `data/analyze.sqlite` was not used for either account. |
| Guided intake | PASS | The blank draft showed the workflow links, the fraction hints (`0.55` means 55 percent, `0.60` means 60 percent), and the line that a blank is not treated as zero. |
| Financial preview and Analyze | PASS | `tests/test_pilot_journey.py` posted fictional monthly assumptions, stored an Analyze result, and the results page showed do-not-proceed and `INSUFFICIENT_DEMAND_EVIDENCE`. The preview control is the existing financial preview. It does not replace that result. |
| Research | PASS | The same test created a research project and reopened the title. It did not call a live public source. |
| Business plan | PASS | The test generated a plan from the saved assessment. |
| Pitch deck and exports | PASS | The test created a deck and downloaded a PowerPoint file beginning `PK` and a PDF beginning `%PDF`. |
| Reports and actions | PASS | The test saved a report containing the business name and an open action in the owner’s words. |
| Adviser with no live model | PASS | The test asked one question. The reply included “Deterministic adviser” and “No live model was called.” |
| Save, sign out, sign in, resume | PASS | After logout the home did not show the business name. Signing in again showed the saved name and the entered revenue. |
| Customer isolation | PASS | A second account received 403 and did not see the business name. |
| CSRF, foreign Origin | PASS | An Origin that names another host is refused and audited as `origin`. |
| CSRF, browser POST without Origin | PASS | A POST that sends `Sec-Fetch-Site` and omits Origin is refused and audited as `fetch`. A non-browser POST that omits both headers is unchanged, which is how the existing test client works. |
| Session security | PASS | Sign-in replaces older sessions. Logout deletes the presented session. An expired session is signed out. Reset links stay out of the server log. |
| Backup and one process | PASS | Temporary-file backup and restore tests pass, including refusal of `data/analyze.sqlite`. One SQLite file supports one application process. A second process was not started. |
| Socket warnings | PASS | `python -m unittest discover -s tests` on 2026-11-12 ran 226 tests, OK, about 52 seconds, and printed no ResourceWarning. Dropping a server without an explicit close no longer leaves the listening socket unclosed. |
| Dependency advisories | PASS | The OSV API, queried for `python-pptx==1.0.2` and `fpdf2==2.9.0`, returned no advisories. No package was added. |
| Official baseline | PASS | The sample SHA256 remains `e7b3daafec3b63d3e45dd1d208a8b5c7b6d890a478b67f6e8ed579c3ea250a43`. The pilot test compared that hash before and after the fictional case. |
| Full workflow click-through in the browser | NOT VERIFIED | The browser walk registered, opened the blank intake, and confirmed the new labels and workflow links. Research, Analyze, the plan, the deck, reports, actions, and the adviser were exercised by the automated journey, not by clicking each control in the browser. |
| Live adviser provider | NOT VERIFIED | No API key was set and no paid model was called. |
| SMTP delivery | NOT VERIFIED | No message was sent to a mail server. |
| Render and a private hosted pilot | NOT VERIFIED | The service was not deployed. Auto-Deploy was not changed. The dashboard environment was not read. |
| Load and a second SQLite process | NOT VERIFIED | Not run. |

## Known limitations

- Fraction fields must be entered as decimals. The labels now say what `0.55` and `0.60` mean. A value such as `55` for gross margin is rejected because the engine accepts `0` through `1`.
- A non-browser client that omits both Origin and `Sec-Fetch-Site` is not blocked by the cross-site check. The session cookie remains HttpOnly and SameSite=Lax.
- The deterministic adviser does not call a model. A live adviser requires a server-side provider and key chosen by the owner.
- Public retrieval is allowlisted and counted on the account. This pilot pass did not send a new live BLS or Federal Register request.
- Market Pulse is a demonstration. Monitoring is not active.
- Validate can record a review request and cannot approve.
- One process per SQLite file.

## Workarounds

- Enter percents as fractions. Use `0.55` for 55 percent.
- Leave a monthly field blank when you do not know it. Do not type `0` unless zero is the assumption.
- Use Start a new assessment for the real case. Leave the official baseline unread as a working file.
- Keep a single `python -m app` process. Stop it with Ctrl+C before starting another.
