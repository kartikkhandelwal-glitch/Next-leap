#!/usr/bin/env python3
"""Re-check every corpus source and report what needs re-reading.

    python3 tools/refresh_corpus.py            # check all sources are live
    python3 tools/refresh_corpus.py --save DIR # also archive each page/PDF

Scheme terms move by addendum, so the corpus is refreshed deliberately rather
than scraped on every request. This tool does the mechanical half: confirm each
URL still resolves, save a copy, and stamp meta.last_updated_from_sources. A
human still re-reads the SID/KIM and edits data/corpus.json - a wrong exit load
delivered confidently is worse than a stale "check the source" answer.

Needs outbound network access to growwmf.in / sebi.gov.in / amfiindia.com.
"""

import argparse
import datetime
import json
import os
import sys
import urllib.error
import urllib.request

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "corpus.json")
UA = "Mozilla/5.0 (compatible; mf-faq-corpus-refresh/1.0)"
TIMEOUT = 30


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.status, response.read()


def safe_name(source):
    return "%s_%s" % (source["id"], "".join(
        c if c.isalnum() else "-" for c in source["title"]
    )[:70])


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--save", metavar="DIR", help="archive each fetched source into DIR")
    parser.add_argument("--stamp", action="store_true",
                        help="set meta.last_updated_from_sources to today if all sources resolve")
    args = parser.parse_args()

    with open(CORPUS, encoding="utf-8") as handle:
        corpus = json.load(handle)

    if args.save:
        os.makedirs(args.save, exist_ok=True)

    failures = []
    for source in corpus["sources"]:
        try:
            status, body = fetch(source["url"])
            note = "%d  %7d bytes" % (status, len(body))
            if args.save:
                ext = ".pdf" if source["url"].lower().endswith(".pdf") else ".html"
                with open(os.path.join(args.save, safe_name(source) + ext), "wb") as out:
                    out.write(body)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as exc:
            note = "FAILED: %s" % exc
            failures.append(source["id"])
        print("%-5s %-52s %s" % (source["id"], source["title"][:52], note))

    print("\n%d/%d sources resolved." % (len(corpus["sources"]) - len(failures),
                                         len(corpus["sources"])))
    if failures:
        print("Unreachable: %s" % ", ".join(failures))
        print("Fix or replace those URLs in data/corpus.json before stamping.")
        return 1

    if args.stamp:
        corpus["meta"]["last_updated_from_sources"] = datetime.date.today().isoformat()
        with open(CORPUS, "w", encoding="utf-8") as handle:
            json.dump(corpus, handle, indent=2, ensure_ascii=False)
        print("Stamped last_updated_from_sources = %s"
              % corpus["meta"]["last_updated_from_sources"])

    print("\nNow re-read the SID/KIM for each scheme and update `facts` in "
          "data/corpus.json where a term has changed, then re-run the tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
