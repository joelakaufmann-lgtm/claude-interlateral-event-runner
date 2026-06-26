#!/usr/bin/env python3
"""
watch_round.py — phase-flip watcher. The Haiku / scheduled-task job.

Polls GET /api/rounds/current and:
  - alerts on EVERY phase transition (propose -> vote -> work -> closed)
  - on `phase == voting`, fires the pre-staged votes via cast_votes.py and confirms 201s

Two run modes (both supported by the skill):
  - --once   : single poll; ideal for a scheduled task on a short cadence during the event
  - --loop   : standing watch loop; ideal for an in-session Haiku sub-agent

Latency is the point: a fast watcher firing the instant the window opens beats a
heavyweight reasoner deliberating while the window closes. Deliberation happens BEFORE the
window opens; this script only executes the already-approved mandate.

Usage:
    python watch_round.py --mandate mandate.yaml --once
    python watch_round.py --mandate mandate.yaml --loop --interval 15
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

import event_client as ec

STATE_FILE = ".watch_round_phase.json"


def _last_phase(state_path: str) -> str | None:
    try:
        return json.load(open(state_path)).get("phase")
    except (OSError, json.JSONDecodeError):
        return None


def _save_phase(state_path: str, phase: str) -> None:
    json.dump({"phase": phase, "ts": time.time()}, open(state_path, "w"))


def _alert(event: dict) -> None:
    """Phase-flip notification. Stdout is the default sink; a scheduled task or sub-agent
    relays it to Joel. Swap in a real notifier (e.g. an MCP message) as needed."""
    print(json.dumps({"alert": event}), flush=True)


def _fire_votes(mandate_path: str) -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.run(
        [sys.executable, os.path.join(here, "cast_votes.py"), "--mandate", mandate_path],
        capture_output=True, text=True,
    )
    try:
        out = json.loads(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip() else {}
    except (json.JSONDecodeError, IndexError):
        out = {"raw": proc.stdout}
    return {"returncode": proc.returncode, "report": out}


def poll_once(mandate_path: str, state_path: str) -> dict:
    phase = ec.current_phase().name
    prev = _last_phase(state_path)
    flipped = phase != prev
    result = {"phase": phase, "previous": prev, "flipped": flipped}

    if flipped:
        _alert({"type": "phase_flip", "from": prev, "to": phase})
        _save_phase(state_path, phase)

    if phase == "voting":
        result["vote_action"] = _fire_votes(mandate_path)

    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mandate", required=True)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--interval", type=int, default=15, help="seconds between polls in --loop")
    ap.add_argument("--max-minutes", type=int, default=120, help="safety stop for --loop")
    args = ap.parse_args()

    state_path = os.path.join(os.path.dirname(os.path.abspath(args.mandate)), STATE_FILE)

    if args.loop:
        deadline = time.time() + args.max_minutes * 60
        while time.time() < deadline:
            try:
                res = poll_once(args.mandate, state_path)
                print(json.dumps(res), flush=True)
                if res["phase"] in ("closed", "complete"):
                    break
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}), flush=True)
            time.sleep(args.interval)
        return 0

    # default: single poll
    print(json.dumps(poll_once(args.mandate, state_path), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
