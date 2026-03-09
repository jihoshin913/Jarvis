"""
Tool router — determines which adapter handles a given tool and
delegates execution to the registry.

Keeping this as a separate layer means routing logic can grow
(e.g. fallback adapters, priority chains) without touching the executor.
"""

from __future__ import annotations
from typing import Any

from tools.tool_registry import ToolRegistry


class ToolRouter:
    def __init__(self, registry: ToolRegistry):
        self._registry = registry

    def route(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """
        Route a tool call to the correct adapter and return the result.

        Result format:
            {"status": "success", "result": ...}
            {"status": "error",   "error":  ...}
        """
        adapter_type = self._registry.get_adapter_type(tool_name) \
            if self._registry.is_registered(tool_name) else "unknown"

        result = self._registry.execute(tool_name, args)
        result["adapter"] = adapter_type
        return result
