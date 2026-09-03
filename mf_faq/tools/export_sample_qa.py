#!/usr/bin/env python3
"""Regenerate data/sample_qa.md by running real questions through the assistant.

Generated, not transcribed: the file always shows what the current corpus and
retriever actually produce.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.assistant import Assistant  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

SECTIONS = [
    ("Facts answered from the corpus", [
        "What is the expense ratio of Groww Value Fund?",
        "What is the exit load of Groww Value Fund?",
        "What is the lock-in period for Groww ELSS Tax Saver Fund?",
        "What is the minimum SIP for Groww Large Cap Fund?",
        "What is the benchmark of Groww ELSS Tax Saver Fund?",
        "What is the riskometer of Groww Nifty Total Market Index Fund?",
        "How do I download my mutual fund capital gains statement?",
    ]),
    ("Refused: opinion and portfolio questions", [
        "Should I buy Groww Value Fund?",
        "Which is the best Groww fund for me?",
    ]),
    ("Refused: performance claims", [
        "What returns did Groww Large Cap Fund give over 3 years?",
    ]),
    ("Refused: personal or account data", [
        "My PAN is ABCDE1234F, what is my folio balance?",
    ]),
    ("Declined: outside the corpus", [
        "What is the exit load of SBI Bluechip Fund?",
        "Who is the fund manager of Groww Value Fund?",
    ]),
]


def main():
    assistant = Assistant()
    out = [
        "# Sample Q&A",
        "",
        "Verbatim output from the prototype. Regenerate with "
        "`python3 tools/export_sample_qa.py`.",
        "",
        "Corpus last updated from sources: **%s**"
        % assistant.meta["last_updated_from_sources"],
        "",
    ]

    for heading, questions in SECTIONS:
        out.append("## %s" % heading)
        out.append("")
        for question in questions:
            reply = assistant.ask(question)
            citation = reply["citation"]
            out.append("**Q. %s**" % question)
            out.append("")
            out.append("> %s" % reply["answer"])
            out.append(">")
            out.append("> Source: [%s](%s) — %s" % (
                citation["title"], citation["url"], citation["publisher"]))
            out.append(">")
            out.append("> Last updated from sources: %s · %s"
                       % (reply["last_updated_from_sources"], reply["disclaimer"]))
            out.append("")
            trace = "intent=%s" % reply.get("intent")
            if reply.get("matched"):
                trace += ", matched=%s" % reply["matched"]
            out.append("<sub>`%s`</sub>" % trace)
            out.append("")

    with open(os.path.join(DATA, "sample_qa.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(out))
    print("Wrote data/sample_qa.md (%d questions)."
          % sum(len(q) for _, q in SECTIONS))


if __name__ == "__main__":
    main()
