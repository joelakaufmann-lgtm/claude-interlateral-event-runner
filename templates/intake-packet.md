# Registration Intake Packet

Built from Joel's actual practice frame so registration is fast and on-brand. Opus fills
this in, then the executor passes it to `register()`. Keep it factual; no fabricated
authorities or credentials.

## Principal
- **Name:** Joel A. Kaufmann
- **Firm:** Kaufmann Law (NV / CA; national practice)
- **Agent handle:** joel-agent-lq9k  (set `ILPT_AGENT_NAME` to match)

## Practice frame (for proposal/topic relevance)
- Estate planning; asset protection and business structuring; civil litigation.
- Professional responsibility / legal ethics (NV + CA) — priority lens.
- Standing interest: the ethics of AI for attorneys and judges; raising the ethical floor.

## Posture for this platform
- **Authorities are framework-only** pending primary-source verification. Never fabricate
  cases, statutes, or holdings.
- **Delegated authorization** is both the event theme and how this agent operates:
  warrant / warden / receipt (see `references/governance.md`).

## Registration fields (map to POST /api/register)
- `agent_name`: joel-agent-lq9k
- `principal`: Joel A. Kaufmann, Kaufmann Law
- `mandate_label`: explicit
- `intent`: "Register as Joel's instrument for this round under a bounded, revocable warrant."
- `intake_summary`: 2–3 lines drawn from the practice frame above, tailored to the round theme.

## Reminders
- The token is minted only after Joel personally enters the emailed 8-digit code and accepts
  CC BY 4.0 consent. The agent never touches the code or the consent box.
- Membership lands `pending`; poll `register/status/<agent_name>` until `registered/active`.
