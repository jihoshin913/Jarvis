"""
Local Windows tools — real computer actions executed via pyautogui,
subprocess, webbrowser, and Win32 APIs.

Each function is registered into the ToolRegistry by setup_local_tools().
"""

from __future__ import annotations
import os
import subprocess
import time
import webbrowser

from typing import Any

import pyautogui
import psutil

# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalize(name: str) -> str:
    return name.lower().strip()

def _get_launch_entry(name: str) -> dict | None:
    """Return {target, args} from Start Menu for the given app name, or None."""
    norm = _normalize(name)
    start_menu = scan_start_menu()
    if norm in start_menu:
        return start_menu[norm]
    for lnk_name, entry in start_menu.items():
        if norm in lnk_name or lnk_name in norm:
            return entry
    return None


# ── Start Menu scanner ────────────────────────────────────────────────────────

# Shortcut names to skip — uninstallers, help files, web links
_SKIP_KEYWORDS = {"uninstall", "help", "manual", "readme", "web site", "more...", "support"}

# Cache: normalized shortcut name → {"target": path, "args": args_string}
_START_MENU_CACHE: dict[str, dict] = {}


def scan_start_menu(force: bool = False) -> dict[str, dict]:
    """
    Scan both user and system Start Menu folders for .lnk shortcuts.
    Resolves each shortcut to its real target path + arguments using the Windows Shell COM API.

    Returns a dict of {normalized_name: {"target": path, "args": args_string}}.
    Results are cached after the first scan; pass force=True to rescan.
    """
    global _START_MENU_CACHE
    if _START_MENU_CACHE and not force:
        return _START_MENU_CACHE

    search_dirs = [
        os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    ]

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
    except Exception:
        return {}

    result: dict[str, dict] = {}

    for search_dir in search_dirs:
        for root, _, files in os.walk(search_dir):
            for fname in files:
                if not fname.lower().endswith(".lnk"):
                    continue

                display_name = fname[:-4]  # strip .lnk
                norm = _normalize(display_name)

                if any(kw in norm for kw in _SKIP_KEYWORDS):
                    continue

                lnk_path = os.path.join(root, fname)
                try:
                    shortcut = shell.CreateShortCut(lnk_path)
                    target = shortcut.Targetpath
                    if target and target.lower().endswith(".exe"):
                        # Don't overwrite user-level entries with system-level ones
                        if norm not in result:
                            result[norm] = {
                                "target": target,
                                "args": shortcut.Arguments or "",
                            }
                except Exception:
                    continue

    _START_MENU_CACHE = result
    return result


def _resolve_app(name: str) -> str:
    """
    Resolve an app name to a launchable path/command.
    Used only for the static APP_MAP fallback (built-ins with no Start Menu entry).
    """
    norm = _normalize(name)
    if norm in APP_MAP:
        return APP_MAP[norm]
    return name


# ── App control ───────────────────────────────────────────────────────────────

# Static map for common apps — takes priority over Start Menu scan
APP_MAP = {
    "discord":            "discord",
    "spotify":            "spotify",
    "chrome":             "chrome",
    "google chrome":      "chrome",
    "firefox":            "firefox",
    "edge":               "msedge",
    "microsoft edge":     "msedge",
    "notepad":            "notepad",
    "calculator":         "calc",
    "explorer":           "explorer",
    "file explorer":      "explorer",
    "slack":              "slack",
    "zoom":               "zoom",
    "steam":              "steam",
    "obs":                "obs64",
    "obs studio":         "obs64",
    "vlc":                "vlc",
    "vscode":             "code",
    "visual studio code": "code",
    "code":               "code",
    "cmd":                "cmd",
    "command prompt":     "cmd",
    "powershell":         "powershell",
    "league of legends":  "LeagueClient",
}


def open_app(name: str) -> str:
    """Open a desktop application by name."""
    # Prefer Start Menu entry (preserves target + arguments like Discord's --processStart)
    entry = _get_launch_entry(name)
    if entry:
        cmd = [entry["target"]]
        if entry["args"]:
            cmd += entry["args"].split()
        try:
            subprocess.Popen(cmd)
            return f"Opened {name}"
        except Exception as e:
            raise RuntimeError(f"Failed to open '{name}': {e}")

    # Fall back to static APP_MAP / passthrough via Windows `start`
    target = _resolve_app(name)
    try:
        subprocess.Popen(["start", "", target], shell=True)
        return f"Opened {name}"
    except Exception as e:
        raise RuntimeError(f"Failed to open '{name}': {e}")


def list_installed_apps() -> list[str]:
    """Return all app names discovered from the Start Menu."""
    apps = scan_start_menu()
    return sorted(apps.keys())


def close_app(name: str) -> str:
    """Close a running application by process name."""
    killed = []
    for proc in psutil.process_iter(["name"]):
        if _normalize(name) in _normalize(proc.info["name"]):
            proc.terminate()
            killed.append(proc.info["name"])
    if not killed:
        return f"No running process found matching '{name}'"
    return f"Closed: {', '.join(killed)}"


def get_running_apps() -> list[str]:
    """Return a list of currently running application names."""
    seen = set()
    apps = []
    for proc in psutil.process_iter(["name"]):
        n = proc.info["name"]
        if n and n not in seen:
            seen.add(n)
            apps.append(n)
    return sorted(apps)


# ── Browser ───────────────────────────────────────────────────────────────────

def open_url(url: str) -> str:
    """Open a URL in the default browser."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}"


def open_folder(path: str) -> str:
    """Open a folder in File Explorer."""
    expanded = os.path.expandvars(os.path.expanduser(path))
    subprocess.Popen(["explorer", expanded])
    return f"Opened folder: {expanded}"


# ── Mouse & keyboard ──────────────────────────────────────────────────────────

def click(x: int, y: int, button: str = "left") -> str:
    """Click at screen coordinates (x, y)."""
    pyautogui.click(x, y, button=button)
    return f"Clicked {button} at ({x}, {y})"


def double_click(x: int, y: int) -> str:
    """Double-click at screen coordinates."""
    pyautogui.doubleClick(x, y)
    return f"Double-clicked at ({x}, {y})"


def right_click(x: int, y: int) -> str:
    """Right-click at screen coordinates."""
    pyautogui.rightClick(x, y)
    return f"Right-clicked at ({x}, {y})"


def move_mouse(x: int, y: int) -> str:
    """Move the mouse to screen coordinates without clicking."""
    pyautogui.moveTo(x, y, duration=0.2)
    return f"Moved mouse to ({x}, {y})"


def type_text(text: str, interval: float = 0.03) -> str:
    """Type text at the current cursor position."""
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text}"


def press_key(key: str) -> str:
    """
    Press a keyboard key or key combination.
    Examples: 'enter', 'ctrl+c', 'alt+tab', 'win'
    """
    if "+" in key:
        keys = [k.strip() for k in key.split("+")]
        pyautogui.hotkey(*keys)
    else:
        pyautogui.press(key)
    return f"Pressed: {key}"


def scroll(direction: str, amount: int = 3) -> str:
    """Scroll the mouse wheel. direction: 'up' or 'down'."""
    clicks = amount if direction == "up" else -amount
    pyautogui.scroll(clicks)
    return f"Scrolled {direction} by {amount}"


# ── Screen ────────────────────────────────────────────────────────────────────

def screenshot(save_path: str = "") -> str:
    """
    Take a screenshot. Saves to save_path if provided,
    otherwise saves to data/screenshots/ with a timestamp.
    """
    if not save_path:
        os.makedirs("data/screenshots", exist_ok=True)
        save_path = f"data/screenshots/screenshot_{int(time.time())}.png"
    img = pyautogui.screenshot()
    img.save(save_path)
    return save_path


def get_screen_size() -> dict[str, int]:
    """Return the current screen resolution."""
    w, h = pyautogui.size()
    return {"width": w, "height": h}


# ── Window management ─────────────────────────────────────────────────────────

def get_active_window() -> str:
    """Return the title of the currently active window."""
    try:
        import pygetwindow as gw
        win = gw.getActiveWindow()
        return win.title if win else "Unknown"
    except Exception:
        return "pygetwindow unavailable"


def get_open_windows() -> list[str]:
    """Return titles of all visible windows."""
    try:
        import pygetwindow as gw
        return [w.title for w in gw.getAllWindows() if w.title]
    except Exception:
        return []


# ── File system (safe subset) ─────────────────────────────────────────────────

def read_file(path: str) -> str:
    """Read and return the contents of a text file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(path: str, content: str) -> str:
    """Write content to a file (creates or overwrites)."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"Written to {path}"


def list_directory(path: str = ".") -> list[str]:
    """List files and directories at the given path."""
    return os.listdir(path)


# ── Wait ──────────────────────────────────────────────────────────────────────

def wait(seconds: float) -> str:
    """Pause execution for a given number of seconds."""
    time.sleep(seconds)
    return f"Waited {seconds}s"


# ── Tool schemas (Anthropic tool-use format) ──────────────────────────────────

LOCAL_TOOL_SCHEMAS = [
    {
        "name": "open_app",
        "description": "Open a desktop application by name (e.g. Discord, Spotify, Chrome).",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "close_app",
        "description": "Close a running application by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Application name to close"}
            },
            "required": ["name"],
        },
    },
    {
        "name": "get_running_apps",
        "description": "Get a list of all currently running application processes.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "open_url",
        "description": "Open a URL in the default web browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to open"}
            },
            "required": ["url"],
        },
    },
    {
        "name": "open_folder",
        "description": "Open a folder in File Explorer. Use this for local folders like Downloads, Desktop, Documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Folder path, e.g. C:\\Users\\name\\Downloads or %USERPROFILE%\\Downloads"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "click",
        "description": "Click the mouse at specific screen coordinates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer", "description": "X coordinate"},
                "y": {"type": "integer", "description": "Y coordinate"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "double_click",
        "description": "Double-click at specific screen coordinates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "right_click",
        "description": "Right-click at specific screen coordinates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "move_mouse",
        "description": "Move the mouse cursor to specific screen coordinates without clicking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "x": {"type": "integer"},
                "y": {"type": "integer"},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "type_text",
        "description": "Type text at the current cursor position.",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to type"},
                "interval": {"type": "number", "description": "Delay between keystrokes in seconds", "default": 0.03},
            },
            "required": ["text"],
        },
    },
    {
        "name": "press_key",
        "description": "Press a key or key combination (e.g. 'enter', 'ctrl+c', 'alt+tab').",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Key or combo like 'ctrl+c'"}
            },
            "required": ["key"],
        },
    },
    {
        "name": "scroll",
        "description": "Scroll the mouse wheel up or down.",
        "input_schema": {
            "type": "object",
            "properties": {
                "direction": {"type": "string", "enum": ["up", "down"]},
                "amount": {"type": "integer", "description": "Number of scroll clicks", "default": 3},
            },
            "required": ["direction"],
        },
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot of the current screen.",
        "input_schema": {
            "type": "object",
            "properties": {
                "save_path": {"type": "string", "description": "Optional file path to save the screenshot"}
            },
        },
    },
    {
        "name": "get_screen_size",
        "description": "Get the current screen resolution.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_active_window",
        "description": "Get the title of the currently focused window.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_open_windows",
        "description": "Get a list of all currently open window titles.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "read_file",
        "description": "Read the contents of a text file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"}
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write text content to a file (creates or overwrites).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "list_directory",
        "description": "List files and folders in a directory.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path", "default": "."}
            },
        },
    },
    {
        "name": "wait",
        "description": "Wait for a specified number of seconds before the next action.",
        "input_schema": {
            "type": "object",
            "properties": {
                "seconds": {"type": "number", "description": "Seconds to wait"}
            },
            "required": ["seconds"],
        },
    },
    {
        "name": "list_installed_apps",
        "description": "List all applications found in the Start Menu. Useful for discovering what apps are installed before trying to open one.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

# Map tool name → function
LOCAL_TOOL_HANDLERS: dict[str, callable] = {
    "open_app":             open_app,
    "close_app":            close_app,
    "get_running_apps":     get_running_apps,
    "open_url":             open_url,
    "open_folder":          open_folder,
    "click":                click,
    "double_click":         double_click,
    "right_click":          right_click,
    "move_mouse":           move_mouse,
    "type_text":            type_text,
    "press_key":            press_key,
    "scroll":               scroll,
    "screenshot":           screenshot,
    "get_screen_size":      get_screen_size,
    "get_active_window":    get_active_window,
    "get_open_windows":     get_open_windows,
    "read_file":            read_file,
    "write_file":           write_file,
    "list_directory":       list_directory,
    "wait":                 wait,
    "list_installed_apps":  list_installed_apps,
}


def setup_local_tools(registry) -> None:
    """Register all local tools into the given ToolRegistry."""
    from tools.tool_registry import LocalToolAdapter

    adapter = LocalToolAdapter()
    registry.register_adapter("local", adapter)

    for schema in LOCAL_TOOL_SCHEMAS:
        name = schema["name"]
        handler = LOCAL_TOOL_HANDLERS.get(name)
        registry.register(name, schema, adapter_type="local", handler=handler)
