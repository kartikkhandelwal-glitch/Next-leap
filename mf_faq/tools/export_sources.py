#!/usr/bin/env python3
"""Regenerate data/sources.csv and data/sources.md from data/corpus.json.

The source list is a deliverable in its own right, so it is generated rather
than maintained by hand - it can never drift from what the assistant cites.
"""

import csv
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
CORPUS = os.path.join(DATA, "corpus.json")

FIELDS = ["id", "publisher", "doc_type", "title", "url", "used_for", "captured_on"]


def used_for(corpus):
    """Map each source id to the questions it backs."""
    schemes = {s["id"]: s["name"] for s in corpus["schemes"]}
    uses = defaultdict(list)
    for fact in corpus["facts"]:
        uses[fact["source_id"]].append(
            "%s - %s" % (schemes[fact["scheme"]], fact["attribute"].replace("_", " "))
        )
    for doc in corpus["documents"]:
        uses[doc["source_id"]].append(doc["topic"].replace("_", " "))
    for name, link in corpus["educational_links"].items():
        for source in corpus["sources"]:
            if source["url"] == link["url"]:
                uses[source["id"]].append("%s link" % name.replace("_", " "))
    return uses


def main():
    with open(CORPUS, encoding="utf-8") as handle:
        corpus = json.load(handle)
    uses = used_for(corpus)

    rows = []
    for source in corpus["sources"]:
        rows.append({
            "id": source["id"],
            "publisher": source["publisher"],
            "doc_type": source["doc_type"],
            "title": source["title"],
            "url": source["url"],
            "used_for": "; ".join(sorted(set(uses.get(source["id"], ["reference"])))),
            "captured_on": source["captured_on"],
        })

    with open(os.path.join(DATA, "sources.csv"), "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    grouped = defaultdict(list)
    for row in rows:
        grouped[row["publisher"]].append(row)

    lines = [
        "# Source list",
        "",
        "%d public pages from the AMC, SEBI, AMFI and the SEBI-registered registrars. "
        "No third-party blogs, no aggregator sites, no app internals." % len(rows),
        "",
        "Captured: %s. Regenerate with `python3 tools/export_sources.py`."
        % corpus["meta"]["last_updated_from_sources"],
        "",
    ]
    for publisher in sorted(grouped):
        lines.append("## %s" % publisher)
        lines.append("")
        lines.append("| # | Type | Page | Used for |")
        lines.append("|---|------|------|----------|")
        for row in grouped[publisher]:
            lines.append("| %s | %s | [%s](%s) | %s |" % (
                row["id"], row["doc_type"], row["title"], row["url"], row["used_for"]))
        lines.append("")

    with open(os.path.join(DATA, "sources.md"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))

    print("Wrote data/sources.csv and data/sources.md (%d sources)." % len(rows))


if __name__ == "__main__":
    main()
