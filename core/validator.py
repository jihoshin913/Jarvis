"""
Validator — checks every planned action before the executor runs it.

Enforces:
  - Tool whitelist (only registered tools allowed)
  - App/domain allow-lists
  - High-risk confirmation requirement
  - Plan size limit
"""

from __future__ import annotations
from dataclasses import dataclass

from config import ALLOWED_DOMAINS, HIGH_RISK_TOOLS, MAX_ACTIONS_PER_PLAN


@dataclass
class ValidationResult:
    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False


class Validator:
    def __init__(self, registry):
        self._registry = registry

    def validate_plan(self, plan: list[dict]) -> ValidationResult:
        """Validate an entire plan before execution starts."""
        if len(plan) > MAX_ACTIONS_PER_PLAN:
            return ValidationResult(
                allowed=False,
                reason=f"Plan has {len(plan)} actions (max {MAX_ACTIONS_PER_PLAN}).",
            )
        return ValidationResult(allowed=True)

    def validate_action(self, action: dict) -> ValidationResult:
        """Validate a single action dict {tool, args}."""
        tool = action.get("tool", "")
        args = action.get("args", {})

        # Internal pseudo-tools (like _message) always pass
        if tool.startswith("_"):
            return ValidationResult(allowed=True)

        # Must be a registered tool
        if not self._registry.is_registered(tool):
            return ValidationResult(
                allowed=False,
                reason=f"Unknown tool '{tool}'. Only registered tools are allowed.",
            )

        # Domain allow-list check
        if tool == "open_url":
            url = args.get("url", "")
            if not any(d in url for d in ALLOWED_DOMAINS):
                return ValidationResult(
                    allowed=False,
                    reason=f"Domain not allowed: {url}",
                )

        # High-risk tool → needs user confirmation
        if tool in HIGH_RISK_TOOLS:
            return ValidationResult(
                allowed=True,
                requires_confirmation=True,
                reason=f"'{tool}' is a high-risk action and requires your approval.",
            )

        return ValidationResult(allowed=True)
