# Disclaimer snippet

The line shown in the UI header and appended to every single reply:

> **Facts-only. No investment advice.**

## Where it appears

| Surface | Placement |
|---|---|
| Web UI header | Pill badge under the welcome line |
| Web UI, every answer card | Footer line, next to "Last updated from sources" |
| `/api/ask` JSON | `disclaimer` field on every response |
| CLI | Welcome banner, and rendered with every answer |

## Full text used in the UI footer

> Scope: Groww Mutual Fund (Groww Asset Management Ltd.) — Groww Large Cap Fund, Groww Value
> Fund, Groww ELSS Tax Saver Fund, Groww Nifty Total Market Index Fund. 25 official sources
> (AMC / SEBI / AMFI / RTA). No PII is accepted or stored. No performance figures are computed.

## Refusal wording

**Opinion / portfolio questions**

> I can only share published facts, so I can't tell you whether to buy, sell, hold or switch —
> that call depends on your own goals and is one for a SEBI-registered investment adviser.
> I'm happy to give you the scheme's exit load, minimum SIP, benchmark, riskometer or lock-in
> instead.

Paired with an educational link: [SEBI Investor — Understanding the Riskometer](https://investor.sebi.gov.in/riskometer.html),
or [SEBI Investor — A Guide to ELSS](https://investor.sebi.gov.in/elss.html) when the question is about the ELSS scheme.

**Performance questions**

> I don't compute or compare returns, and I don't make performance claims. Groww Mutual Fund
> publishes disclosed performance for every scheme in its monthly factsheet, linked below.
> Ask me a scheme fact — exit load, minimum SIP, benchmark, riskometer or lock-in — and I'll
> answer that.

Paired with: [Groww Mutual Fund — Monthly Factsheets](https://www.growwmf.in/downloads/fact-sheet)

**Personal or account data**

> I can't accept personal or account details, so I've discarded what you sent and detected
> \<type\> in it. Ask me about a scheme's published facts instead — for example "What is the
> exit load of Groww Value Fund?" For anything tied to your own folio, use the official
> investor channels.

Paired with: [MF Central](https://www.mfcentral.com/)
