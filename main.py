"""eSaiph — Software Testing & Monitoring Tool.

Usage:
    python main.py          → Launch the GUI
    python main.py cli      → Launch the CLI
    python main.py --help   → Show help

Or install with: pip install -e .
Then use: esaiph --help
"""

import sys


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "cli":
        # Remove 'cli' from argv so Click doesn't see it as a command
        sys.argv.pop(1)
        from esaiph.cli import main as cli_main
        cli_main()
    elif len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
    else:
        from esaiph.gui.app import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()