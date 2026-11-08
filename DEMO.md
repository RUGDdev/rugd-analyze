# Show the RUGD Analyze 0.2 platform

This script uses the seeded hypothetical restaurant drafts. They are not real assessments. Only the RUGD Intelligence assessment is the official baseline.

Start the app from `c:\Projects\RUGD`:

```text
"C:\Users\Blaze\AppData\Local\Programs\Python\Python312\python.exe" -m app
```

Open `http://127.0.0.1:8765`. Press Ctrl+C in that terminal when the demonstration is finished.

## 1. Dashboard

On the customer dashboard, point out two different cards:

- **RUGD Intelligence** is labeled Official baseline. It stays do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE`, investor readiness internal, and human review pending.
- **Hypothetical Restaurant Startup** is labeled “Hypothetical demonstration — not a real assessment.”

Bunny Hive and Small Town Pub, if started, are empty named-pilot drafts. They are not the baseline.

## 2. Unanswered restaurant draft

Open **Hypothetical Restaurant Startup** (Continue), or go to `/assessments/hypothetical-restaurant`.

The intake is labeled “Hypothetical demonstration — not a real assessment.” Seats, ticket, occupancy, and the cost build are filled with invented figures. The customer demand question is blank. Those figures are not verified market research.

Choose **Run Analyze**.

The results page repeats the hypothetical label. It shows do-not-proceed, `INSUFFICIENT_DEMAND_EVIDENCE` present, investor readiness internal, and human review pending. Sources and uses, base and downside, and DSCR come from the 0.1 engine. The page does not mark the draft investor-ready.

Open the report and the HTML audit from the results page. They show the same status.

## 3. Verified-demand variant

From the unanswered draft, open **Open the verified-demand demonstration**, or go to `/assessments/hypothetical-restaurant-verified-demand`.

This second draft uses the same hypothetical operating figures. It is not marked as a hypothetical engine record, because a hypothetical demonstration does not apply a verified demand record. The verified record is boolean `demand_evidence` true, source `verified`, with a rationale. The customer yes/no question stays blank.

Choose **Run Analyze**.

`INSUFFICIENT_DEMAND_EVIDENCE` is not present. The draft stays unapproved. Investor readiness is not investor-ready. Clearing the flag does not make the result final.

## 4. What not to claim

Do not describe either restaurant draft as a real assessment or as the official baseline. Do not use Validate to approve. A customer post that includes `human_review_approved` returns 403. Market Intelligence and Partner remain demonstrations. Reviewer sign-in is prototype-grade.

Stop the server with Ctrl+C.
