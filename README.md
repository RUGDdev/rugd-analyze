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

With `RUGD_ENV` unset, the server binds to 127.0.0.1 only and prints:

```text
RUGD Analyze is running at http://127.0.0.1:8765
Press Ctrl+C to stop. This server is local only.
```

Open `http://127.0.0.1:8765` in a browser.

## How to create a reviewer account

Self-registration on Register creates a customer account. It cannot create a reviewer, and it cannot change a customer into a reviewer.

The first reviewer is created from the environment of the terminal that starts the app, and only when no reviewer account exists yet:

```text
$env:RUGD_BOOTSTRAP_REVIEWER_EMAIL = "reviewer@example.com"
$env:RUGD_BOOTSTRAP_REVIEWER_PASSWORD = "a-password-at-least-8"
"C:\Users\Blaze\AppData\Local\Programs\Python\Python312\python.exe" -m app
```

The password is stored as a scrypt hash. It is not written into the repository. After the reviewer can log in, unset both variables. Starting the app again with the variables set does not create a second reviewer and does not change an existing account.

A signed-in reviewer can open `/reviewer/accounts` and create another reviewer. A customer account and a signed-out request are refused. Creating a reviewer does not approve an assessment or set `human_review_approved`.

A new account can log in before the email is verified. The pages show a banner until the verification link is opened. That link expires in 24 hours. Forgot password, on the login page, emails a reset link that expires in one hour and works once. Neither link changes a role.

Leave `SMTP_HOST` unset and the running server prints the message, including the link, to its log. To send through an SMTP server later, set `SMTP_HOST`. Optional values are `SMTP_PORT` (587), `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and `SMTP_USE_TLS` (`true` by default). Set `RUGD_PUBLIC_URL` to the public base of the link, such as `https://app.rugdintelligence.com` on Render. The message does not include the password.

To walk through the hypothetical restaurant drafts, follow `DEMO.md`.

## How to stop the server

In the same terminal that launched it, press Ctrl+C. The process prints `Stopped.` and releases port 8765. Do not leave a server running after a work session.

## How to run tests

From `c:\Projects\RUGD`:

```text
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m unittest discover -s tests
```

The suite must stay green. Tests do not need the browser server.

## Production (Render)

The pilot host is `app.rugdintelligence.com`. Steps, DNS, and the one-instance SQLite disk are in `DEPLOYMENT.md`. The app reads environment variables. It does not load a `.env` file. Local `.env` files stay gitignored.

Set these in the Render dashboard:

- `RUGD_ENV=production`
- `SECRET_KEY` — at least 32 characters, generated in Render, never committed
- `RUGD_DATABASE=/var/data/analyze.sqlite`
- `RUGD_BOOTSTRAP_REVIEWER_EMAIL`
- `RUGD_BOOTSTRAP_REVIEWER_PASSWORD`

`SECURE_COOKIES=true` is also set in `render.yaml`. Production mode already marks the session cookie Secure, HttpOnly, and SameSite=Lax. Render sets `PORT`. Do not override it.

Optional variables, left unset unless that provider is wanted: `ANALYST_PROVIDER`, `ANALYST_MODEL`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `XAI_API_KEY`, `MARKET_PROVIDER`, `MARKET_CENSUS`, `MARKET_CBP`, `MARKET_BEA`, `BEA_USER_ID`, `MARKET_LAUS`, `MARKET_YEAR`, `ACS_YEAR`, `CBP_YEAR`, `BEA_YEAR`, `LAUS_YEAR`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS`, `RUGD_PUBLIC_URL`.

The start command is `python -m app`. Responses send `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and `Referrer-Policy: same-origin`. Render terminates HTTPS. Add a CNAME for `app.rugdintelligence.com` to the Render hostname. The apex domain stays on the public website.

This build stays pilot-grade. Prototype warnings stay. There is no rate limit and no public self-service billing. Email verification and password reset use the local account. Without `SMTP_HOST`, the message is written to the server log. Clear the bootstrap password in the dashboard after the first reviewer can log in.

## Official baseline

Only the RUGD Intelligence assessment is the official baseline (`intake/samples/rugd_intelligence.json`, app id `rugd-intelligence-baseline`). It remains a draft do-not-proceed, blocking flag `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and `human_review_approved` false.

Bunny Hive and Small Town Pub are empty named-pilot drafts. They are not completed assessments, and their names are not inputs to the scoring engine.

## What is implemented

- Explore intake, save, and resume for local drafts
- Analyze through the unchanged 0.1 engine
- Dashboard history, next-step guidance, results tables, Markdown reports, JSON audit, and a read-only HTML audit page
- A separate verified demand record that follows the documented 0.1 clear rule
- Local email and password accounts. Self-registration creates a customer. Reviewer accounts are created by the bootstrap variables or by an existing reviewer. Approval requires a signed-in reviewer, records that email, and does not clear a flag.
- Local JSON export of one saved assessment, and one file for every non-baseline draft

## Export saved assessments

On the dashboard, **Export all drafts** downloads `rugd-drafts-YYYY-MM-DD.json`. That file contains every saved assessment except the official RUGD Intelligence baseline. Each draft includes the saved profile, the engine intake when Analyze has been run, and the latest engine result when one is stored.

**Export draft as JSON** on an assessment does the same for that one record. The official baseline can be exported by itself. It is not included in the all-drafts file.

Export does not run the engine and does not fill blank fields. It does not include reviewer session tokens, passphrases, or cookies. Drafts stay in gitignored `data/analyze.sqlite`. The export file is a copy for local backup.

## Research package

On a results page, **Download Research Package** saves `name-date-research.json`. The file contains the assessment summary, the stored engine result, market observations with source, coverage, period, retrieval date, and limitations, evidence gaps and flags, the analyst explanation, and the tier and prototype disclaimers. **Download research Markdown** saves the same package as Markdown. **Research Brief** opens a print-friendly HTML view with those citations and a limitations section.

The package uses the stored engine result. It does not run the engine, fill blank fields, clear a flag, or set `human_review_approved`. Session tokens, passphrases, and cookies are omitted. With no market provider configured, the market section is the labeled synthetic snapshot. With no analyst provider configured, the explanation is the Demonstration Analyst.

## Demonstration only or unfinished

- Validate can request review, shows a prototype Review Package, and cannot approve
- Partner monitoring is not active. The Ongoing Intelligence panel is an inactive demonstration
- Market Intelligence stays on a labeled synthetic snapshot unless `MARKET_PROVIDER=bls`, `MARKET_CENSUS=acs`, `MARKET_CBP=cbp`, `MARKET_BEA=bea`, or `MARKET_LAUS=laus` is set
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
- `MARKET_CBP=cbp` (`census-cbp` and `patterns` are accepted)
- `CBP_YEAR` — optional County Business Patterns release. The default is `2023`
- `MARKET_BEA=bea` (`regional` and `bea-regional` are accepted)
- `BEA_YEAR` — optional Regional Economic Accounts year. The default is `2024`
- `BEA_USER_ID` — free BEA API user id. A BEA request without it falls back to the synthetic snapshot. The page does not show the id
- `MARKET_LAUS=laus` (`bls-laus` and `unemployment` are accepted)
- `LAUS_YEAR` — optional unemployment annual average. The default is `2024`

No Census API key is used. Set any of the provider variables, or all of them. They appear together on the same page. If one request fails, only that part returns to the synthetic snapshot.

Open Market Intelligence and choose a geography of United States, Alabama, Colbert County, Alabama, Tennessee, Hamilton County, Tennessee, Georgia, or Fulton County, Georgia. Industries are Restaurant (NAICS 722), Professional services (54), Retail (44-45), Construction (23), Manufacturing (31-33), Accommodation (721), and Health care (62). The page requests the BLS Quarterly Census of Employment and Wages annual file and shows private employment, average weekly wage, establishments, total annual wages, average annual pay, and establishment size coverage when those cells are published. When the file includes an over-the-year percent change, that percent is an extended metric. The page names the active provider and year.

The Census ACS extract is total population from table B01003 and median household income from table B19013. It is a 5-year residence estimate, not an industry and not business revenue. When the prior vintage is available, the page can also show the difference between the two overlapping 5-year population estimates, and a household-income bracket note from table B19001. Those two items are extended metrics. County Business Patterns adds establishments, employment, and annual payroll in thousands of dollars. A NAICS code in the sector table is read from that table. Restaurant (722) and Accommodation (721) are requested from the Census CBP API filtered to that NAICS code, with no API key. If that request fails, only that part falls back. BEA Regional Economic Accounts adds current-dollar GDP for all industries (CAGDP2 line 1) and personal income (CAINC1 line 1), both in thousands of dollars, for a mapped geography. The BEA request needs `BEA_USER_ID`. Local Area Unemployment Statistics adds the unemployment rate and the labor force for a mapped state or county. The annual average is BLS period M13. The United States row uses the Current Population Survey national series because LAUS is a local-area program. No BLS API key is sent. The page names each active provider and its year. `MARKET_YEAR`, `ACS_YEAR`, `CBP_YEAR`, `BEA_YEAR`, and `LAUS_YEAR` are read from the environment. The page does not offer another year control. When a variable is unset, QCEW, ACS, BEA, and LAUS use 2024 and County Business Patterns uses 2023.

The market view control does not change an assessment. Explore shows the headline snapshot. Analyze adds the full current view and a Market Research Summary. Validate and Partner add the extended metrics. The summary says it is derived from the cited public sources and that it is not a recommendation. Opening the page without a view selected uses Explore.

The page includes a combined summary of the figures for the current industry and geography, with the source and period beside each one, and the active provider and year. **Download market observations (JSON)** saves the observations for the selected view, including a synthetic snapshot when that is what the page is showing. The file does not include an assessment, a session token, or a passphrase. A suppressed cell is labeled not disclosed. If a selection is outside a provider’s map, or that provider’s request fails, that part returns to the labeled synthetic snapshot. The Partner screen does not call these providers, and recurring monitoring stays off. The figures do not clear `INSUFFICIENT_DEMAND_EVIDENCE` or any other flag, and they do not change investor readiness. This is not a live feed and monitoring is not active.

- Bunny Hive and Small Town Pub have no completed assessments
- Local accounts are pilot-grade: scrypt password hashes, no OAuth, and no external identity provider. The session cookie is marked Secure when `RUGD_ENV=production` or `SECURE_COOKIES=true`. On local HTTP it is not marked Secure
- No billing, live market feed, or investor matchmaking. Render files for `app.rugdintelligence.com` are prepared and the service stays pilot-grade. The optional BLS extract above is an annual file, not a live feed
- React remains deferred

To resume after an owner decision, read `HANDOFF.md`. Disabled seams for authentication, scoring, deployment, and billing live in `app/future.py` and stay off until `DECISIONS.md` records the owner input.
