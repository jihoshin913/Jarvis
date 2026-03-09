"""
Planner — sends user input + context to Claude and returns a structured
action plan as a list of {tool, args} dicts.
"""

from __future__ import annotations
import json
from typing import Any

import anthropic

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, MAX_ACTIONS_PER_PLAN

SYSTEM_PROMPT_TEMPLATE = """\
You are Jarvis, a personal AI agent that controls a Windows computer on behalf of the user.

Your job is to convert natural language commands into a precise sequence of tool calls.

Rules:
- Only use tools that are listed in the available tools.
- Generate the minimum number of steps needed to complete the task.
- Do not add unnecessary actions.
- If a task is ambiguous, make the most reasonable interpretation.
- If a task cannot be completed with available tools, say so clearly instead of guessing.
- Never invent tool names — only use exactly the tools provided.
- Maximum {max_actions} actions per plan.

{context_block}
"""


class Planner:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def generate_plan(
        self,
        user_input: str,
        tool_schemas: list[dict],
        context_block: str = "",
    ) -> list[dict[str, Any]]:
        """
        Call Claude with tool_use and extract the planned tool calls.

        Returns a list of actions:
            [{"tool": "open_app", "args": {"name": "Discord"}}, ...]
        """
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            max_actions=MAX_ACTIONS_PER_PLAN,
            context_block=context_block,
        )

        messages = [{"role": "user", "content": user_input}]

        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            tools=tool_schemas,
            messages=messages,
        )

        return self._extract_plan(response)

    def _extract_plan(self, response) -> list[dict[str, Any]]:
        """Parse Claude's response into a flat action list."""
        actions = []

        for block in response.content:
            if block.type == "tool_use":
                actions.append({
                    "tool": block.name,
                    "args": block.input,
                })
            elif block.type == "text" and block.text.strip():
                # Claude returned a text explanation instead of tool calls
                # Treat it as a no-op plan with a message
                actions.append({
                    "tool": "_message",
                    "args": {"text": block.text.strip()},
                })

        return actions

    def explain(
        self,
        user_input: str,
        context_block: str = "",
    ) -> str:
        """
        Ask Claude to explain what it would do, without generating tool calls.
        Useful for previewing a plan before execution.
        """
        system = (
            "You are Jarvis, a personal AI agent. "
            "Explain in plain English what steps you would take to complete this task. "
            "Be concise and specific.\n\n" + context_block
        )
        response = self._client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user_input}],
        )
        return response.content[0].text if response.content else ""
