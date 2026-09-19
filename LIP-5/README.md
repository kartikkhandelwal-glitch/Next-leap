# Groww Review Pulse — LIP 5

A small, rerunnable pipeline for turning public App Store + Play Store reviews into a weekly one-page product pulse.

## Product carried forward
**Groww**, selected in LIP 4. The previous repository confirms Groww was the chosen product.

## Flow
`CSV import → PII-safe cleaning → theme grouping (max 5) → quote selection → action ideas → weekly note → email draft`

## Demo status
The included `data/reviews_demo.csv` is a **demo/sample corpus**. It contains 3 reviews copied from the public Groww Google Play listing and redacted synthetic rows for testing the 8–12 week workflow. It intentionally contains no usernames, emails or IDs.

Before an operational run, replace the CSV with a public review export containing:
`source,date,rating,title,text`

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

Upload a CSV, choose the week, and click **Generate pulse**. The app outputs the top 3 themes, 3 quotes and 3 action ideas. The fallback classifier is deterministic so the demo works without an API key.

## LLM prompt
The app includes a prompt template for an LLM stage. The model is instructed to:
- use only supplied review text;
- assign exactly one of five themes;
- keep quotes verbatim except PII redaction;
- never invent counts or quotes;
- produce ≤250 words;
- return exactly 3 action hypotheses.

## PII rules
Never persist author names, usernames, emails, phone numbers, account IDs, ticket IDs or other reviewer identifiers. Redact PII before storing or sending reviews to an LLM.

## Theme legend

1. Funds, KYC & Account Access — withdrawals, deposits, KYC, login/account access.
2. Orders & Trading — order placement/execution, trading flows and related failures.
3. App Experience & Reliability — crashes, freezes, speed, navigation, UI/update regressions.
4. Support & Communications — support/tickets and outbound notifications/messages.
5. Product Requests — explicit requests for new/customizable product capabilities.

## Re-run for a new week
1. Export the latest public reviews.
2. Replace `data/reviews_demo.csv`.
3. Run the app and select the new week.
4. Review the three quotes for PII.
5. Export/copy the generated note into the weekly email draft.

## Important sourcing note
The demo does not scrape behind logins. Use public review exports/feeds that your source permits. Store only the fields needed for analysis.
