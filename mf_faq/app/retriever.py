"""Small-corpus retrieval: Okapi BM25 over ~36 short passages, no dependencies.

The corpus is tiny and closed, so BM25 over hand-tagged keyword strings beats
an embedding index here: it is deterministic, inspectable, and every hit carries
the source id that becomes the answer's single citation.
"""

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+")

# Query words that carry no retrieval signal in this domain.
STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "of", "for", "to", "in", "on",
    "at", "by", "and", "or", "it", "its", "this", "that", "what", "whats", "which",
    "how", "do", "does", "did", "i", "me", "my", "you", "your", "can", "will",
    "be", "have", "has", "there", "any", "much", "many", "please", "tell", "about",
    "fund", "scheme", "groww", "mutual", "funds",
}

# Light stemming: the corpus is small enough that a handful of suffix rules
# gets "charges"->"charge" and "returns"->"return" without a real stemmer.
def _stem(word):
    for suffix in ("ies", "es", "s"):
        if len(word) > 4 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def tokenize(text, keep_stopwords=False):
    """Lowercase, drop stopwords, stem. Stopwords are checked against both the
    raw and the stemmed form so "schemes" is dropped alongside "scheme"."""
    out = []
    for word in _TOKEN.findall(text.lower()):
        if len(word) < 2:
            continue
        stem = _stem(word)
        if not keep_stopwords and (word in STOPWORDS or stem in STOPWORDS):
            continue
        out.append(stem)
    return out


class BM25Index:
    """Standard Okapi BM25 with the usual k1=1.5, b=0.75."""

    K1 = 1.5
    B = 0.75

    def __init__(self, passages):
        # passages: list of dicts with 'id' and 'text'
        self.passages = passages
        self.docs = [tokenize(p["text"]) for p in passages]
        self.lengths = [len(d) for d in self.docs]
        self.avg_len = (sum(self.lengths) / len(self.docs)) if self.docs else 0.0
        self.tfs = [Counter(d) for d in self.docs]

        df = Counter()
        for doc in self.docs:
            df.update(set(doc))
        n = len(self.docs)
        self.idf = {
            term: math.log(1 + (n - freq + 0.5) / (freq + 0.5))
            for term, freq in df.items()
        }

    def score(self, query_terms, i):
        tf, length, total = self.tfs[i], self.lengths[i], 0.0
        for term in query_terms:
            if term not in tf:
                continue
            freq = tf[term]
            denom = freq + self.K1 * (1 - self.B + self.B * length / (self.avg_len or 1))
            total += self.idf.get(term, 0.0) * freq * (self.K1 + 1) / denom
        return total

    def search(self, query, top_k=5, allowed_ids=None):
        """Return [(passage, score)] sorted by score, best first."""
        terms = tokenize(query)
        if not terms:
            return []
        hits = []
        for i, passage in enumerate(self.passages):
            if allowed_ids is not None and passage["id"] not in allowed_ids:
                continue
            score = self.score(terms, i)
            if score > 0:
                hits.append((passage, score))
        hits.sort(key=lambda pair: pair[1], reverse=True)
        return hits[:top_k]
