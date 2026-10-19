from __future__ import annotations

import sys
from typing import List, Optional

from .llm import LLMClient
from ..ui.console import TerminalUI

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class BaizoAgent:
    """The central conversational brain of Baizo."""

    def __init__(self, llm_client: Optional[LLMClient] = None) -> None:
        self.client = llm_client or LLMClient()
        self.ui = TerminalUI()
        self.history: List[dict] = []
        self.console = Console() if HAS_RICH else None

    def ask(self, query: str) -> str:
        """Process a one-shot user question or instruction."""
        return self.client.query_with_tools(query, self.history)

    def interactive_chat(self) -> None:
        """Launch an interactive terminal chat session with Baizo."""
        self.ui.print_banner()

        welcome_text = (
            "🤖 Hello! I am **Baizo**, your desktop intelligence assistant.\n\n"
            "Here are some things you can ask me:\n"
            "• *\"Find all python files modified this week\"*\n"
            "• *\"Where is invoice.pdf in downloads and open it\"*\n"
            "• *\"Search for 'TODO' in D:\\projects\"*\n"
            "• *\"Read pyproject.toml\"*\n"
            "• *\"Show system info and drives\"*\n\n"
            "Type **exit** or **quit** to leave."
        )

        if HAS_RICH and self.console:
            self.console.print(Panel(Markdown(welcome_text), title="Baizo AI Agent", border_style="cyan"))
        else:
            print("\n" + welcome_text + "\n")

        while True:
            try:
                user_input = input("\nBaizo > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye!")
                break

            if not user_input:
                continue

            if user_input.lower() in {"exit", "quit", "q", ":q"}:
                print("Goodbye!")
                break

            try:
                response = self.client.query_with_tools(user_input, self.history)
                # Keep short history for conversational context
                self.history.append({"role": "user", "content": user_input})
                self.history.append({"role": "assistant", "content": response})
                if len(self.history) > 10:
                    self.history = self.history[-10:]

                if HAS_RICH and self.console:
                    self.console.print(f"\n[bold green]Baizo:[/bold green]\n{response}")
                else:
                    print(f"\nBaizo:\n{response}")

            except Exception as e:
                print(f"\nError: {e}", file=sys.stderr)
