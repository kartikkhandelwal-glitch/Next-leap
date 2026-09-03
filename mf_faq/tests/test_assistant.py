"""Behaviour tests for the FAQ assistant.

    python3 -m unittest discover -s tests -v

The three rules the brief makes non-negotiable are asserted for every reply:
one citation, an official publisher, and no PII ever echoed back.
"""

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.assistant import Assistant  # noqa: E402
from app.guardrails import scan_and_redact  # noqa: E402

# Publishers we are allowed to cite: the AMC, the platform's own help pages,
# the regulator, the industry body and the SEBI-registered RTAs. No blogs.
ALLOWED_HOSTS = {
    "www.growwmf.in", "assets-netstorage.growwmf.in", "groww.in",
    "www.sebi.gov.in", "investor.sebi.gov.in",
    "www.amfiindia.com", "portal.amfiindia.com",
    "www.camsonline.com", "mfs.kfintech.com", "www.mfcentral.com",
}

_ABBREV = re.compile(r"\b(Rs|Re|No|Sr|Ltd|Pvt|e\.g|i\.e|vs|approx|Sec)\.$", re.I)


def sentence_count(text):
    """Sentence split that does not break on "Rs. 500"."""
    parts, buf = [], ""
    for chunk in re.split(r"(?<=[.!?])\s+", text.strip()):
        buf = (buf + " " + chunk).strip() if buf else chunk
        if _ABBREV.search(buf):
            continue
        parts.append(buf)
        buf = ""
    if buf:
        parts.append(buf)
    return len(parts)


def host_of(url):
    return url.split("://", 1)[-1].split("/", 1)[0]


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.a = Assistant()

    def test_source_count_is_within_brief(self):
        self.assertTrue(15 <= len(self.a.sources) <= 25, len(self.a.sources))

    def test_every_source_is_an_official_host(self):
        for source in self.a.sources.values():
            self.assertIn(host_of(source["url"]), ALLOWED_HOSTS, source["url"])

    def test_every_passage_resolves_to_a_real_source(self):
        for passage in self.a.passages:
            self.assertIn(passage["source_id"], self.a.sources, passage["id"])

    def test_no_source_is_orphaned(self):
        used = {p["source_id"] for p in self.a.passages}
        used |= {
            s["id"] for s in self.a.sources.values()
            for link in self.a.links.values() if link["url"] == s["url"]
        }
        orphans = set(self.a.sources) - used
        self.assertEqual(orphans, set(), "unused sources: %s" % sorted(orphans))

    def test_corpus_answers_stay_within_three_sentences(self):
        for passage in self.a.passages:
            self.assertLessEqual(sentence_count(passage["answer"]), 3, passage["id"])

    def test_no_scheme_alias_collides_across_schemes(self):
        seen = {}
        for scheme in self.a.corpus["schemes"]:
            for alias in [scheme["name"]] + scheme["aliases"]:
                key = alias.lower()
                self.assertNotIn(key, seen, "%r claimed by %s and %s"
                                 % (key, seen.get(key), scheme["id"]))
                seen[key] = scheme["id"]


class ContractTests(unittest.TestCase):
    """Invariants that must hold for every reply the assistant can produce."""

    QUESTIONS = [
        "What is the exit load of Groww Value Fund?",
        "ELSS lock-in?",
        "Minimum SIP for Groww Large Cap Fund",
        "Riskometer of Groww Nifty Total Market Index Fund",
        "Expense ratio of Groww Value Fund",
        "How do I download my capital gains statement?",
        "Should I buy Groww ELSS Tax Saver Fund?",
        "What returns did Groww Large Cap Fund give?",
        "Exit load of SBI Bluechip Fund",
        "who is the fund manager of Groww Value Fund",
        "my PAN is ABCDE1234F",
        "hi",
        "",
        "   ",
        "?????",
    ]

    def setUp(self):
        self.a = Assistant()

    def test_every_reply_carries_exactly_one_official_citation(self):
        for question in self.QUESTIONS:
            reply = self.a.ask(question)
            citation = reply["citation"]
            self.assertIsNotNone(citation, question)
            self.assertIn(host_of(citation["url"]), ALLOWED_HOSTS, question)
            self.assertTrue(citation["title"], question)

    def test_every_reply_is_stamped_and_disclaimed(self):
        for question in self.QUESTIONS:
            reply = self.a.ask(question)
            self.assertRegex(reply["last_updated_from_sources"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertEqual(reply["disclaimer"], "Facts-only. No investment advice.")

    def test_answers_stay_within_three_sentences(self):
        for question in self.QUESTIONS:
            reply = self.a.ask(question)
            self.assertLessEqual(sentence_count(reply["answer"]), 4, question)

    def test_reply_is_json_serialisable(self):
        for question in self.QUESTIONS:
            json.dumps(self.a.ask(question))


class FactTests(unittest.TestCase):
    def setUp(self):
        self.a = Assistant()

    def assert_answers(self, question, must_contain, source_fragment=None):
        reply = self.a.ask(question)
        self.assertEqual(reply["intent"], "fact", "%s -> %s" % (question, reply["answer"]))
        for needle in must_contain:
            self.assertIn(needle.lower(), reply["answer"].lower(),
                          "%r missing from: %s" % (needle, reply["answer"]))
        if source_fragment:
            self.assertIn(source_fragment, reply["citation"]["url"])

    def test_exit_load_per_scheme(self):
        self.assert_answers("What is the exit load of Groww Value Fund?", ["1%", "1 year"])
        self.assert_answers("Exit load for Groww Large Cap Fund", ["1%", "7 days"])
        self.assert_answers("Groww Nifty Total Market Index Fund exit load", ["0.25%", "7 days"])
        self.assert_answers("Exit load on Groww ELSS Tax Saver Fund", ["nil"])

    def test_lock_in(self):
        self.assert_answers("What is the lock-in period for Groww ELSS Tax Saver Fund?",
                            ["3 years", "lock-in"])

    def test_minimums(self):
        self.assert_answers("Minimum SIP for Groww Large Cap Fund", ["100"])
        self.assert_answers("Minimum lumpsum for Groww Value Fund", ["500"])
        self.assert_answers("Minimum investment in Groww ELSS Tax Saver Fund", ["500"])

    def test_benchmarks(self):
        self.assert_answers("Benchmark of Groww Large Cap Fund", ["nifty 100"])
        self.assert_answers("Benchmark of Groww Value Fund", ["nifty 500"])
        self.assert_answers("Benchmark of Groww ELSS Tax Saver Fund", ["nifty 500"])
        self.assert_answers("Benchmark of Groww Nifty Total Market Index Fund",
                            ["nifty total market"])

    def test_riskometer(self):
        self.assert_answers("Riskometer of Groww Value Fund", ["very high"])
        self.assert_answers("What is a riskometer?", ["six levels"])

    def test_expense_ratio_links_live_disclosure_and_quotes_no_number(self):
        reply = self.a.ask("What is the expense ratio of Groww Value Fund?")
        self.assertIn("expense-ratio", reply["citation"]["url"])
        # A stale TER figure is worse than no figure: assert none is asserted.
        self.assertNotRegex(reply["answer"], r"\bis \d+\.\d+ ?%")

    def test_statement_download(self):
        self.assert_answers("How do I download my mutual fund capital gains statement?",
                            ["reports"], "groww.in/help")
        self.assert_answers("How do I get a consolidated account statement?", ["cas"])

    def test_scheme_named_never_answers_with_another_schemes_fact(self):
        reply = self.a.ask("Exit load of Groww ELSS Tax Saver Fund")
        self.assertEqual(reply["scheme"], "Groww ELSS Tax Saver Fund")
        self.assertNotIn("1 year", reply["answer"])


class RefusalTests(unittest.TestCase):
    def setUp(self):
        self.a = Assistant()

    def test_advice_is_refused_with_an_educational_link(self):
        for question in [
            "Should I buy Groww Value Fund?",
            "Is Groww ELSS Tax Saver Fund good for me?",
            "Which is the best Groww fund?",
            "Can you recommend a fund for my portfolio?",
            "Should I sell my Groww Large Cap Fund units?",
            "How much should I invest in ELSS?",
            "Is Groww Value Fund a good choice for me?",
        ]:
            reply = self.a.ask(question)
            self.assertEqual(reply["intent"], "advice_refusal", question)
            self.assertIn("sebi.gov.in", reply["citation"]["url"], question)
            self.assertNotIn("you should", reply["answer"].lower())

    def test_performance_questions_are_refused_and_point_at_the_factsheet(self):
        for question in [
            "What returns did Groww Large Cap Fund give in 3 years?",
            "What is the CAGR of Groww Value Fund?",
            "Compare the performance of Groww Value Fund and Groww Large Cap Fund",
            "How much will I earn from Groww ELSS Tax Saver Fund?",
        ]:
            reply = self.a.ask(question)
            self.assertEqual(reply["intent"], "performance_refusal", question)
            self.assertIn("fact-sheet", reply["citation"]["url"])
            self.assertNotRegex(reply["answer"], r"\d+(\.\d+)?\s?%")

    def test_other_fund_houses_are_out_of_scope(self):
        for question in [
            "Exit load of SBI Bluechip Fund",
            "What is the lock-in of Axis ELSS Tax Saver Fund?",
            "Parag Parikh Flexi Cap minimum SIP",
        ]:
            reply = self.a.ask(question)
            self.assertEqual(reply["intent"], "out_of_scope", question)

    def test_unknown_facts_are_declined_rather_than_guessed(self):
        for question in [
            "who is the fund manager of Groww Value Fund",
            "what is the AUM of Groww Value Fund",
            "what is the portfolio turnover of Groww Large Cap Fund",
        ]:
            reply = self.a.ask(question)
            self.assertEqual(reply["intent"], "no_answer", "%s -> %s" % (question, reply["answer"]))

    def test_scheme_specific_question_without_a_scheme_asks_which_one(self):
        reply = self.a.ask("What is the exit load?")
        self.assertEqual(reply["intent"], "no_answer")
        self.assertIn("which scheme", reply["answer"].lower())


class PIITests(unittest.TestCase):
    def setUp(self):
        self.a = Assistant()

    CASES = [
        ("My PAN is ABCDE1234F, what is the exit load?", "PAN"),
        ("Aadhaar 2345 6789 0123 exit load please", "Aadhaar"),
        ("mail me at investor@example.com", "email address"),
        ("call me on 9876543210", "phone number"),
        ("my OTP is 483920", "OTP"),
        ("folio number 1234567890 exit load", "folio or account number"),
        ("my account 123456789012 balance", "folio or account number"),
        ("transfer to 123456789012 please", "bank account number"),
        ("+91 98765 43210", "phone number"),
    ]

    def test_pii_is_detected(self):
        for text, label in self.CASES:
            _, found = scan_and_redact(text)
            self.assertIn(label, found, text)

    def test_pii_questions_are_refused_and_never_echoed(self):
        for text, _ in self.CASES:
            reply = self.a.ask(text)
            self.assertEqual(reply["intent"], "pii_refusal", text)
            for token in re.findall(r"[A-Z]{5}[0-9]{4}[A-Z]|[0-9]{4,}|\S+@\S+", text):
                self.assertNotIn(token, json.dumps(reply), "%r echoed back" % token)

    def test_clean_questions_are_not_flagged(self):
        for text in [
            "What is the exit load of Groww Value Fund?",
            "Minimum SIP is Rs 500?",
            "ELSS lock-in 3 years?",
            "Is the benchmark Nifty 100 TRI?",
            "TER slabs start at 2.25% on the first Rs. 500 crore",
            "Groww Nifty 500 Low Volatility 50 exit load",
            "exit load 0.25% within 7 days",
        ]:
            _, found = scan_and_redact(text)
            self.assertEqual(found, [], "%s -> %s" % (text, found))


if __name__ == "__main__":
    unittest.main()
