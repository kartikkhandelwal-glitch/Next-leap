#!/usr/bin/env python3
"""Command-line front end for the Groww Mutual Fund FAQ assistant.

    python3 cli.py                      # interactive
    python3 cli.py "ELSS lock-in?"      # one shot
    python3 cli.py --json "Exit load of Groww Value Fund?"
"""

import json
import sys

from app.assistant import DISCLAIMER, Assistant

WELCOME = """Groww Mutual Fund FAQ - facts about scheme terms, with a source link on every answer.

Try:
  1. What is the exit load of Groww Value Fund?
  2. What is the lock-in period for Groww ELSS Tax Saver Fund?
  3. How do I download my mutual fund capital gains statement?

{disclaimer}
""".format(disclaimer=DISCLAIMER)


def render(reply):
    lines = [reply["answer"], ""]
    citation = reply.get("citation")
    if citation:
        lines.append("Source: {title} ({publisher})".format(**citation))
        lines.append("        " + citation["url"])
    lines.append("Last updated from sources: " + reply["last_updated_from_sources"])
    return "\n".join(lines)


def main(argv):
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    assistant = Assistant()

    if argv:
        reply = assistant.ask(" ".join(argv))
        print(json.dumps(reply, indent=2) if as_json else render(reply))
        return 0

    print(WELCOME)
    while True:
        try:
            question = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if question.lower() in {"exit", "quit", ":q"}:
            return 0
        if not question:
            continue
        reply = assistant.ask(question)
        print()
        print(json.dumps(reply, indent=2) if as_json else render(reply))
        print()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
