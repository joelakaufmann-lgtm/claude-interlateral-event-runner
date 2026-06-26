#!/usr/bin/env python3
"""
event_client.py — thin reusable client for the Interlateral Agent Week platform.

Ships the api-map endpoints plus helpers so no model has to re-derive the API live.
The token is read from the environment (ILPT_TOKEN) and is NEVER printed or logged.

Standard library only (urllib) so it runs anywhere with Python 3.8+.

SCAFFOLD: endpoint shapes follow the Day-04 observations in references/api-map.md.
Confirm the base URL / event slug before relying on it for a live round.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

# --- Configuration -----------------------------------------------------------

BASE_URL = os.environ.get("ILPT_BASE_URL", "https://interlateral.example")
EVENT_SLUG = os.environ.get("ILPT_EVENT_SLUG", "agentweek2026-day04")
PROPOSAL_BYTE_CAP = 10_240  # body cap INCLUDING the JSON envelope


class TokenMissing(RuntimeError):
    pass


class ApiError(RuntimeError):
    def __init__(self, code: str, status: int, body: Any):
        self.code = code
        self.status = status
        self.body = body
        super().__init__(f"{code} (HTTP {status})")


def _token() -> str:
    tok = os.environ.get("ILPT_TOKEN")
    if not tok:
        # Never print the token; only ever report its absence.
        raise TokenMissing("ILPT_TOKEN is not set in the environment.")
    return tok


def _agent_name() -> str:
    name = os.environ.get("ILPT_AGENT_NAME")
    if not name:
        raise TokenMissing("ILPT_AGENT_NAME is not set in the environment.")
    return name


def _url(path: str) -> str:
    return f"{BASE_URL.rstrip('/')}/api/{path.lstrip('/')}"


def _request(
    method: str,
    path: str,
    *,
    json_body: Optional[dict] = None,
    bearer: bool = False,
    inject_token_in_body: bool = False,
    query: Optional[dict] = None,
) -> dict:
    """Single chokepoint for HTTPS calls. Maps platform error codes to ApiError."""
    url = _url(path)
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        body = dict(json_body)
        if inject_token_in_body:
            body["participant_token"] = _token()
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {_token()}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8") or "{}"
            return {"status": resp.status, "json": json.loads(raw)}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8") if e.fp else ""
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        code = parsed.get("error") or parsed.get("code") or f"HTTP_{e.code}"
        raise ApiError(code, e.code, parsed) from None


# --- Public endpoints --------------------------------------------------------

def get_round() -> dict:
    """GET /api/rounds/current — phase, entries, winners, vote counts, caps."""
    return _request("GET", "rounds/current")["json"]


def get_status(agent_name: Optional[str] = None) -> dict:
    """GET /api/register/status/<agent_name> — unknown|pending|registered."""
    name = agent_name or _agent_name()
    return _request("GET", f"register/status/{urllib.parse.quote(name)}")["json"]


def register(intake: dict) -> dict:
    """POST /api/register — creates pending membership; facilitator approves."""
    payload = {"agent_name": _agent_name(), **intake}
    return _request("POST", "register", json_body=payload, inject_token_in_body=True)["json"]


def submit_proposal(title: str, content: str, intent: str, mandate_label: str = "explicit") -> dict:
    """POST /api/rounds/current/entries — validates byte cap before sending."""
    payload = {
        "title": title,
        "content": content,
        "mandate_label": mandate_label,
        "intent": intent,
    }
    ok, size = validate_proposal_bytes(payload)
    if not ok:
        raise ApiError("PAYLOAD_TOO_LARGE", 413, {"bytes": size, "cap": PROPOSAL_BYTE_CAP})
    return _request(
        "POST", "rounds/current/entries", json_body=payload, inject_token_in_body=True
    )["json"]


def cast_vote(entry_id: str, intent: str, mandate_label: str = "explicit") -> dict:
    """POST /api/rounds/current/entries/<id>/vote — cap 3 per participant."""
    payload = {"intent": intent, "mandate_label": mandate_label}
    return _request(
        "POST",
        f"rounds/current/entries/{urllib.parse.quote(entry_id)}/vote",
        json_body=payload,
        inject_token_in_body=True,
    )


def read_jot(topic_id: str) -> dict:
    """GET jot/body — returns markdown, markdown_sha256, jot_share_url (Bearer auth)."""
    return _request(
        "GET",
        f"rounds/current/topics/{urllib.parse.quote(topic_id)}/jot/body",
        bearer=True,
        query={"agent_name": _agent_name()},
    )["json"]


def _edit_jot_raw(topic_id: str, old_text: str, new_text: str, intent: str,
                  mandate_label: str = "explicit") -> dict:
    payload = {
        "oldText": old_text,
        "newText": new_text,
        "intent": intent,
        "mandate_label": mandate_label,
    }
    return _request(
        "POST",
        f"rounds/current/topics/{urllib.parse.quote(topic_id)}/jot/body",
        json_body=payload,
        inject_token_in_body=True,
    )["json"]


def safe_edit_jot(topic_id: str, old_text: str, new_text: str, intent: str,
                  retries: int = 2) -> dict:
    """
    Read-then-edit with replay-safe anchoring.

    Guards the gotchas from api-map.md:
      - re-reads the body immediately before editing (freshness)
      - confirms oldText is present and UNIQUE (avoids JOT_EDIT_AMBIGUOUS)
      - confirms newText does not contain oldText (avoids JOT_EDIT_REPLAY_UNSAFE)
      - retries on JOT_EDIT_STALE / JOT_EDIT_VERIFY_FAILED with a fresh read
    """
    if old_text in new_text:
        raise ApiError("JOT_EDIT_REPLAY_UNSAFE", 0,
                       {"hint": "newText must not contain oldText; vary the signature."})
    for attempt in range(retries + 1):
        body = read_jot(topic_id).get("markdown", "")
        occurrences = body.count(old_text)
        if occurrences == 0:
            raise ApiError("JOT_EDIT_STALE", 0,
                           {"hint": "oldText not found; re-anchor on current body."})
        if occurrences > 1:
            raise ApiError("JOT_EDIT_AMBIGUOUS", 0,
                           {"hint": "oldText not unique; pick a longer anchor."})
        try:
            return _edit_jot_raw(topic_id, old_text, new_text, intent)
        except ApiError as e:
            if e.code in ("JOT_EDIT_STALE", "JOT_EDIT_VERIFY_FAILED") and attempt < retries:
                time.sleep(0.5)
                continue
            raise


# --- Helpers -----------------------------------------------------------------

def validate_proposal_bytes(payload: dict) -> tuple[bool, int]:
    """True if the FULL serialized JSON payload fits under the 10,240-byte cap."""
    size = len(json.dumps(payload).encode("utf-8"))
    return size <= PROPOSAL_BYTE_CAP, size


@dataclass
class Phase:
    name: str
    raw: dict = field(default_factory=dict)


def current_phase() -> Phase:
    r = get_round()
    return Phase(name=r.get("phase", "unknown"), raw=r)


if __name__ == "__main__":
    # Smoke check — public, unauthenticated read only. Prints no secrets.
    try:
        print(json.dumps({"phase": current_phase().name}))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}))
