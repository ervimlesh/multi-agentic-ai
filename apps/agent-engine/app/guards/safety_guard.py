"""Risk classification for proposed browser actions (Flow B).

Decides whether an action needs explicit human approval before it runs. The
risky categories match what the user listed: payment, delete, submit sensitive
form, withdraw, password/account change.

Deterministic keyword matching for now (fast, free, auditable). A small LLM
classifier (GROQ_MODEL_FAST) can replace this later for fuzzier judgement.
"""
from __future__ import annotations

from dataclasses import dataclass

# category -> trigger keywords (checked against the action description + type)
_RISK_RULES: dict[str, tuple[str, ...]] = {
    "payment": (
        "pay",
        "payment",
        "purchase",
        "buy",
        "checkout",
        "place order",
        "complete order",
        "confirm order",
        "subscribe",
        "billing",
    ),
    "deletion": ("delete", "remove", "destroy", "wipe", "cancel order"),
    "submit_sensitive": ("submit", "send form", "apply", "confirm"),
    "withdraw": ("withdraw", "transfer", "send money", "payout"),
    "account_change": ("password", "change email", "2fa", "security settings", "deactivate"),
}

_HUMAN_LABELS = {
    "payment": "Payment / purchase",
    "deletion": "Deletion",
    "submit_sensitive": "Sensitive form submission",
    "withdraw": "Withdrawal / money transfer",
    "account_change": "Account / security change",
}


@dataclass
class RiskVerdict:
    risky: bool
    category: str | None
    label: str | None
    reason: str | None


def classify_action(action: dict) -> RiskVerdict:
    """Classify a proposed action dict like {type, description, target}."""
    haystack = " ".join(
        str(action.get(k, "")) for k in ("type", "description", "target", "value")
    ).lower()

    for category, keywords in _RISK_RULES.items():
        hit = next((kw for kw in keywords if kw in haystack), None)
        if hit:
            return RiskVerdict(
                risky=True,
                category=category,
                label=_HUMAN_LABELS[category],
                reason=f"Action looks like a {_HUMAN_LABELS[category].lower()} "
                f"(matched “{hit}”) — needs your approval before it runs.",
            )

    return RiskVerdict(risky=False, category=None, label=None, reason=None)
