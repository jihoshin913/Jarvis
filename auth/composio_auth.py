"""
Composio auth helper — run this script directly to connect apps.

Usage:
    python auth/composio_auth.py                  # show connected apps
    python auth/composio_auth.py connect gmail
    python auth/composio_auth.py connect slack
    python auth/composio_auth.py connect discord
    python auth/composio_auth.py connect googlecalendar
    python auth/composio_auth.py connect notion
    python auth/composio_auth.py connect spotify
    python auth/composio_auth.py connect github

Composio stores OAuth tokens on their servers — you only connect once.
"""

import sys
import os

# Allow running this file directly from any directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.composio_tools import connect_app, list_connected_apps


def main():
    args = sys.argv[1:]

    if not args or args[0] == "list":
        apps = list_connected_apps()
        if apps:
            print(f"\nConnected apps ({len(apps)}):")
            for app in apps:
                print(f"  ✓ {app}")
        else:
            print("\nNo apps connected yet.")
        print("\nTo connect an app:  python auth/composio_auth.py connect gmail")

    elif args[0] == "connect" and len(args) > 1:
        app_name = args[1]
        print(f"\nConnecting {app_name}...")
        connect_app(app_name)

    else:
        print(__doc__)


if __name__ == "__main__":
    main()
