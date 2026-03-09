"""
Context builder — assembles a rich snapshot of the user's current system
state and injects it into the planner's system prompt.
"""

from __future__ import annotations
import datetime
import os
import platform

import psutil

from memory.memory_store import MemoryStore


class ContextBuilder:
    def __init__(self, memory: MemoryStore):
        self._memory = memory

    def build(self) -> dict:
        """Return a structured context dict."""
        return {
            "system":   self._system_info(),
            "time":     self._time_info(),
            "apps":     self._app_info(),
            "memory":   self._memory_info(),
            "user":     self._user_info(),
        }

    def build_prompt_block(self) -> str:
        """Return a formatted string ready to inject into a system prompt."""
        ctx = self.build()

        lines = [
            "=== SYSTEM CONTEXT ===",
            f"Time:            {ctx['time']['now']}",
            f"OS:              {ctx['system']['os']}",
            f"Active window:   {ctx['apps']['active_window']}",
            f"Running apps:    {', '.join(ctx['apps']['running'][:10]) or 'none'}",
            "",
            "=== USER MEMORY ===",
            f"Frequent apps:   {', '.join(ctx['memory']['frequent_apps']) or 'none'}",
            f"Recent commands:\n{ctx['memory']['recent_commands']}",
            "",
            "=== USER PREFERENCES ===",
        ]

        prefs = ctx["user"]["preferences"]
        if prefs:
            for k, v in prefs.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append("  (none set yet)")

        lines.append("=== END CONTEXT ===")
        return "\n".join(lines)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _system_info(self) -> dict:
        return {
            "os":      f"{platform.system()} {platform.release()}",
            "machine": platform.machine(),
            "python":  platform.python_version(),
        }

    def _time_info(self) -> dict:
        now = datetime.datetime.now()
        return {
            "now":      now.strftime("%Y-%m-%d %H:%M:%S"),
            "date":     now.strftime("%A, %B %d %Y"),
            "time":     now.strftime("%I:%M %p"),
            "weekday":  now.strftime("%A"),
        }

    def _app_info(self) -> dict:
        # Active window
        active = "Unknown"
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            active = win.title if win else "Unknown"
        except Exception:
            pass

        # Running processes (top visible ones)
        running = []
        seen = set()
        try:
            for proc in psutil.process_iter(["name"]):
                n = proc.info["name"]
                if n and n not in seen and not n.lower().endswith((".exe", "svchost")):
                    seen.add(n)
                    running.append(n)
        except Exception:
            pass

        return {
            "active_window": active,
            "running":       sorted(running),
        }

    def _memory_info(self) -> dict:
        return {
            "frequent_apps":   self._memory.get_frequent_apps(top_n=5),
            "recent_commands": self._memory.get_command_history_summary(limit=8),
        }

    def _user_info(self) -> dict:
        return {
            "preferences": self._memory.get_all_preferences(),
        }
