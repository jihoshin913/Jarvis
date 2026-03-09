"""
Master Agent — the top-level orchestrator.

Wires together:
  ContextBuilder → Planner → Validator → Executor → MemoryStore

This is the single object main.py interacts with.
"""

from __future__ import annotations
from typing import Any

from core.planner import Planner
from core.validator import Validator
from executor.executor import Executor
from executor.tool_router import ToolRouter
from memory.context_builder import ContextBuilder
from memory.memory_store import MemoryStore
from tools.local_tools import setup_local_tools
from tools.composio_tools import setup_composio_tools
from tools.tool_registry import ToolRegistry


class MasterAgent:
    def __init__(self, enable_composio: bool = False):
        # ── Infrastructure ────────────────────────────────────────────────────
        self.memory   = MemoryStore()
        self.registry = ToolRegistry()
        self.context  = ContextBuilder(self.memory)
        self.planner  = Planner()
        self.validator = Validator(self.registry)
        self.router   = ToolRouter(self.registry)
        self.executor = Executor(self.router, self.validator, self.memory)

        # ── Register tools ────────────────────────────────────────────────────
        setup_local_tools(self.registry)

        if enable_composio:
            setup_composio_tools(self.registry)

    def run(self, user_input: str) -> list[dict[str, Any]]:
        """
        Full pipeline:
          1. Build context
          2. Generate plan via Claude
          3. Execute plan (with validation + confirmation)
          4. Update memory
          5. Return results
        """
        user_input = user_input.strip()
        if not user_input:
            return []

        print(f"\n  Building context...")
        context_block = self.context.build_prompt_block()

        print(f"  Planning...")
        tool_schemas = self.registry.get_available_tool_schemas()
        plan = self.planner.generate_plan(user_input, tool_schemas, context_block)

        if not plan:
            print("  No actions generated.")
            return []

        print(f"  Plan ({len(plan)} step{'s' if len(plan) != 1 else ''}):")

        # Log the command before execution
        command_id = self.memory.log_command(user_input, plan)

        # Execute
        results = self.executor.run_plan(plan, command_id)

        # Update command success status
        all_ok = all(r.get("status") in ("success", "cancelled") for r in results)
        self.memory.update_command_status(command_id, all_ok)

        return results

    def preview(self, user_input: str) -> str:
        """Return a plain-English preview of what the agent would do, without executing."""
        context_block = self.context.build_prompt_block()
        return self.planner.explain(user_input, context_block)

    def set_preference(self, key: str, value: Any):
        self.memory.set_preference(key, value)

    def get_tools(self) -> list[str]:
        return self.registry.list_tools()
