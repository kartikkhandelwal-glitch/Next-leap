#!/usr/bin/env python3
"""Build the standalone single-page prototype into dist/index.html.

Inlines data/corpus.json and web/engine.js into web/page.template.html, so the
hosted page is one self-contained file with no network calls of its own (beyond
the Google Fonts stylesheet). Run tools/parity_check.py afterwards to confirm
the inlined engine still answers exactly like the Python one.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TEMPLATE = os.path.join(ROOT, "web", "page.template.html")
ENGINE = os.path.join(ROOT, "web", "engine.js")
CORPUS = os.path.join(ROOT, "data", "corpus.json")
OUT = os.path.join(ROOT, "dist", "index.html")


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main():
    template = read(TEMPLATE)
    engine = read(ENGINE)
    corpus = json.loads(read(CORPUS))

    # Compact, and neutralise any sequence that would close the host <script>.
    corpus_json = json.dumps(corpus, separators=(",", ":"), ensure_ascii=False)
    corpus_json = corpus_json.replace("</", "<\\/")

    if "__CORPUS_JSON__" not in template or "__ENGINE_JS__" not in template:
        print("template is missing a placeholder", file=sys.stderr)
        return 1

    page = template.replace("__CORPUS_JSON__", corpus_json).replace("__ENGINE_JS__", engine)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(page)

    print("Wrote dist/index.html  (%.1f KB, %d sources, %d facts, %d documents)" % (
        len(page.encode("utf-8")) / 1024,
        len(corpus["sources"]), len(corpus["facts"]), len(corpus["documents"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
