from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from ..core.search import SearchResult, SearchStats

try:
    from rich.console import Console
    from rich.table import Table
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


class TerminalUI:
    def __init__(self) -> None:
        self.console = Console() if HAS_RICH else None

    def print_banner(self) -> None:
        title = "⚡ Baizo: Desktop Intelligence & Search Engine"
        if HAS_RICH and self.console:
            self.console.print(f"[bold cyan]{title}[/bold cyan]")
        else:
            print(f"\n=== {title} ===\n")

    def print_search_header(self, query: str, roots: List[Path]) -> None:
        roots_str = ", ".join(str(r) for r in roots)
        if HAS_RICH and self.console:
            self.console.print(f"🔎 [bold]Searching for:[/bold] [yellow]\"{query}\"[/yellow] in [cyan]{roots_str}[/cyan]")
        else:
            print(f'🔎 Searching for "{query}" in {roots_str}...')

    def print_results(
        self,
        results: List[SearchResult],
        highlight_query: Optional[str] = None,
        max_display: int = 100,
    ) -> None:
        if not results:
            if HAS_RICH and self.console:
                self.console.print("[yellow]No matching files or folders found.[/yellow]")
                self.console.print("[dim]Tip: try a broader term, check --hidden, or search a specific --root.[/dim]")
            else:
                print("No matching files or folders found.")
                print("Tip: try a broader term or check --hidden.")
            return

        if HAS_RICH and self.console:
            table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 1))
            table.add_column("#", style="dim", justify="right", width=4)
            table.add_column("Type", width=7)
            table.add_column("Name", style="bold")
            table.add_column("Size", justify="right", style="cyan")
            table.add_column("Modified", style="dim")
            table.add_column("Path", style="dim")

            for idx, res in enumerate(results[:max_display], start=1):
                type_str = "[blue]DIR [/blue]" if res.is_dir else "[green]FILE[/green]"
                name = res.path.name or str(res.path)

                # Highlight query in name
                text_name = Text(name)
                if highlight_query and highlight_query.lower() in name.lower():
                    start = name.lower().find(highlight_query.lower())
                    text_name.stylize("bold yellow on default", start, start + len(highlight_query))

                table.add_row(
                    str(idx),
                    type_str,
                    text_name,
                    res.readable_size,
                    res.readable_mtime,
                    str(res.path.parent),
                )

            self.console.print(table)
            if len(results) > max_display:
                self.console.print(f"[dim]... and {len(results) - max_display} more results truncated.[/dim]")
        else:
            print(f"\nFound {len(results)} matches:\n")
            for idx, res in enumerate(results[:max_display], start=1):
                kind = "DIR " if res.is_dir else "FILE"
                print(f"{idx:>3}. [{kind}] {res.readable_size:>8}  {res.readable_mtime}  {res.path}")

    def print_summary(self, stats: SearchStats, errors: List[str]) -> None:
        summary = f"✨ Matched {stats.matched_count} item(s) in {stats.duration_seconds:.2f}s"
        if stats.total_scanned > 0:
            summary += f" (scanned {stats.total_scanned:,} entries)"

        if HAS_RICH and self.console:
            self.console.print(f"\n[bold green]{summary}[/bold green]")
            if errors:
                self.console.print(f"[dim yellow]Notice: {len(errors)} directory(s) skipped due to permissions or OS locks.[/dim yellow]")
        else:
            print(f"\n{summary}")
            if errors:
                print(f"Notice: {len(errors)} location(s) skipped due to permissions.")

    def prompt_for_selection(self, results: List[SearchResult]) -> Optional[SearchResult]:
        """Prompt user to choose one result from the list to open or inspect."""
        if not results:
            return None
        if len(results) == 1:
            return results[0]

        prompt_msg = f"\nMultiple matches found. Enter number [1-{len(results)}] to open (or 'q' to cancel): "
        while True:
            try:
                choice = input(prompt_msg).strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return None

            if choice.lower() in {"q", "quit", "exit", ""}:
                return None
            if choice.isdigit():
                val = int(choice)
                if 1 <= val <= len(results):
                    return results[val - 1]
            print(f"Invalid selection. Please enter a number between 1 and {len(results)}.")
