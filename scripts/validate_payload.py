#!/usr/bin/env python3
"""
validate_payload.py — 10,240-byte pre-flight for proposal submissions.

The cap is on the FULL serialized JSON body, not just the content string. Day-04 lost time
binary-searching the cap live; this checks it deterministically before any POST.

Usage:
    # check a content file with a title/intent
    python validate_payload.py --title "Agent or Guardian?" --intent "Submit proposal" \
        --content-file proposal.md

    # or check a pre-built JSON payload
    python validate_payload.py --payload-file payload.json

Exit 0 = fits; exit 1 = over cap (prints how many bytes to trim).
"""

from __future__ import annotations

import argparse
import json
import sys

CAP = 10_240


def payload_bytes(payload: dict) -> int:
    return len(json.dumps(payload).encode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title")
    ap.add_argument("--intent")
    ap.add_argument("--mandate-label", default="explicit")
    ap.add_argument("--content-file")
    ap.add_argument("--payload-file")
    args = ap.parse_args()

    if args.payload_file:
        payload = json.load(open(args.payload_file, encoding="utf-8"))
    else:
        if not (args.title and args.content_file and args.intent):
            print(json.dumps({"error": "need --title, --intent, --content-file (or --payload-file)"}))
            return 2
        content = open(args.content_file, encoding="utf-8").read()
        payload = {
            "title": args.title,
            "content": content,
            "mandate_label": args.mandate_label,
            "intent": args.intent,
        }

    size = payload_bytes(payload)
    fits = size <= CAP
    report = {
        "bytes": size,
        "cap": CAP,
        "fits": fits,
        "headroom" if fits else "over_by": CAP - size if fits else size - CAP,
    }
    print(json.dumps(report, indent=2))
    return 0 if fits else 1


if __name__ == "__main__":
    sys.exit(main())
