#!/usr/bin/env python3
"""Diff the JavaScript engine against the Python one over a question bank.

The hosted single-page build runs web/engine.js, the local server runs app/.
They must answer identically, so this runs both over the same questions and
reports any field that differs. Needs `node` on PATH.

    python3 tools/parity_check.py
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from app.assistant import Assistant  # noqa: E402

QUESTIONS = [
    # facts, one per attribute per scheme
    "What is the exit load of Groww Value Fund?",
    "Exit load for Groww Large Cap Fund",
    "Groww Nifty Total Market Index Fund exit load",
    "Exit load on Groww ELSS Tax Saver Fund",
    "What is the lock-in period for Groww ELSS Tax Saver Fund?",
    "ELSS lock-in?",
    "Minimum SIP for Groww Large Cap Fund",
    "Minimum lumpsum for Groww Value Fund",
    "Minimum investment in Groww ELSS Tax Saver Fund",
    "Minimum SIP Groww Nifty Total Market Index Fund",
    "Benchmark of Groww Large Cap Fund",
    "Benchmark of Groww Value Fund",
    "Benchmark of Groww ELSS Tax Saver Fund",
    "Benchmark of Groww Nifty Total Market Index Fund",
    "Riskometer of Groww Value Fund",
    "Riskometer of Groww Large Cap Fund",
    "What category is Groww Value Fund?",
    # general documents
    "What is a riskometer?",
    "What is the expense ratio of Groww Value Fund?",
    "What is the TER limit for equity schemes?",
    "Where do I find the TER for all schemes?",
    "How do I download my mutual fund capital gains statement?",
    "Where can I get my 80C tax proof?",
    "How do I get a consolidated account statement?",
    "What is MF Central?",
    "Where can I find the latest factsheet?",
    "Where do I find the SID?",
    "What is the latest NAV?",
    "What plans and options are available?",
    "What is ELSS?",
    "Where are the scheme portfolios published?",
    # refusals and edges
    "Should I buy Groww Value Fund?",
    "Is Groww ELSS Tax Saver Fund good for me?",
    "Which is the best Groww fund?",
    "Can you recommend a fund for my portfolio?",
    "Should I sell my Groww Large Cap Fund units?",
    "How much should I invest in ELSS?",
    "Is Groww Value Fund a good choice for me?",
    "What returns did Groww Large Cap Fund give in 3 years?",
    "What is the CAGR of Groww Value Fund?",
    "Compare the performance of Groww Value Fund and Groww Large Cap Fund",
    "How much will I earn from Groww ELSS Tax Saver Fund?",
    "Exit load of SBI Bluechip Fund",
    "What is the lock-in of Axis ELSS Tax Saver Fund?",
    "Parag Parikh Flexi Cap minimum SIP",
    "who is the fund manager of Groww Value Fund",
    "what is the AUM of Groww Value Fund",
    "what is the portfolio turnover of Groww Large Cap Fund",
    "What is the exit load?",
    "My PAN is ABCDE1234F, what is my folio balance?",
    "Aadhaar 2345 6789 0123 exit load please",
    "mail me at investor@example.com",
    "call me on 9876543210",
    "+91 98765 43210",
    "my OTP is 483920",
    "folio number 1234567890 exit load",
    "hi",
    "thanks",
    "",
    "   ",
    "?????",
    "TER slabs start at 2.25% on the first Rs. 500 crore",
]

# Reads the question list on stdin so nothing depends on how `node -e` numbers
# its arguments.
RUNNER = """
const engine = require(process.argv[1]);
const corpus = require(process.argv[2]);
const assistant = engine.create(corpus);
let input = '';
process.stdin.on('data', d => input += d);
process.stdin.on('end', () => {
  console.log(JSON.stringify(JSON.parse(input).map(q => assistant.ask(q))));
});
"""


def main():
    assistant = Assistant()
    python_replies = [assistant.ask(q) for q in QUESTIONS]

    try:
        result = subprocess.run(
            ["node", "-e", RUNNER,
             os.path.join(ROOT, "web", "engine.js"),
             os.path.join(ROOT, "data", "corpus.json")],
            input=json.dumps(QUESTIONS),
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError:
        print("node not found on PATH - install Node to run the parity check.")
        return 2
    except subprocess.CalledProcessError as exc:
        print(exc.stderr)
        return 2

    js_replies = json.loads(result.stdout)

    # source_id is added by the JS build for the UI's reference line; the Python
    # reply does not carry it. Everything else must match exactly.
    compared = ["answer", "intent", "matched", "attribute", "scheme",
                "score", "pii_detected", "out_of_scope",
                "last_updated_from_sources", "disclaimer"]

    mismatches = 0
    for question, py, js in zip(QUESTIONS, python_replies, js_replies):
        problems = []
        for field in compared:
            if py.get(field) != js.get(field):
                problems.append("  %-28s py=%r  js=%r" % (field, py.get(field), js.get(field)))
        for field in ("url", "title", "publisher"):
            if py["citation"][field] != js["citation"][field]:
                problems.append("  citation.%-19s py=%r  js=%r"
                                % (field, py["citation"][field], js["citation"][field]))
        if problems:
            mismatches += 1
            print("MISMATCH  %r" % question)
            print("\n".join(problems))

    print("\n%d/%d questions identical across both engines."
          % (len(QUESTIONS) - mismatches, len(QUESTIONS)))
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
