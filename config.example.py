import os

# ── Claude API ────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY_HERE")
CLAUDE_MODEL = "claude-sonnet-4-6"

# ── Composio ──────────────────────────────────────────────────────────────────
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY", "YOUR_COMPOSIO_API_KEY_HERE")
COMPOSIO_USER_ID = os.getenv("COMPOSIO_USER_ID", "jarvis-local-user")
COMPOSIO_TOOLKITS = ["GMAIL", "GOOGLECALENDAR", "SLACK", "DISCORD", "NOTION", "SPOTIFY", "GITHUB"]

# ── Memory ────────────────────────────────────────────────────────────────────
MEMORY_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "jarvis.db")

# ── Safety ────────────────────────────────────────────────────────────────────
ALLOWED_DOMAINS = [
    "youtube.com", "google.com", "github.com", "notion.so",
    "spotify.com", "reddit.com", "twitch.tv", "discord.com",
    "stackoverflow.com", "docs.python.org",
]

HIGH_RISK_TOOLS = [
    "gmail_send_email",
    "google_calendar_create_event",
    "slack_post_message",
    "discord_send_message",
    "delete_file",
    "notion_create_page",
]

# ── Rate limiting ─────────────────────────────────────────────────────────────
MAX_ACTIONS_PER_PLAN = 20
MAX_PLANS_PER_MINUTE = 10
