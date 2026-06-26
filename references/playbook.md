# Playbook — Model Allocation & Next-Event Checklist

## Model allocation

| Task | Model | Why |
|---|---|---|
| Topic/proposal development; Jot contributions; red-team critique; summarization | **Opus 4.8** | High-judgment, citation-disciplined drafting — the work that earns votes and respect. |
| Deciding *which* entries to vote and *what* to post | **Opus 4.8** (with Joel's sign-off) | Judgment + approval; never delegate the "what." |
| Substantive Jot edits (uniqueness, replay-safety, re-read discipline) | **Opus 4.8** (or Sonnet on pre-validated anchors) | Keep substance edits on the stronger model. |
| Casting pre-approved votes; polling; status/registration; payload validation; phase-flip watcher | **Sonnet** | Deterministic, latency-sensitive, no judgment once the "what" is fixed. |
| Pure notification ("ping when phase flips"); standing watch loop | **Haiku** | Cheapest watch loop. |

Governing rule: **the expensive model owns the *what*; the cheap model owns the
*when/do-it*.** That single split is the fix for the missed vote.

## Why latency is a feature in voting

A fast model polling and firing beats a heavyweight reasoner deliberating while the window
closes. Reserve deliberation for *before* the window opens; pre-stage the mandate; let the
lean executor fire the instant `phase == voting`.

## Next-event checklist

- [ ] Load the participant token into `ILPT_TOKEN`; set `ILPT_AGENT_NAME`; never echo it; rotate after the event.
- [ ] Confirm the event slug in `references/api-map.md` matches the current round.
- [ ] Opus: develop topics/proposals; keep a condensed ≤ 9.5 KB variant ready; reserve full text for the Jot.
- [ ] Validate proposal payload bytes (`scripts/validate_payload.py`) before POST; up-gate submission to Joel.
- [ ] Capture decisions as a pre-staged mandate set (`mandate.yaml`) the instant Joel makes them.
- [ ] Stand up the watcher (`scripts/watch_round.py`) — in-session Haiku sub-agent and/or a scheduled task for the event window.
- [ ] On `voting`: executor casts the pre-approved votes, confirms 201s, tracks the cap of 3 (no double-fire).
- [ ] Keep substantive Jot edits on Opus with re-read-before-edit + replay-safe anchoring.
- [ ] Apply the warrant/warden model: per-model allowlists, provenance gate, up-gate for binding acts, mandate receipts, token-rotation revocation.
- [ ] Debrief with an honest ledger; convert any new slip into a system.

## The "faster, more organized" answer

The Day-04 gap was not reasoning — it was operational discipline under time pressure (the
votes) and secret hygiene (the token). This architecture closes exactly those gaps: an Opus
orchestrator for quality, a lean Sonnet/Haiku executor for speed and reliability, a watcher
so nothing is missed, a reusable client so nothing is re-derived, and pre-staged mandates so
execution never waits on a conversation. Strongest-model reasoning *and* lean-model speed,
without choosing between them.
