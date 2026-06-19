---
name: subject-profile
description: Resolve a subject (ticker, company, or industry) into a compact research brief.
---

## Purpose

Turn a raw subject — a stock ticker, company name, or industry theme — into a structured brief that every other agent uses as ground truth for the edition.

## Input

The subject string the user provided. If verified exchange listing details are already injected into your instructions, treat them as ground truth and skip the confirmation search.

## Instructions

1. If the subject is not obvious and no verified listing details are provided, call `web_search` (kind="web" or kind="news", recency="") to confirm what it is.
2. Output a compact brief using exactly the labelled lines in the Output section below — nothing else.

## Output

```
Subject: <common English name — no PT prefix or Tbk suffix for Indonesian companies>
Type: <ticker | company | industry>
Ticker/Exchange: <SYMBOL:EXCHANGE or n/a>
Sector: <industry>
Market: <home country or region>
Locale: <Serper codes, e.g. gl=id, hl=id for Indonesia>
Key players: <3–6 named companies — rivals if a company, leaders if an industry>
Themes: <3–5 topics currently in the subject's news>
```

The `Subject:` value is the canonical name used to refer to the subject throughout the entire edition. All other agents read it from this brief.
