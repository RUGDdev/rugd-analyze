# RUGD Intelligence local pilot

This guide is for the owner running the pilot on this computer. It does not deploy the application, and it does not start a subscription.

The local pilot does not ask for a payment method. Registration creates a customer account. It does not create a reviewer, and it does not grant investor-ready status.

## Start the application

Open a terminal in `c:\Projects\RUGD` and run:

```text
"C:\Users\Blaze\AppData\Local\Programs\Python\Python312\python.exe" -m app
```

Leave `RUGD_ENV` unset. The server binds to `127.0.0.1:8765` and prints that address. Open `http://127.0.0.1:8765`.

Stop it with Ctrl+C in that same terminal. Do not leave it running after the session.

The `python` command on this PC is the Windows Store stub. Use the Python 3.12 path above.

Drafts are stored in gitignored `data/analyze.sqlite`. That file is the local pilot database. It is not the Render disk. Do not copy a test database over it.

## Sign in

Choose Register. Enter an email and a password of at least 8 characters. The password is stored as a scrypt hash.

You can sign in before the email is verified. The pages show a banner until the verification link is opened. With `SMTP_HOST` unset, the server records the mail subject and does not write the address or the link in the log. A local test capture holds the link. Forgot password, on the login page, works the same way. The reset link expires in one hour and works once.

Signing in again replaces older sessions for that account. Log out from the sidebar.

## Create a business

On the signed-in home, choose Start a new assessment.

Say whether this is a startup idea or an existing or expanding business. A startup idea includes the startup cost-build questions. An existing or expanding business skips those questions and still asks for the monthly figures.

Enter the real business name. Leave the business profile on “New business profile” for the first draft. Purpose can stay Startup feasibility. Starting tier can stay Explore.

Create draft. The intake opens blank. Nothing is copied from the official baseline.

Use a new assessment for the real pilot case. Do not type the real case into the official RUGD Intelligence baseline, and do not treat the fictional Harbor Lane Coffee test as that case. Harbor Lane Coffee exists only in the automated test and uses invented figures.

## Enter the case

The workflow links at the top of the assessment are Explore, Research, Analyze, Business plan, Pitch deck, Reports, Action Center, Adviser, and Market Pulse. Opening a link does not change the saved assessment.

On Explore:

1. Describe the business. Industry, stage, customers, and competition stay your assumptions. Example phrases are suggestions. Selecting one does not run the engine.
2. Answer the demand questions if you know them. A yes on “Is there demand evidence?” is still a user-supplied assumption. It does not clear `INSUFFICIENT_DEMAND_EVIDENCE`.
3. For a startup, enter the cost-build figures you know. Occupancy and contribution margin are fractions: `0.60` means 60 percent. Operating days is a count.
4. Enter the four monthly figures: initial capital, monthly fixed costs, gross margin, and projected monthly base revenue. Gross margin is a fraction: `0.55` means 55 percent. A blank stays missing and is not stored as zero. An entered zero is kept as zero.
5. Leave “These monthly figures are measured” unchecked unless the figures come from measured records.
6. Save the draft. The page returns to the same assessment. Reload it to confirm the values are still there.

Change a monthly figure to update the financial preview. The preview is not the official result. Choose Run Analyze to store the engine result.

## What each feature does

**Analyze.** Runs the existing 0.1 engine on the saved inputs. The results page shows the stored recommendation, flags, and charts from that result. A hard recommend-against flag keeps the recommendation at do-not-proceed. The page does not invent a feasibility score.

**Research.** Create a research project on the assessment. You can record evidence you already have. A typed web address is stored as text and is not fetched. Retrieve public information sends one allowlisted BLS or Federal Register request when you choose it. Nothing from that request is saved until you import a row. An imported row is a public source, not verified demand for this business.

**Business plan.** Generate a plan from the saved assessment. Edit the narrative and save. The plan copies stored figures. It does not replace the official result.

**Pitch deck.** Create a deck from a saved plan, then download PowerPoint or PDF from that deck. The deck does not grant investor-ready status.

**Reports.** Generate report saves a snapshot. An older snapshot stays in History.

**Action Center.** Add a follow-up in your own words. Completing an action does not clear a flag.

**Adviser.** Ask a question about the saved assessment. With no adviser provider configured, the reply is deterministic and says that no live model was called. A configured provider is used only when you send a question. The adviser cannot change a number, a flag, or an approval. A plan or deck suggestion is not saved until you approve it.

**Market Pulse.** A labeled demonstration. Monitoring is not active.

## Save and resume

Save draft, Run Analyze, Generate report, and the plan and deck save buttons write to the local database. Sign out, sign in again, and open the assessment from the home list. The saved fields and the stored result are still there.

Another customer account cannot open the assessment by changing the address.

## How to read the result

The recommendation and the flags are the engine’s draft answer from the inputs you entered. Customer-entered values are assumptions, not verified data.

`INSUFFICIENT_DEMAND_EVIDENCE` means the file does not yet have verified demand. A blank demand answer, a customer yes, a market paragraph, or an adviser reply does not clear it.

Investor readiness stays internal until the existing gate and an authorized review are in place. `human_review_approved` stays false. A customer account cannot set it.

A preview, a chart, a plan, and a deck read the stored file. They do not create a second official result.

## Limits

- This is a local pilot. The screens say it is not investor-approved.
- One SQLite file supports one application process. Run one server.
- Leave `RUGD_BILLING_SIMULATION` unset. A simulated plan is not a paid subscription, and this pilot does not charge anyone.
- Do not point a public website at this server. A hosted pilot is a separate owner decision.
- The official sample `intake/samples/rugd_intelligence.json` stays the draft do-not-proceed baseline. The app reads it and does not overwrite it.

## Report a usability problem

Note the page address, what you expected, and what happened. Say whether the draft was saved. Do not send a password, an API key, or a customer list. A later session can reproduce the step on a temporary database.
