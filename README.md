# RUGD Intelligence MVP

Pilot project. Every Cursor/Claude session must begin by reading all files in the `/docs` folder, plus `AGENTS.md`, `CURRENT_STATUS.md`, and `DECISIONS.md`.

Work only in `c:\Projects\RUGD`. Do not open or change Longarc_Platform or the Webflow site.

## How to run a 0.1 assessment

From any directory:

```text
"C:\Users\Blaze\AppData\Local\Programs\Python\Python312\python.exe" "C:\Projects\RUGD\run_assessment.py"
```

That command uses the 0.1 engine and the official sample. It does not start the browser app.

## How to start RUGD Analyze 0.2

Open a terminal in `c:\Projects\RUGD` and run:

```text
"C:\Users\Blaze\AppData\Local\Programs\Python\Python312\python.exe" -m app
```

The `python` command on this PC is the Windows Store stub. Use the Python 3.12 path above.

The server binds to 127.0.0.1 only and prints:

```text
RUGD Analyze is running at http://127.0.0.1:8765
Press Ctrl+C to stop. This server is local only.
```

Open `http://127.0.0.1:8765` in a browser.

To walk through the hypothetical restaurant drafts, follow `DEMO.md`.

## How to stop the server

In the same terminal that launched it, press Ctrl+C. The process prints `Stopped.` and releases port 8765. Do not leave a server running after a work session.

## How to run tests

From `c:\Projects\RUGD`:

```text
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m unittest discover -s tests
```

The suite must stay green. Tests do not need the browser server.

## Official baseline

Only the RUGD Intelligence assessment is the official baseline (`intake/samples/rugd_intelligence.json`, app id `rugd-intelligence-baseline`). It remains a draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

Bunny Hive and Small Town Pub are empty named-pilot drafts. They are not completed assessments, and their names are not inputs to the scoring engine.

## What is implemented

- Explore intake, save, and resume for local drafts
- Analyze through the unchanged 0.1 engine
- Dashboard history, next-step guidance, results tables, Markdown reports, JSON audit, and a read-only HTML audit page
- A separate verified demand record that follows the documented 0.1 clear rule
- Prototype reviewer sign-in, a 4-hour session, sign-out, and a local audit trail

## Demonstration only or unfinished

- Validate can request review and cannot approve
- Partner monitoring is not active
- Market Intelligence is a synthetic demonstration, not Census, BLS, or BEA research
- The Demonstration Analyst has no external AI service
- Bunny Hive and Small Town Pub have no completed assessments
- Reviewer sign-in is prototype-grade: one source-constant passphrase, no OAuth, no password hash, and no account directory
- No production accounts, billing, public deployment, live market data, or investor matchmaking
- React remains deferred
