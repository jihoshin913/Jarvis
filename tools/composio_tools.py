"""
Composio tool setup — fetches real tool schemas from Composio at runtime.

Composio returns schemas already in Anthropic tool-use format,
so we pass them straight to the registry and planner.
"""

from __future__ import annotations

from config import COMPOSIO_API_KEY, COMPOSIO_USER_ID, COMPOSIO_TOOLKITS


def _make_client():
    from composio import Composio
    from composio_anthropic import AnthropicProvider
    return Composio(api_key=COMPOSIO_API_KEY, provider=AnthropicProvider())


def setup_composio_tools(registry, toolkits: list[str] | None = None) -> int:
    """
    Connect to Composio, fetch tool schemas for the configured toolkits,
    and register them into the registry.

    Returns the number of tools registered.
    """
    from tools.tool_registry import ComposioToolAdapter

    toolkits = toolkits or COMPOSIO_TOOLKITS

    adapter = ComposioToolAdapter(api_key=COMPOSIO_API_KEY, user_id=COMPOSIO_USER_ID)
    registry.register_adapter("composio", adapter)

    if not adapter.is_available():
        print("  [Composio] Not available — set COMPOSIO_API_KEY and install composio-anthropic")
        return 0

    try:
        composio = _make_client()

        # Fetch schemas for all toolkits — already in Anthropic format
        tools = composio.tools.get(COMPOSIO_USER_ID, toolkits=toolkits)

        count = 0
        for schema in tools:
            name = schema.get("name", "")
            if name:
                registry.register(name, schema, adapter_type="composio")
                count += 1

        print(f"  [Composio] Loaded {count} tools from: {', '.join(toolkits)}")
        return count

    except Exception as e:
        print(f"  [Composio] Failed to load tools: {e}")
        return 0


def connect_app(app_name: str) -> None:
    """
    Run the OAuth flow to connect an app (e.g. 'gmail', 'slack').
    Call this once per app — Composio stores the tokens permanently.

    Example:
        python auth/composio_auth.py connect gmail
    """
    try:
        composio = _make_client()
        # toolkits.authorize() returns a ConnectionRequest with a redirect_url
        connection = composio.toolkits.authorize(
            user_id=COMPOSIO_USER_ID,
            toolkit=app_name.upper(),
        )
        print(f"\nOpen this URL to connect {app_name}:\n\n  {connection.redirect_url}\n")
        print("After completing the login, your account is saved. You won't need to do this again.")
    except Exception as e:
        print(f"Failed to initiate connection for {app_name}: {e}")


def list_connected_apps() -> list[str]:
    """Return names of apps the user has already connected via OAuth."""
    try:
        composio = _make_client()
        # 0.10.x API: user_ids= (plural, list)
        response = composio.connected_accounts.list(user_ids=[COMPOSIO_USER_ID])
        items = getattr(response, "items", []) or []
        return [getattr(a, "toolkit_slug", str(a)) for a in items]
    except Exception as e:
        print(f"Failed to list connected apps: {e}")
        return []
