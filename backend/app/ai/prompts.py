"""Prompt text for fact extraction.

The model's job here is comprehension, not pricing and not proposal design: it
reads the brief and returns five facts. Candidate scopes are constructed by the
server (`app/ai/candidates.py`) and priced by `app.rules`.

Measured 2026-10-30 against this gateway: asking the model to emit a nested
object with candidate scopes produced a different JSON shape on most attempts
(persona reports, markdown fences), while the five-key fact sheet below matched
on every attempt. The narrow schema is the one that survives.
"""

from __future__ import annotations

from datetime import date

from app.requirements.models import RequirementMessage
from app.rules.types import RuleSet

PROMPT_VERSION = "facts-v6"

SYSTEM_PROMPT = (
    "Extract facts from a client brief for a web design studio. "
    "Return JSON only: no prose, no markdown, no code fences.\n"
    "Keys: pages (integer|null), budget_usd (number|null), deadline_days (integer|null), "
    "assets_ready (boolean|null), features (array of strings).\n"
    "Use null when the brief does not say. Never guess a price. "
    "Never add keys.\n"
    "features lists what the client asked for, as short snake_case codes. Use the capability "
    "codes when they match, and still name asks this studio does not offer "
    "(for example on_site_ordering) — never silently narrow the request.\n"
    'Example: {"pages": 2, "budget_usd": 800, "deadline_days": 21, "assets_ready": true, '
    '"features": ["landing_pages", "on_site_ordering"]}'
)


def build_user_prompt(
    *,
    client_name: str,
    client_business: str,
    messages: list[RequirementMessage],
    rules: RuleSet,
    today: date,
) -> str:
    lines = [
        f"Today: {today.isoformat()}",
        f"Client: {client_name} — {client_business}".rstrip(" —"),
        "Capability codes: " + ", ".join(sorted(rules.capabilities)),
        "",
        "Brief:",
    ]
    for message in messages:
        header = f"[rev {message.revision} · {message.author}]"
        lines.append(header)
        lines.append(message.body)
        recorded = []
        if message.budget_minor is not None:
            recorded.append(f"budget {message.budget_minor / 100:.2f} USD")
        if message.deadline is not None:
            recorded.append(f"deadline {message.deadline.isoformat()}")
        if message.assets_ready is not None:
            recorded.append("assets " + ("ready" if message.assets_ready else "not ready"))
        if recorded:
            lines.append("(recorded: " + "; ".join(recorded) + ")")
        lines.append("")
    lines.append("Return the JSON now.")
    return "\n".join(lines)
