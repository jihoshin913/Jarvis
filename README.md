# Jarvis Agent

A local agentic AI runtime that converts natural language commands into real computer actions — powered by Claude.

```
You: start my gaming setup
→ open_app("Discord")
→ open_app("Spotify")
→ open_app("League of Legends")

You: send an email to my manager saying I'll be late today
→ gmail_send_email(to="manager@company.com", subject="Running Late", body="...")

You: open my downloads folder and take a screenshot
→ open_folder("C:/Users/.../Downloads")
→ screenshot()

You: schedule a meeting with Sarah tomorrow at 2pm
→ google_calendar_create_event(title="Meeting with Sarah", start="2025-01-15T14:00:00", ...)

You: post in the #general Slack channel that the build is done
→ slack_post_message(channel="#general", text="Build is done!")

You: close spotify and open telegram
→ close_app("Spotify")
→ open_app("Telegram")

You: what's the weather like today?
→ open_url("https://wttr.in")

You: search for minecraft videos on youtube
→ open_url("https://www.youtube.com/results?search_query=minecraft")

You: find the pytorch repo on github
→ open_url("https://github.com/search?q=pytorch")

You: explain how transformers work
→ [Claude answers directly — no action needed]
```

---

## What it can do

- **Open any installed app** by name — scans your Start Menu automatically
- **Control your mouse and keyboard** — click, type, scroll, press keys
- **Send emails, create calendar events, post to Slack** via Composio integrations
- **Browse the web** — open URLs in your default browser
- **Read and write files**
- **Take screenshots**
- **Remember your habits** — stores command history and learns frequent workflows

---

## Architecture

```
User Input (natural language)
     ↓
Context Builder  (active window, running apps, time, memory)
     ↓
Master Agent / Claude API  (generates structured action plan)
     ↓
Validator  (safety checks, high-risk confirmation)
     ↓
Tool Router
  ├── Local Tools     (pyautogui, subprocess, win32com)
  └── Composio Tools  (Gmail, Google Calendar, Slack, Discord, Notion, GitHub...)
     ↓
Executor  (runs each action, logs results)
     ↓
Memory Store  (SQLite — command history, preferences, habits)
```

---

## Project Structure

```
jarvis-agent/
├── main.py                    # CLI entry point
├── config.py                  # API keys, safety settings
├── requirements.txt
├── agents/
│   └── master_agent.py        # Top-level orchestrator
├── tools/
│   ├── tool_registry.py       # Adapter pattern (Local + Composio)
│   ├── local_tools.py         # Windows automation (19 tools)
│   └── composio_tools.py      # App integrations via Composio
├── core/
│   ├── planner.py             # Claude API → action plan
│   └── validator.py           # Safety + high-risk confirmation
├── executor/
│   ├── executor.py            # Runs the plan step by step
│   └── tool_router.py         # Routes tools to correct adapter
├── memory/
│   ├── memory_store.py        # SQLite memory (commands, preferences)
│   └── context_builder.py     # Builds system context for Claude
└── auth/
    └── composio_auth.py       # OAuth connection helper
```

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set API keys

Edit `config.py` with your keys, or set environment variables:

```bash
set ANTHROPIC_API_KEY=sk-ant-...
set COMPOSIO_API_KEY=ak_...
```

Get your keys:
- **Anthropic** → [console.anthropic.com](https://console.anthropic.com)
- **Composio** → [app.composio.dev](https://app.composio.dev)

### 3. Run

```bash
# Local tools only (no Composio)
python main.py

# With Composio integrations (Gmail, Slack, etc.)
python main.py --composio
```

---

## Connecting Apps (Composio)

Run the OAuth flow once per app — tokens are stored permanently:

```bash
python auth/composio_auth.py connect gmail
python auth/composio_auth.py connect googlecalendar
python auth/composio_auth.py connect slack
python auth/composio_auth.py connect discord
python auth/composio_auth.py connect notion
python auth/composio_auth.py connect github

# Check what's connected
python auth/composio_auth.py
```

---

## Usage

```
You: start my gaming setup
You: open telegram
You: send an email to john@example.com about the meeting tomorrow
You: schedule lunch with Sarah tomorrow at noon
You: take a screenshot
You: open YouTube
You: close spotify
```

### CLI Commands

| Command | Description |
|---|---|
| `/tools` | List all available tools |
| `/preview` | Preview next action without executing |
| `/context` | Show current system context |
| `/history` | Show recent command history |
| `/set key=value` | Save a user preference |
| `/help` | Show help |
| `/quit` | Exit |

### Single-shot mode

```bash
python main.py "open discord and spotify"
```

---

## Local Tools

| Tool | Description |
|---|---|
| `open_app` | Open any installed application |
| `close_app` | Close a running application |
| `open_url` | Open a URL in the browser |
| `click` | Click at screen coordinates |
| `type_text` | Type text at cursor position |
| `press_key` | Press a key or combo (e.g. `ctrl+c`) |
| `screenshot` | Take a screenshot |
| `get_active_window` | Get the focused window title |
| `read_file` / `write_file` | Read or write files |
| `list_installed_apps` | List all apps found in Start Menu |
| `wait` | Pause between actions |

App resolution priority:
1. Start Menu scan (real `.exe` paths with arguments — e.g. Discord's `--processStart`)
2. Windows built-ins (`notepad`, `calc`, `explorer`)
3. Passthrough to Windows `start`

---

## Composio Integrations

Composio handles OAuth and API calls for 200+ apps. Enabled via `--composio` flag.

Configured toolkits: `GMAIL`, `GOOGLECALENDAR`, `SLACK`, `DISCORD`, `NOTION`, `SPOTIFY`, `GITHUB`

Add more in `config.py`:
```python
COMPOSIO_TOOLKITS = ["GMAIL", "GOOGLECALENDAR", "SLACK", ...]
```

---

## Safety

- **High-risk actions** (send email, post message, create calendar event) require explicit `y` confirmation before executing
- **Domain allow-list** for `open_url` — edit `ALLOWED_DOMAINS` in `config.py`
- **Tool whitelist** — only registered tools can be called; arbitrary code execution is not possible

---

## Memory

All commands and results are stored in `data/jarvis.db` (SQLite).

The agent uses this to:
- Show recent command history (`/history`)
- Infer frequent apps and workflows
- Build richer context for Claude on each request

---

## Tech Stack

| Component | Technology |
|---|---|
| AI reasoning | Claude (Anthropic API) |
| App integrations | Composio |
| Mouse/keyboard | pyautogui, pynput |
| App launching | subprocess, win32com |
| System info | psutil, pygetwindow |
| Memory | SQLite |
| Platform | Windows |
