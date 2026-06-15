---
name: section-research
description: Find recent articles for one newsletter section and format them as cited summaries.
---

## Purpose

Research one newsletter beat, find the strongest recent articles, and output them as ready-to-use cited summaries.

## Input

- Your section name and editorial focus (given in your instructions).
- The subject brief: Subject, Locale, Key players, Themes.

## Search instructions

1. Build simple queries: the subject's short common name on its own first, then add at most one topic word to narrow if needed. Never use long multi-keyword queries, `site:` operators, or mixed-language queries — they return nothing.
2. Call `search` with kind="news" first; use kind="web" only for background. Always pass the `gl` and `hl` codes from the brief's Locale line. Searches default to the past week; widen to recency="month" if results are thin, narrow to recency="day" for breaking news.
3. Keep the subject the lead: most items should be about it. You may cover named competitors and industry context secondarily, but only from the subject's home market.
4. Select the strongest, most relevant recent items — at least 2, at most 5. Prefer substantive developments: products, strategy, expansion, deals, regulation, technology, operations, leadership. Skip stock-index roundups (IHSG levels), "top gainers/losers", analyst price targets, and technical analysis unless a price move is itself the news. Never invent an article or URL.

## Output format

Each item is exactly three parts, in this order:

```
<single-sentence summary in English>
[Read: <article title in English>](<url>)
---
```

Translate non-English headlines into English. Output only the items — no section heading, no preamble.

## Writing each summary

One short sentence (about 30 words max) a person would actually say out loud.

- Vary how entries open — lead with the news, the deal, the partner, a product, or a number.
- When the subject is obviously the actor, "the company" or "it" works as a back-reference; not every entry needs to repeat the name.
- When you do name the subject, use the exact name from the brief's `Subject:` line — never the ticker or the legal PT/Tbk form.
- State the concrete fact, then stop. Cut hedging purpose clauses ("to strengthen its position", "to enhance shareholder value") unless the purpose is the actual news.

Good:
```
Gojek and Grab cut driver commissions to 8 percent under a new government cap.
[Read: Gojek, Grab Slash Driver Fees After Government Cap](https://example.com)
---
A Rp 3.5 trillion buyback follows GoTo's removal from the FTSE and MSCI indices.
[Read: GoTo Launches Share Buyback After Index Removal](https://example.com)
---
```

Avoid:
```
GoTo Group and rival Grab slashed driver commission fees to 8% to comply with new government mandates while seeking to sustain profitability through broader digital ecosystem services.
```

## House style

Write everything in English — translate Indonesian headlines and key points. Write like a human journalist: plain, direct, specific. No marketing hype, no generic AI phrasing ("delves into", "in today's fast-paced landscape", "stands out"). No em-dashes, no semicolons. Lead with real developments, not share prices or analyst targets.
