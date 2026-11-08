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
- Local JSON export of one saved assessment, and one file for every non-baseline draft

## Export saved assessments

On the dashboard, **Export all drafts** downloads `rugd-drafts-YYYY-MM-DD.json`. That file contains every saved assessment except the official RUGD Intelligence baseline. Each draft includes the saved profile, the engine intake when Analyze has been run, and the latest engine result when one is stored.

**Export draft as JSON** on an assessment does the same for that one record. The official baseline can be exported by itself. It is not included in the all-drafts file.

Export does not run the engine and does not fill blank fields. It does not include reviewer session tokens, passphrases, or cookies. Drafts stay in gitignored `data/analyze.sqlite`. The export file is a copy for local backup.

## Demonstration only or unfinished

- Validate can request review and cannot approve
- Partner monitoring is not active
- Market Intelligence stays on a labeled synthetic snapshot unless `MARKET_PROVIDER=bls` or `MARKET_CENSUS=acs` is set
- The Demonstration Analyst is the default. An optional external analyst can be enabled with an environment variable and an API key

## Optional external analyst

The analyst is off the network unless you set a provider. With no provider, or with a missing key, or when a call fails, the app uses the labeled Demonstration Analyst. That explanation cannot change engine numbers, clear flags, set `human_review_approved`, or change investor readiness.

Set these in the environment for the terminal that starts the app. Do not put keys in source files.

- `ANALYST_PROVIDER` — `claude`, `openai`, or `grok` (`anthropic`, `chatgpt`, and `xai` are accepted aliases)
- `ANTHROPIC_API_KEY` — required when the provider is Claude
- `OPENAI_API_KEY` — required when the provider is OpenAI
- `XAI_API_KEY` — required when the provider is Grok
- `ANALYST_MODEL` — optional model name. Defaults are `claude-sonnet-4-5`, `gpt-4.1-mini`, and `grok-3`

The provider receives a summary of the current assessment and the engine result, plus a system instruction that forbids changing numbers, clearing flags, or approving the assessment. It does not receive session tokens or the API key in the prompt. This is still prototype-grade. It is not production authentication and it is not a decision.

## Optional public market data

With no market setting, Market Intelligence and Partner show the synthetic snapshot. Examples stay marked “Synthetic example only.” Nothing on that page is a Census, BLS, or BEA feed.

To request one public extract, set this in the terminal that starts the app. No API key is used.

- `MARKET_PROVIDER=bls` (`qcew` and `bls-qcew` are accepted)
- `MARKET_YEAR` — optional QCEW annual file. The default is `2024`
- `MARKET_CENSUS=acs` (`census` and `census-acs` are accepted)
- `ACS_YEAR` — optional ACS 5-year vintage. The default is `2024`

No Census API key is used. Set either variable, or both. Both together show QCEW and ACS on the same page. If one request fails, only that part returns to the synthetic snapshot.

Open Market Intelligence and choose a geography of United States, Alabama, Colbert County, Alabama, Tennessee, or Hamilton County, Tennessee. Industries are Restaurant (NAICS 722), Professional services (54), Retail (44-45), Construction (23), Manufacturing (31-33), Accommodation (721), and Health care (62). The page requests the BLS Quarterly Census of Employment and Wages annual file and shows private employment, average weekly wage, establishments, total annual wages, average annual pay, and establishment size coverage when those cells are published. The page names the active provider and year.

The Census extract is total population from table B01003 and median household income from table B19013. It is a 5-year residence estimate, not an industry and not business revenue. The page names each active provider and its year. `MARKET_YEAR` and `ACS_YEAR` are read from the environment. The page does not offer another year control. When either variable is unset, that provider uses 2024.

Each figure is shown with its source, geographic coverage, classification, measurement period, retrieval date, and limitations. A suppressed cell is labeled not disclosed. If a selection is outside a provider’s map, or that provider’s request fails, that part returns to the labeled synthetic snapshot. Partner does not call these providers. The figures do not clear `INSUFFICIENT_DEMAND_EVIDENCE` or any other flag, and they do not change investor readiness. This is not a live feed and monitoring is not active.
- Bunny Hive and Small Town Pub have no completed assessments
- Reviewer sign-in is prototype-grade: one source-constant passphrase, no OAuth, no password hash, and no account directory
- No production accounts, billing, public deployment, live market feed, or investor matchmaking. The optional BLS extract above is an annual file, not a live feed
- React remains deferred
