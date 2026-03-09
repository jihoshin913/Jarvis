"""
Jarvis Agent — CLI entry point.

Usage:
    python main.py                  # interactive loop
    python main.py --composio       # enable Composio integrations
    python main.py "open Discord"   # single command then exit
"""

from __future__ import annotations
import argparse
import sys

from agents.master_agent import MasterAgent


BANNER = """
╔══════════════════════════════════════╗
║           JARVIS  AGENT              ║
║   Natural Language → Computer Action ║
╚══════════════════════════════════════╝

Commands:
  /tools      — list available tools
  /preview    — preview next action without executing
  /context    — show current system context
  /history    — show recent command history
  /set k=v    — save a user preference
  /help       — show this message
  /quit       — exit

"""


def print_results(results: list[dict]):
    if not results:
        return
    failed = [r for r in results if r.get("status") == "error"]
    if failed:
        print(f"\n  {len(failed)} action(s) failed.")


def run_interactive(agent: MasterAgent):
    print(BANNER)
    preview_next = False

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        # ── Built-in commands ─────────────────────────────────────────────────
        if user_input == "/quit":
            print("Goodbye.")
            break

        elif user_input == "/help":
            print(BANNER)

        elif user_input == "/tools":
            tools = agent.get_tools()
            print(f"\n  Available tools ({len(tools)}):")
            for t in tools:
                print(f"    • {t}")
            print()

        elif user_input == "/context":
            print("\n" + agent.context.build_prompt_block() + "\n")

        elif user_input == "/history":
            cmds = agent.memory.get_recent_commands(10)
            if not cmds:
                print("  No history yet.\n")
            else:
                print("\n  Recent commands:")
                for cmd in reversed(cmds):
                    icon = "✓" if cmd["success"] else "✗"
                    print(f"    {icon} {cmd['user_input']}")
                print()

        elif user_input == "/preview":
            preview_next = True
            print("  Preview mode ON — next command will be explained, not executed.\n")

        elif user_input.startswith("/set "):
            parts = user_input[5:].split("=", 1)
            if len(parts) == 2:
                agent.set_preference(parts[0].strip(), parts[1].strip())
                print(f"  Preference saved: {parts[0].strip()} = {parts[1].strip()}\n")
            else:
                print("  Usage: /set key=value\n")

        # ── Natural language input ────────────────────────────────────────────
        else:
            if preview_next:
                preview_next = False
                explanation = agent.preview(user_input)
                print(f"\n  Preview: {explanation}\n")
            else:
                results = agent.run(user_input)
                print_results(results)


def main():
    parser = argparse.ArgumentParser(description="Jarvis Agent")
    parser.add_argument("command", nargs="?", help="Single command to execute then exit")
    parser.add_argument("--composio", action="store_true", help="Enable Composio integrations")
    args = parser.parse_args()

    agent = MasterAgent(enable_composio=args.composio)

    if args.command:
        # Single-shot mode
        results = agent.run(args.command)
        print_results(results)
        sys.exit(0 if all(r.get("status") != "error" for r in results) else 1)
    else:
        run_interactive(agent)


if __name__ == "__main__":
    main()
