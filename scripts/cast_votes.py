#!/usr/bin/env python3
"""
cast_votes.py — executor entrypoint. Fires the PRE-APPROVED votes from a mandate file.

This is the lean-model job: no judgment, just execution. It must NOT decide which entries
to vote — those come from mandate.yaml, which Opus wrote with Joel's sign-off.

Idempotency: it tracks what it has cast to a small state file so a re-run (or a watcher
firing twice) never exceeds the cap of 3 and never double-fires the same entry.

Usage:
    python cast_votes.py --mandate mandate.yaml
    python cast_votes.py --mandate mandate.yaml --dry-run

Exit code 0 = all approved votes confirmed (201); non-zero = something to report up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import event_client as ec

VOTE_CAP = 3


def _load_mandate(path: str) -> dict:
    text = open(path, "r", encoding="utf-8").read()
    if path.endswith((".yaml", ".yml")):
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except ImportError:
            return _mini_yaml(text)
    return json.loads(text)


def _mini_yaml(text: str) -> dict:
    """Tiny fallback parser for the flat mandate schema if PyYAML is unavailable.
    Supports: scalars, and a 'votes:' list of '- id' or inline '[a, b, c]'."""
    out: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].split("#", 1)[0].rstrip()
        if not line.strip():
            i += 1
            continue
        if line.strip().endswith(":") and not line.strip().startswith("-"):
            key = line.strip()[:-1].strip()
            block = []
            i += 1
            while i < len(lines) and (lines[i].startswith((" ", "\t")) or lines[i].strip().startswith("-")):
                item = lines[i].split("#", 1)[0].strip()
                if item.startswith("- "):
                    block.append(item[2:].strip().strip('"\''))
                i += 1
            out[key] = block
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                out[k.strip()] = [x.strip().strip('"\'') for x in v[1:-1].split(",") if x.strip()]
            else:
                out[k.strip()] = v.strip('"\'')
        i += 1
    return out


def _state_path(mandate_path: str) -> str:
    return os.path.join(os.path.dirname(os.path.abspath(mandate_path)), ".cast_votes_state.json")


def _load_state(path: str) -> set:
    try:
        return set(json.load(open(path)))
    except (OSError, json.JSONDecodeError):
        return set()


def _save_state(path: str, cast: set) -> None:
    json.dump(sorted(cast), open(path, "w"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mandate", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mandate = _load_mandate(args.mandate)
    votes = [str(v) for v in (mandate.get("votes") or [])]
    intent = mandate.get("vote_intent", "Cast pre-approved vote per Joel's mandate.")

    if not votes:
        print(json.dumps({"result": "no_votes_in_mandate"}))
        return 0
    if len(votes) > VOTE_CAP:
        print(json.dumps({"result": "error", "reason": f"mandate exceeds cap of {VOTE_CAP}",
                          "votes": votes}))
        return 2

    # Only act in the voting phase — a watcher may invoke us early.
    phase = ec.current_phase().name
    if phase != "voting":
        print(json.dumps({"result": "skipped", "phase": phase,
                          "reason": "not in voting phase yet"}))
        return 3

    state_path = _state_path(args.mandate)
    already = _load_state(state_path)
    results = []
    ok = True

    for entry_id in votes:
        if entry_id in already:
            results.append({"entry": entry_id, "status": "already_cast", "skipped": True})
            continue
        if args.dry_run:
            results.append({"entry": entry_id, "status": "dry_run"})
            continue
        try:
            resp = ec.cast_vote(entry_id, intent=intent)
            status = resp.get("status")
            fp = (resp.get("json") or {}).get("edit_fingerprint") or (resp.get("json") or {}).get("receipt")
            confirmed = status == 201
            ok = ok and confirmed
            if confirmed:
                already.add(entry_id)
            results.append({"entry": entry_id, "status": status,
                            "confirmed_201": confirmed, "fingerprint": fp})
        except ec.ApiError as e:
            ok = False
            results.append({"entry": entry_id, "error": e.code, "http": e.status})

    if not args.dry_run:
        _save_state(state_path, already)

    print(json.dumps({"result": "ok" if ok else "partial",
                      "cast": sorted(already), "details": results}, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
