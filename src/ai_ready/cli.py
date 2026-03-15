"""Interactive CLI entry point for the SEC EDGAIR financial chat.

Usage:
    python -m src.ai_ready.cli                       # Interactive chat
    python -m src.ai_ready.cli --single "question"   # Single question
    python -m src.ai_ready.cli --model claude-opus-4-20250514  # Model override
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

BANNER = """
SEC EDGAIR Financial Chat
  20 companies | 25 metrics | 7 ratios | FY2009-2026
  Type 'quit' to exit, 'clear' to reset conversation
"""


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="SEC EDGAIR Financial Chat")
    parser.add_argument(
        "--single",
        type=str,
        help="Ask a single question and exit (no conversation mode)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="claude-sonnet-4-5-20250514",
        help="Claude model to use (default: claude-sonnet-4-5-20250514)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging (shows tool calls)",
    )
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    # Import here to avoid loading DB on --help
    from src.ai_ready.chat.agent import chat

    # Initialize DB (loads Iceberg tables)
    print("Loading financial data from Iceberg tables...")
    try:
        from src.ai_ready.tools.db import get_db, get_table_row_counts
        get_db()
        counts = get_table_row_counts()
        total = sum(counts.values())
        print(f"  Loaded {total:,} rows across {len(counts)} tables")
    except Exception as e:
        print(f"Warning: Failed to load some tables: {e}")
        print("Some tools may return errors.")

    # Single question mode
    if args.single:
        response_text, _ = chat(args.single, [], model=args.model)
        print(response_text)
        return

    # Interactive mode
    print(BANNER)
    history: list[dict] = []

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if user_input.lower() == "clear":
            history = []
            print("Conversation cleared.")
            continue

        try:
            response_text, history = chat(user_input, history, model=args.model)
            print(f"\n{response_text}")
        except Exception as e:
            print(f"\nError: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()
