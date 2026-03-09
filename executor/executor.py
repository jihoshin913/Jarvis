"""
Executor — walks through a validated action plan and runs each step.

Responsibilities:
  - Validate each action before running
  - Request user confirmation for high-risk tools
  - Log every execution to memory
  - Collect and return results
"""

from __future__ import annotations
from typing import Any

from core.validator import Validator
from executor.tool_router import ToolRouter
from memory.memory_store import MemoryStore


class Executor:
    def __init__(
        self,
        router: ToolRouter,
        validator: Validator,
        memory: MemoryStore,
    ):
        self._router    = router
        self._validator = validator
        self._memory    = memory

    def run_plan(
        self,
        plan: list[dict[str, Any]],
        command_id: int,
        confirm_fn: callable | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a list of actions sequentially.

        Args:
            plan:        List of {tool, args} dicts from the planner.
            command_id:  Memory row ID for this command (for logging).
            confirm_fn:  Callable(prompt: str) -> bool for high-risk confirmation.
                         Defaults to a CLI prompt if not provided.

        Returns:
            List of result dicts, one per action.
        """
        if confirm_fn is None:
            confirm_fn = self._default_confirm

        # Validate the whole plan first
        plan_check = self._validator.validate_plan(plan)
        if not plan_check.allowed:
            return [{"tool": "_plan_blocked", "status": "error", "error": plan_check.reason}]

        results = []

        for action in plan:
            tool = action.get("tool", "")
            args = action.get("args", {})

            # ── Internal pseudo-tools ─────────────────────────────────────────
            if tool == "_message":
                print(f"\n  Jarvis: {args.get('text', '')}\n")
                results.append({"tool": "_message", "status": "success"})
                continue

            # ── Validate ──────────────────────────────────────────────────────
            check = self._validator.validate_action(action)

            if not check.allowed:
                result = {"tool": tool, "status": "blocked", "error": check.reason}
                print(f"  [BLOCKED] {tool}: {check.reason}")
                self._log(command_id, tool, args, "blocked", check.reason)
                results.append(result)
                continue

            # ── High-risk confirmation ────────────────────────────────────────
            if check.requires_confirmation:
                prompt = f"\n  ⚠  High-risk action: {tool}\n  Args: {args}\n  {check.reason}\n  Proceed? [y/N] "
                if not confirm_fn(prompt):
                    result = {"tool": tool, "status": "cancelled"}
                    print(f"  [CANCELLED] {tool}")
                    self._log(command_id, tool, args, "cancelled", "User declined")
                    results.append(result)
                    continue

            # ── Execute ───────────────────────────────────────────────────────
            print(f"  → {tool}({self._fmt_args(args)})")
            result = self._router.route(tool, args)
            result["tool"] = tool

            status_icon = "✓" if result["status"] == "success" else "✗"
            if result["status"] == "success":
                print(f"    {status_icon} {result.get('result', '')}")
            else:
                print(f"    {status_icon} Error: {result.get('error', '')}")

            self._log(command_id, tool, args, result["status"], result)
            results.append(result)

        return results

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _log(self, command_id, tool, args, status, result):
        self._memory.log_execution(command_id, tool, args, status, result)

    @staticmethod
    def _fmt_args(args: dict) -> str:
        parts = [f"{k}={repr(v)}" for k, v in args.items()]
        return ", ".join(parts)

    @staticmethod
    def _default_confirm(prompt: str) -> bool:
        response = input(prompt).strip().lower()
        return response in ("y", "yes")
