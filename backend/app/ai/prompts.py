"""Prompt text for fact extraction.

The model's job here is comprehension, not pricing and not proposal design: it
reads the brief and returns five facts. Candidate scopes are constructed by the
server (`app/ai/candidates.py`) and priced by `app.rules`.

Measured 2026-10-30 against this gateway: asking for a nested object with
candidate scopes produced a different JSON shape on most attempts. The five-key
fact sheet is better but not reliable — 7/19 on one run, 9/19 on another — and
the failures are mostly markdown-fenced JSON with invented keys. v7 states the
contract first, forbids extra keys explicitly, and keeps one filled example.
Prompt changes alone are reported as measurements, never assumed to be enough.
"""

from __future__ import annotations

from datetime import date

from app.requirements.models import RequirementMessage
from app.rules.types import RuleSet

PROMPT_VERSION = "facts-v7"

CONTRACT = (
    '{"pages": integer|null, "budget_usd": number|null, "deadline_days": integer|null, '
    '"assets_ready": boolean|null, "features": [string]}'
)

SYSTEM_PROMPT = (
    "OUTPUT CONTRACT: one JSON object with exactly these five keys and no others: "
    + CONTRACT
    + "\n"
    "Renaming keys, nesting them under client/project/scope, or adding summary/status/decision "
    "is a failure. Do not use triple backticks. Do not write prose before or after the JSON.\n"
    "Use null when the brief does not say. Never guess a price.\n"
    "features lists what the client asked for as short snake_case codes; use the capability "
    "codes from the input when they match, and still name asks this studio does not offer "
    "(for example on_site_ordering).\n"
    'Example of the complete answer for a different brief: {"pages": 2, "budget_usd": 800, '
    '"deadline_days": 21, "assets_ready": true, '
    '"features": ["landing_pages", "on_site_ordering"]}'
    "\nReturn only that object."
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
    # The contract travels with the payload as well as in the system message:
    # this gateway has been observed ignoring instructions that only live there,
    # in which case the model treats the brief as a document to summarise.
    return SYSTEM_PROMPT + "\n\n" + "\n".join(lines)
