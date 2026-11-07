# Decisions

## 2026-11-07 — RUGD Analyze 0.2 stays inside this repository

RUGD Analyze 0.2 is a local browser application in `c:\Projects\RUGD`. It is not a new repository. Longarc_Platform and the Webflow site stay untouched.

## 2026-11-07 — One platform, four service tiers

Explore, Analyze, Validate, and Partner are service levels in one application. Service tier, draft recommendation, evidence status, human-review approval, and investor readiness are separate fields. Changing tier does not change a recommendation.

## 2026-11-07 — Python shell around the 0.1 engine

The customer application calls the existing Python engine. It does not rewrite calculations in another language. The first interface is local HTML served by Python on 127.0.0.1. React is deferred until this journey is stable. Drafts are stored in local SQLite under `data/`, which is gitignored.

## 2026-11-07 — No customer approval control

Version 0.2 has no accounts and no payment processing. The Validate screen can record a review request. It cannot set `human_review_approved`. Investor summaries remain behind the existing gate.

## 2026-11-07 — Market intelligence is labeled hypothetical

Version 0.2 does not call Census, BLS, BEA, or any paid data API. Market pages state that their examples are hypothetical.

## 2026-11-07 — Git author identity was not set

`git init` created this repository and the 0.1 files were staged. The checkpoint commit did not run because Git has no author name or email. Git configuration was not changed.
