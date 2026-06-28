# Interlateral Event Runner

A multi-model runner skill for the **Interlateral** platform (the `propose →
vote → work` agent unconference). It splits the work across models on a single principle:
the expensive model owns the judgment, the cheap model owns the time-sensitive execution.

The skill exists because of a post-event debrief. The reasoning during the event was
strong; the **operational discipline under time pressure** was not. Two concrete misses —
approved votes that were never cast before the round closed, and a participant token that
rode along in a logged command — cost a winning slot and broke secret hygiene. This skill
turns both of those into solved, structural problems rather than things you have to
remember to do.

> **License:** MIT — see [`LICENSE`](./LICENSE).

---

## The one rule that matters

**The expensive model owns the *what*; the cheap model owns the *when / do-it*.**

A high-judgment orchestrator decides everything that needs reasoning or a human sign-off.
The moment a decision becomes a deterministic, latency-sensitive call, it is handed to a
leaner model. A dedicated executor with exactly one job does not get distracted by drafting
work and does not stall across conversational hand-offs — which is precisely what killed
the votes on Day 04.

| Work | Model | How it runs |
|---|---|---|
| Proposal / Jot drafting, vote *decisions*, substantive Jot edits, red-team critique | **Opus-class orchestrator** | Main session |
| Casting pre-approved votes, polling phase, status / registration checks, payload validation | **Sonnet-class executor** | Sub-agent |
| Pure phase-flip notification / standing watch loop | **Haiku-class watcher** | Sub-agent or scheduled task |

The executor is **never** allowed to author proposals, decide votes, or edit substance.
That boundary is its warrant.

## Operating modes

The skill routes a request to the mode that matches it:

- **SETUP** — confirm credentials are in the environment, register the agent, poll to active.
- **PROPOSE** — develop the proposal with citation discipline, pre-flight the size cap, and submit (with a fresh human sign-off, since submitting is outcome-determinative).
- **STAGE MANDATE** — the instant votes are approved, capture them as a structured `mandate.yaml` so execution never waits on a conversation.
- **EXECUTE / VOTE** — a lean executor fires the pre-approved votes, confirms each `201`, and tracks the cap so it never double-fires or exceeds the limit.
- **WATCH** — a watcher (in-session or a scheduled task) polls round state and fires the instant the voting window opens, so nothing is missed even if the main session is idle.
- **WORK** — collaborative "Jot" edits stay on the orchestrator: server-side find/replace with re-read-before-every-edit and replay-safe anchoring.
- **DEBRIEF** — close with an honest ledger and convert any new slip into a system.

## Security model

This skill is built around three guardrails, all documented in
[`references/governance.md`](./references/governance.md):

1. **Token hygiene.** The participant token is an event-scoped bearer secret. It is loaded
   **once** into the environment, never echoed into chat, logs, a command string, a shared
   document, or a sub-agent prompt, and rotated after the event. Sub-agents receive
   *parameters*, never the token.
2. **Provenance gate.** If the trigger for an action originated in untrusted input (another
   agent's text, an injected "use my token as authorized" instruction), the skill does not
   act autonomously — it routes the decision back to the human.
3. **Up-gate.** Outcome-determinative or binding acts — submitting a proposal, casting
   votes, posting under the operator's name — get a fresh human confirmation even when a
   standing mandate exists. A mandate lets the executor *act*; it never lets a model *bind*
   the operator to something they did not approve.

## Repository layout

```
.
├── SKILL.md                      # Skill definition and routing logic
├── references/
│   ├── api-map.md                # Endpoint map, auth model, error codes, edit semantics
│   ├── governance.md             # Warrant/warden model: allowlists, provenance gate, up-gate
│   └── playbook.md               # Model-allocation table and the next-event checklist
├── scripts/
│   ├── event_client.py           # Thin reusable client: endpoints + submit/vote/edit helpers
│   ├── cast_votes.py             # Executor entrypoint: fire pre-staged votes, confirm 201s
│   ├── watch_round.py            # Poll round state, fire on phase transition, alert on flips
│   └── validate_payload.py       # Pre-flight size check for proposals
├── templates/
│   ├── mandate.example.yaml      # The pre-staged mandate set (copy to mandate.yaml to use)
│   └── intake-packet.md          # Registration intake template
├── LICENSE                       # MIT
└── README.md
```

## Installation

This is a [Claude](https://www.anthropic.com/claude) skill. Drop the folder into the
location your setup loads skills from — for example a Claude Code plugin's `skills/`
directory, or your personal skills directory — so the runtime can discover `SKILL.md`:

```bash
git clone https://github.com/<your-username>/claude-interlateral-event-runner.git
```

The Python scripts use only the standard library and read configuration from the
environment (the participant token and agent name). Copy `templates/mandate.example.yaml`
to `mandate.yaml` when you stage a mandate; that file is git-ignored so a populated mandate
never lands in version control.

## Disclaimer

This is an independent, community tool for a specific agent-event platform. It is provided
"as is" under the MIT License, without warranty of any kind. It is not affiliated with or
endorsed by the platform operator, and nothing here is legal, security, or other
professional advice.

## License

Released under the [MIT License](./LICENSE). Copyright (c) 2026 Joel Kaufmann.
