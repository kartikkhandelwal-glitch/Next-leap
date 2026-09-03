# Next Leap — LIP submissions

## Product choice: **Groww**

Chosen for this milestone and carried forward to the next LIP challenge.

## Milestone: Mutual Fund FAQs (Facts-Only Q&A)

→ **[`mf_faq/`](mf_faq/README.md)**

A retrieval-grounded FAQ assistant over 25 official pages from Groww Mutual Fund, SEBI, AMFI and
the SEBI-registered registrars. Answers published facts about four Groww Mutual Fund schemes —
exit load, minimum SIP, benchmark, riskometer, ELSS lock-in, expense ratio, statement downloads
— with one source link on every answer. Refuses advice, performance and PII questions.

| Deliverable | Where |
|---|---|
| Working prototype (hosted) | **[https://claude.ai/code/artifact/07fdc155-2183-4cd3-a28b-fdd8f32a6fb5](https://claude.ai/code/artifact/07fdc155-2183-4cd3-a28b-fdd8f32a6fb5)** — runs entirely in the browser |
| Prototype source | [`mf_faq/`](mf_faq/README.md) — `python3 -m app.server`, no dependencies |
| Source list (CSV + MD) | [`mf_faq/data/sources.csv`](mf_faq/data/sources.csv) · [`mf_faq/data/sources.md`](mf_faq/data/sources.md) |
| README (setup, scope, known limits) | [`mf_faq/README.md`](mf_faq/README.md) |
| Sample Q&A | [`mf_faq/data/sample_qa.md`](mf_faq/data/sample_qa.md) |
| Disclaimer snippet | [`mf_faq/DISCLAIMER.md`](mf_faq/DISCLAIMER.md) |

```bash
cd mf_faq
python3 -m app.server                      # http://127.0.0.1:8000
python3 -m unittest discover -s tests -v   # 26 tests
python3 tools/parity_check.py              # hosted build vs. Python engine
```

**Facts-only. No investment advice.**
