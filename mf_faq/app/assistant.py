"""The FAQ assistant: guardrails -> scheme resolution -> retrieval -> cited answer.

Every returned answer carries exactly one citation and an "as-of" line. Nothing
is generated free-form: answers are grounded passages from data/corpus.json.
"""

import json
import os
import re

from .guardrails import classify, scan_and_redact
from .retriever import BM25Index, tokenize

CORPUS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "corpus.json")

DISCLAIMER = "Facts-only. No investment advice."

# Minimum BM25 score for a passage to count as an answer rather than a miss.
# Tuned against tests/test_assistant.py: below this the top hit is usually an
# incidental keyword overlap.
SCORE_FLOOR = 1.2

# Other fund houses. A question naming one of these is out of corpus scope, and
# must be caught before alias matching - "SBI Bluechip" would otherwise match the
# large-cap scheme's "bluechip" alias and get answered with the wrong AMC's terms.
OTHER_AMCS = [
    "sbi", "hdfc", "icici", "prudential", "axis", "nippon", "kotak", "uti",
    "mirae", "quant", "parag parikh", "ppfas", "dsp", "franklin", "templeton",
    "aditya birla", "birla", "canara", "robeco", "edelweiss", "motilal",
    "tata", "bandhan", "idfc", "invesco", "jm financial", "lic mf", "sundaram",
    "zerodha", "navi", "bajaj finserv", "whiteoak", "white oak", "360 one",
    "helios", "samco", "union mutual", "baroda", "bnp", "mahindra", "pgim",
    "shriram", "taurus", "trust mutual", "quantum", "indiabulls", "iti mutual",
    "angel one", "jio blackrock", "blackrock", "nj mutual", "old bridge",
    "unifi", "capitalmind", "choice mutual",
]

_OTHER_AMC_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in OTHER_AMCS) + r")\b", re.I
)

# Attributes that only make sense for a named scheme. Asking one of these with
# no scheme named is ambiguous, not answerable.
_SCHEME_ATTRIBUTE_RE = re.compile(
    r"\b(exit load|lock[ -]?in|minimum|min\.? ?sip|lumpsum|lump sum|benchmark|"
    r"riskometer|risk[ -]?o[ -]?meter|category)\b", re.I
)


class Assistant:
    def __init__(self, corpus_path=CORPUS_PATH):
        with open(corpus_path, encoding="utf-8") as handle:
            self.corpus = json.load(handle)

        self.meta = self.corpus["meta"]
        self.sources = {s["id"]: s for s in self.corpus["sources"]}
        self.schemes = {s["id"]: s for s in self.corpus["schemes"]}
        self.links = self.corpus["educational_links"]

        # One flat passage list over facts and general documents; a fact's
        # scheme name and aliases are folded into its indexed text so
        # "exit load of Groww Value Fund" ranks the right scheme's fact.
        self.passages = []
        for fact in self.corpus["facts"]:
            scheme = self.schemes[fact["scheme"]]
            self.passages.append({
                "id": fact["id"],
                "kind": "fact",
                "scheme": fact["scheme"],
                "attribute": fact["attribute"],
                "answer": fact["answer"],
                "source_id": fact["source_id"],
                "text": " ".join([
                    scheme["name"], " ".join(scheme["aliases"]),
                    fact["attribute"].replace("_", " "), fact["keywords"], fact["answer"],
                ]),
            })
        for doc in self.corpus["documents"]:
            self.passages.append({
                "id": doc["id"],
                "kind": "document",
                "scheme": None,
                "attribute": doc["topic"],
                "answer": doc["answer"],
                "source_id": doc["source_id"],
                "text": " ".join([doc["topic"].replace("_", " "), doc["keywords"], doc["answer"]]),
            })

        self.index = BM25Index(self.passages)

        # Longest aliases first so "groww nifty total market index fund" is not
        # matched by the shorter "index fund".
        self._alias_map = []
        for scheme in self.corpus["schemes"]:
            for alias in [scheme["name"]] + scheme["aliases"]:
                self._alias_map.append((alias.lower(), scheme["id"]))
        self._alias_map.sort(key=lambda pair: len(pair[0]), reverse=True)

        # Tokens that merely name a scheme. A passage matching only these has
        # not answered the attribute that was actually asked about.
        self._scheme_tokens = set()
        for alias, _ in self._alias_map:
            self._scheme_tokens.update(tokenize(alias, keep_stopwords=True))

    # -- helpers --------------------------------------------------------------

    def scheme_names(self):
        return [s["name"] for s in self.corpus["schemes"]]

    def resolve_scheme(self, text):
        """Return a scheme id if the question names one of the in-scope schemes."""
        lowered = " " + re.sub(r"[^a-z0-9 ]+", " ", text.lower()) + " "
        lowered = re.sub(r"\s+", " ", lowered)
        for alias, scheme_id in self._alias_map:
            if " " + alias + " " in lowered:
                return scheme_id
        return None

    def names_other_amc(self, text):
        match = _OTHER_AMC_RE.search(text)
        return match.group(1) if match else None

    def _answers_the_question(self, question, passage):
        """True if the passage matches at least one query term that is not just
        a scheme name. Guards against "who is the fund manager of Groww Value
        Fund" scoring on "value" alone and returning the category fact."""
        topic_terms = [t for t in tokenize(question) if t not in self._scheme_tokens]
        if not topic_terms:
            return True
        passage_terms = set(tokenize(passage["text"]))
        return any(term in passage_terms for term in topic_terms)

    def _cite(self, source_id):
        source = self.sources[source_id]
        return {
            "url": source["url"],
            "title": source["title"],
            "publisher": source["publisher"],
        }

    def _reply(self, answer, source_id=None, link=None, **extra):
        citation = self._cite(source_id) if source_id else link
        reply = {
            "answer": answer,
            "citation": citation,
            "last_updated_from_sources": self.meta["last_updated_from_sources"],
            "disclaimer": DISCLAIMER,
        }
        reply.update(extra)
        return reply

    # -- main entry point -----------------------------------------------------

    def ask(self, question):
        question = (question or "").strip()
        if not question:
            return self._reply(
                "Ask me a factual question about a Groww Mutual Fund scheme - for example its "
                "exit load, minimum SIP, benchmark, riskometer or lock-in.",
                link=self.links["advice_refusal"], intent="empty",
            )

        # 1. PII gate. The raw question is dropped here and never indexed,
        #    returned or logged.
        safe_question, pii_found = scan_and_redact(question)
        if pii_found:
            return self._reply(
                "I can't accept personal or account details, so I've discarded what you sent "
                "and detected " + ", ".join(pii_found) + " in it. Ask me about a scheme's "
                "published facts instead - for example \"What is the exit load of Groww Value Fund?\" "
                "For anything tied to your own folio, use the official investor channels.",
                link=self.links["pii_refusal"],
                intent="pii_refusal", pii_detected=pii_found,
            )

        # 2. Opinion / performance gates.
        intent = classify(safe_question)

        if intent == "greeting":
            return self._reply(
                "Hello. I answer published facts about Groww Mutual Fund schemes - exit load, "
                "minimum SIP, benchmark, riskometer, ELSS lock-in, expense ratio and statement "
                "downloads. Try: \"What is the exit load of Groww Value Fund?\"",
                link=self.links["advice_refusal"], intent="greeting",
            )

        if intent == "advice":
            scheme_id = self.resolve_scheme(safe_question)
            link = self.links["elss_refusal"] if scheme_id == "elss" else self.links["advice_refusal"]
            return self._reply(
                "I can only share published facts, so I can't tell you whether to buy, sell, hold or "
                "switch - that call depends on your own goals and is one for a SEBI-registered "
                "investment adviser. I'm happy to give you the scheme's exit load, minimum SIP, "
                "benchmark, riskometer or lock-in instead.",
                link=link, intent="advice_refusal",
            )

        if intent == "performance":
            return self._reply(
                "I don't compute or compare returns, and I don't make performance claims. "
                "Groww Mutual Fund publishes disclosed performance for every scheme in its monthly "
                "factsheet, linked below. Ask me a scheme fact - exit load, minimum SIP, benchmark, "
                "riskometer or lock-in - and I'll answer that.",
                link=self.links["performance_refusal"], intent="performance_refusal",
            )

        # 3. Fact path.
        other_amc = self.names_other_amc(safe_question)
        if other_amc:
            return self._reply(
                "That fund house isn't in this assistant's corpus - I only cover four Groww "
                "Mutual Fund schemes: " + ", ".join(self.scheme_names()) + ". Ask me about one "
                "of those, or look the other scheme up in its own AMC's Scheme Information Document.",
                link=self.links["no_answer"], intent="out_of_scope", out_of_scope=other_amc,
            )

        scheme_id = self.resolve_scheme(safe_question)

        # Restrict retrieval by scope. With a scheme named, that scheme's facts
        # plus the scheme-independent documents; with none named, documents only
        # - otherwise "what is a riskometer?" would return one arbitrary
        # scheme's riskometer reading instead of the definition.
        if scheme_id:
            allowed = {
                p["id"] for p in self.passages
                if p["scheme"] == scheme_id or p["scheme"] is None
            }
        else:
            allowed = {p["id"] for p in self.passages if p["scheme"] is None}

        hits = self.index.search(safe_question, top_k=3, allowed_ids=allowed)
        hits = [(p, sc) for p, sc in hits if self._answers_the_question(safe_question, p)]

        if not hits or hits[0][1] < SCORE_FLOOR:
            return self._no_answer(safe_question, scheme_id)

        passage, score = hits[0]

        return self._reply(
            passage["answer"],
            source_id=passage["source_id"],
            intent="fact",
            matched=passage["id"],
            attribute=passage["attribute"],
            scheme=self.schemes[passage["scheme"]]["name"] if passage["scheme"] else None,
            score=round(score, 3),
        )

    def _no_answer(self, question, scheme_id):
        in_scope = ", ".join(self.scheme_names())
        if scheme_id is None and _SCHEME_ATTRIBUTE_RE.search(question):
            answer = (
                "Which scheme do you mean? That fact is per-scheme, and I cover four: "
                + in_scope + "."
            )
        elif scheme_id is None and re.search(r"\bfund\b|\bscheme\b|\bamc\b", question, re.I):
            answer = (
                "That scheme isn't in this assistant's corpus. I cover four Groww Mutual Fund "
                "schemes: " + in_scope + ". Ask me about one of those and I'll cite the official page."
            )
        else:
            answer = (
                "I don't have that fact in my corpus, so I won't guess. I can answer exit load, "
                "minimum SIP or lumpsum, benchmark, riskometer, scheme category, ELSS lock-in, "
                "expense ratio and statement downloads for: " + in_scope + "."
            )
        return self._reply(answer, link=self.links["no_answer"], intent="no_answer")
