"""
Tool Registry — adapter pattern so Composio (or any future backend)
can be plugged in without touching the planner, router, or executor.

Adding a new adapter in Phase 2:
    registry.register_adapter("composio", ComposioToolAdapter())
    registry.register("gmail_send_email", schema, adapter_type="composio")
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


# ── Base adapter interface ─────────────────────────────────────────────────────

class ToolAdapter(ABC):
    """All tool backends implement this interface."""

    @abstractmethod
    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool and return a result dict with at least a 'status' key."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this adapter is configured and ready."""
        ...


# ── Local adapter (Phase 1) ───────────────────────────────────────────────────

class LocalToolAdapter(ToolAdapter):
    """
    Runs Python functions registered directly in the tool registry.
    The function implementations live in tools/local_tools.py.
    """

    def __init__(self):
        self._handlers: dict[str, callable] = {}

    def register_handler(self, tool_name: str, fn: callable):
        self._handlers[tool_name] = fn

    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        handler = self._handlers.get(tool_name)
        if not handler:
            return {"status": "error", "error": f"No local handler for '{tool_name}'"}
        try:
            result = handler(**args)
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def is_available(self) -> bool:
        return True


# ── Composio adapter ─────────────────────────────────────────────────────────

class ComposioToolAdapter(ToolAdapter):
    """
    Executes tools via the Composio SDK.

    Composio handles OAuth, token storage, and API calls for 200+ apps
    (Gmail, Google Calendar, Slack, Discord, Notion, Spotify, GitHub, etc.)

    Setup:
        pip install composio-anthropic
        composio login          # authenticate your Composio account
        composio add gmail      # connect a specific app (runs OAuth flow)
    """

    def __init__(self, api_key: str, user_id: str = "jarvis-local-user"):
        self.api_key = api_key
        self.user_id = user_id
        self._composio = None

        if self.is_available():
            try:
                from composio import Composio
                from composio_anthropic import AnthropicProvider
                self._composio = Composio(
                    api_key=api_key,
                    provider=AnthropicProvider(),
                )
            except ImportError:
                pass  # is_available() will return False

    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if not self._composio:
            return {
                "status": "error",
                "error": "Composio not initialized. Run: pip install composio-anthropic",
            }
        try:
            # Execute the tool directly via Composio SDK
            # 0.10.x API: slug= and arguments= (not tool_name= and input=)
            result = self._composio.tools.execute(
                slug=tool_name,
                arguments=args,
                user_id=self.user_id,
            )
            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def is_available(self) -> bool:
        if not self.api_key or self.api_key == "YOUR_COMPOSIO_API_KEY_HERE":
            return False
        try:
            import composio  # noqa: F401
            return True
        except ImportError:
            return False


# ── Registry ──────────────────────────────────────────────────────────────────

class ToolRegistry:
    """
    Central registry that maps tool names → (schema, adapter_type).

    The executor never needs to know which backend runs a tool —
    it just calls registry.execute(tool_name, args).
    """

    def __init__(self):
        self._tools: dict[str, dict] = {}          # name → {schema, adapter_type}
        self._adapters: dict[str, ToolAdapter] = {} # type → adapter instance

    # ── Adapter management ────────────────────────────────────────────────────

    def register_adapter(self, adapter_type: str, adapter: ToolAdapter):
        self._adapters[adapter_type] = adapter

    def get_adapter(self, adapter_type: str) -> ToolAdapter:
        adapter = self._adapters.get(adapter_type)
        if not adapter:
            raise KeyError(f"No adapter registered for type '{adapter_type}'")
        return adapter

    # ── Tool management ───────────────────────────────────────────────────────

    def register(
        self,
        name: str,
        schema: dict,
        adapter_type: str = "local",
        handler: callable | None = None,
    ):
        """
        Register a tool.

        Args:
            name:         Tool name (matches schema["name"])
            schema:       Anthropic tool schema dict
            adapter_type: Which adapter runs this tool ("local", "composio", ...)
            handler:      For local tools — the Python function to call
        """
        self._tools[name] = {"schema": schema, "adapter_type": adapter_type}

        if handler and adapter_type == "local":
            local: LocalToolAdapter = self._adapters.get("local")
            if local:
                local.register_handler(name, handler)

    def get_tool_schemas(self) -> list[dict]:
        """Return all schemas in Anthropic tool-use format for the planner."""
        return [entry["schema"] for entry in self._tools.values()]

    def get_available_tool_schemas(self) -> list[dict]:
        """Only return schemas whose adapter is available (configured)."""
        schemas = []
        for name, entry in self._tools.items():
            adapter = self._adapters.get(entry["adapter_type"])
            if adapter and adapter.is_available():
                schemas.append(entry["schema"])
        return schemas

    def is_registered(self, tool_name: str) -> bool:
        return tool_name in self._tools

    def get_adapter_type(self, tool_name: str) -> str:
        return self._tools[tool_name]["adapter_type"]

    # ── Execution ─────────────────────────────────────────────────────────────

    def execute(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in self._tools:
            return {"status": "error", "error": f"Unknown tool '{tool_name}'"}

        adapter_type = self._tools[tool_name]["adapter_type"]
        adapter = self._adapters.get(adapter_type)

        if not adapter:
            return {"status": "error", "error": f"No adapter for type '{adapter_type}'"}

        if not adapter.is_available():
            return {
                "status": "error",
                "error": f"Adapter '{adapter_type}' is not configured.",
            }

        return adapter.execute(tool_name, args)

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
