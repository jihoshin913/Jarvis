from __future__ import annotations
from dataclasses import dataclass

from config import HIGH_RISK_TOOLS, MAX_ACTIONS_PER_PLAN


@dataclass
class ValidationResult:
    allowed: bool
    reason: str = ""
    requires_confirmation: bool = False


class Validator:
    def __init__(self, registry):
        self._registry = registry

    def validate_plan(self, plan: list[dict]) -> ValidationResult:
        if len(plan) > MAX_ACTIONS_PER_PLAN:
            return ValidationResult(
                allowed=False,
                reason=f"Plan has {len(plan)} actions (max {MAX_ACTIONS_PER_PLAN}).",
            )
        return ValidationResult(allowed=True)

    def validate_action(self, action: dict) -> ValidationResult:
        tool = action.get("tool", "")

        if tool.startswith("_"):
            return ValidationResult(allowed=True)

        if not self._registry.is_registered(tool):
            return ValidationResult(
                allowed=False,
                reason=f"Unknown tool '{tool}'. Only registered tools are allowed.",
            )

        if tool in HIGH_RISK_TOOLS:
            return ValidationResult(
                allowed=True,
                requires_confirmation=True,
                reason=f"'{tool}' is a high-risk action and requires your approval.",
            )

        return ValidationResult(allowed=True)
