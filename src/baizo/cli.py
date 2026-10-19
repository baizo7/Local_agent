from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from . import __version__
from .agent.brain import BaizoAgent
from .core.content import ContentSearcher
from .core.drives import get_available_roots
from .core.filters import SearchFilter, parse_date_filter, parse_size_to_bytes
from .core.indexer import LocalIndexer
from .core.search import SearchEngine
from .ui.console import TerminalUI
from .ui.explorer import copy_to_clipboard, open_path_in_file_manager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="baizo",
        description="Baizo: Intelligent desktop search engine, indexer, and AI assistant.",
        epilog=(
            "Examples:\n"
            '  baizo find "main.py"\n'
            '  baizo find "*.pdf" --root "D:\\Documents" --modified "<7d"\n'
            '  baizo find "report" --size ">5MB" --open\n'
            '  baizo grep "def main" --path "D:\\projects" --ext py\n'
            '  baizo index add "D:\\projects"\n'
            '  baizo index search "transformer"\n'
            '  baizo ask "where are my recent spreadsheets?"\n'
            "  baizo chat\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"Baizo {__version__}")
    subparsers = parser.add_subparsers(dest="subcommand", title="Commands")

    # Command: find
    find_parser = subparsers.add_parser("find", help="Search for files and folders by name, pattern, or attributes")
    find_parser.add_argument("query", nargs="*", default=[""], help="Name or glob pattern to search for")
    find_parser.add_argument("--root", action="append", default=[], help="Target drive or folder (may be repeated)")
    find_parser.add_argument("--ext", help="Comma-separated extensions (e.g. py,pdf,docx)")
    find_parser.add_argument("--type", choices=["file", "dir"], help="Limit results to files or directories")
    find_parser.add_argument("--size", help="Filter by size (e.g. '>10MB', '<500KB')")
    find_parser.add_argument("--modified", help="Filter by modified date (e.g. '<7d', '<24h', '2026-01-01')")
    find_parser.add_argument("--regex", action="store_true", help="Treat query as a regular expression")
    find_parser.add_argument("--hidden", action="store_true", help="Include hidden files and folders")
    find_parser.add_argument("--max-results", type=int, default=100, help="Maximum results to return (default: 100)")
    find_parser.add_argument("--open", action="store_true", help="Reveal result in File Explorer")
    find_parser.add_argument("--copy", action="store_true", help="Copy matching path(s) to system clipboard")

    # Command: grep
    grep_parser = subparsers.add_parser("grep", help="Search inside files for text or regex patterns")
    grep_parser.add_argument("pattern", help="Text or regex to search for")
    grep_parser.add_argument("--path", default=".", help="Directory or file to search within (default: .)")
    grep_parser.add_argument("--ext", help="Filter by extension (e.g. py, json)")
    grep_parser.add_argument("--regex", action="store_true", help="Treat pattern as regular expression")
    grep_parser.add_argument("--max", type=int, default=50, help="Maximum matches to return")

    # Command: index
    index_parser = subparsers.add_parser("index", help="Manage and query the local SQLite FTS5 database")
    index_sub = index_parser.add_subparsers(dest="index_action")

    idx_add = index_sub.add_parser("add", help="Index a folder or drive")
    idx_add.add_argument("path", help="Folder path to index")
    idx_add.add_argument("--content", action="store_true", help="Index text contents of files for full-text search")

    idx_search = index_sub.add_parser("search", help="Fast full-text search against the index")
    idx_search.add_argument("query", help="Search query")
    idx_search.add_argument("--limit", type=int, default=50, help="Max results")

    index_sub.add_parser("stats", help="Show index statistics")
    index_sub.add_parser("clear", help="Clear the index database")

    # Command: ask
    ask_parser = subparsers.add_parser("ask", help="Ask the Baizo AI agent to find or inspect desktop items")
    ask_parser.add_argument("prompt", nargs="+", help="Natural language question or request")

    # Command: chat
    subparsers.add_parser("chat", help="Start an interactive conversation with the Baizo AI agent")

    # Command: stats
    subparsers.add_parser("stats", help="Display accessible system drives and system status")

    # Command: watch
    watch_parser = subparsers.add_parser("watch", help="Watch a directory and automatically synchronize changes into the index")
    watch_parser.add_argument("path", help="Folder path to monitor")
    watch_parser.add_argument("--content", action="store_true", help="Index document content on changes")

    # Command: semantic
    semantic_parser = subparsers.add_parser("semantic", help="Search indexed documents by meaning using vector similarity")
    semantic_parser.add_argument("query", help="Semantic query phrase")
    semantic_parser.add_argument("--limit", type=int, default=10, help="Max results to return")

    return parser


def handle_find(args: argparse.Namespace, ui: TerminalUI) -> None:
    query = " ".join(args.query).strip() if args.query else ""
    roots = [Path(r).expanduser() for r in args.root] if args.root else get_available_roots()
    roots = [p.resolve() for p in roots if p.exists()]

    if not roots:
        print("Error: No searchable roots found. Specify one with --root PATH.", file=sys.stderr)
        sys.exit(2)

    extensions = set()
    if args.ext:
        extensions = {e.strip() for e in args.ext.split(",") if e.strip()}

    min_size, max_size = None, None
    if args.size:
        try:
            op, sz = parse_size_to_bytes(args.size)
            if op in (">", ">="):
                min_size = sz
            elif op in ("<", "<="):
                max_size = sz
            else:
                min_size = sz
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(2)

    mod_after, mod_before = None, None
    if args.modified:
        try:
            op, ts = parse_date_filter(args.modified)
            if op in ("<", "<="):
                mod_after = ts
            else:
                mod_before = ts
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(2)

    try:
        search_filter = SearchFilter(
            query=query,
            is_regex=args.regex,
            file_type=args.type,
            extensions=extensions,
            min_size=min_size,
            max_size=max_size,
            modified_after=mod_after,
            modified_before=mod_before,
            include_hidden=args.hidden,
        )
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    ui.print_search_header(query or "*", roots)
    engine = SearchEngine()
    results, errors, stats = engine.search(search_filter, roots=roots, max_results=args.max_results)

    ui.print_results(results, highlight_query=query if not args.regex else None)
    ui.print_summary(stats, errors)

    if args.copy and results:
        copied_text = "\n".join(str(r.path) for r in results)
        if copy_to_clipboard(copied_text):
            print(f"📋 Copied {len(results)} path(s) to clipboard.")
        else:
            print("Notice: Clipboard could not be accessed.")

    if args.open and results:
        target = ui.prompt_for_selection(results)
        if target:
            open_path_in_file_manager(target.path)
            print(f"📂 Opened: {target.path}")


def handle_grep(args: argparse.Namespace, ui: TerminalUI) -> None:
    target_path = Path(args.path).resolve()
    if not target_path.exists():
        print(f"Error: Path not found: {target_path}", file=sys.stderr)
        sys.exit(1)

    print(f'🔍 Grepping for "{args.pattern}" in {target_path}...')
    searcher = ContentSearcher()

    if target_path.is_file():
        matches = searcher.search_file(target_path, args.pattern, is_regex=args.regex, max_matches_per_file=args.max)
    else:
        exts = {f".{args.ext.lstrip('.')}".lower()} if args.ext else None
        files = []
        for curr, _, fnames in Path.walk(target_path) if hasattr(Path, "walk") else os.walk(target_path):
            for fn in fnames:
                if exts and Path(fn).suffix.lower() not in exts:
                    continue
                files.append(Path(curr) / fn)
        matches = list(searcher.search_files(files, args.pattern, is_regex=args.regex, max_total_matches=args.max))

    if matches:
        print(f"\nFound {len(matches)} match(es):\n")
        for m in matches:
            print(f"  {m.path}:{m.line_number} -> {m.line_text.strip()}")
    else:
        print(f"No occurrences of \"{args.pattern}\" found.")


def handle_index(args: argparse.Namespace) -> None:
    indexer = LocalIndexer()
    action = args.index_action

    if action == "add":
        target = Path(args.path).resolve()
        print(f"📁 Indexing '{target}' (content={args.content})...")
        stats = indexer.index_directory(target, index_content=args.content)
        print(f"Index complete: added {stats['added']:,}, updated {stats['updated']:,}, skipped {stats['skipped']:,}.")
    elif action == "search":
        results = indexer.search(args.query, limit=args.limit)
        if results:
            print(f"Found {len(results)} indexed match(es):\n")
            for idx, r in enumerate(results, start=1):
                kind = "DIR " if r.is_dir else "FILE"
                snippet_line = f"\n     Excerpt: \"{r.snippet}\"" if r.snippet else ""
                print(f"{idx:>3}. [{kind}] {r.readable_size:>8}  {r.path}{snippet_line}")
        else:
            print("No indexed results found.")
    elif action == "stats":
        stats = indexer.get_stats()
        print(f"📊 Local Index Stats: {stats['files']:,} files, {stats['directories']:,} folders indexed.")
    elif action == "clear":
        indexer.clear()
        print("🗑️ Local index cleared.")
    else:
        print("Specify an index action: add, search, stats, clear. See --help.")


def handle_stats() -> None:
    roots = get_available_roots()
    print("\n🖥️  System & Drive Status:")
    for r in roots:
        try:
            stat = os.statvfs(r) if hasattr(os, "statvfs") else None
            print(f"  • Drive: {r}")
        except Exception:
            print(f"  • Drive: {r}")
    indexer = LocalIndexer()
    idx_stats = indexer.get_stats()
    print(f"  • Local Index: {idx_stats['files']} files, {idx_stats['directories']} folders\n")


def handle_watch(args: argparse.Namespace) -> None:
    from .core.watcher import start_watcher
    target = Path(args.path).resolve()
    start_watcher(target, index_content=args.content, blocking=True)


def handle_semantic(args: argparse.Namespace) -> None:
    from .core.semantic import LocalSemanticEngine
    print(f'🧠 Searching semantic relevance for: "{args.query}"...\n')
    engine = LocalSemanticEngine()
    results = engine.search_semantic(args.query, limit=args.limit)
    if not results:
        print("No semantically relevant indexed documents found.")
        print("Tip: Run 'baizo index add <path> --content' first to index your documents.")
        return

    for idx, (res, score) in enumerate(results, start=1):
        print(f"{idx:>2}. [Score: {score:.2f}] {res.path.name}")
        print(f"    Path: {res.path}\n")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    ui = TerminalUI()

    if args.subcommand == "find":
        handle_find(args, ui)
    elif args.subcommand == "grep":
        handle_grep(args, ui)
    elif args.subcommand == "index":
        handle_index(args)
    elif args.subcommand == "watch":
        handle_watch(args)
    elif args.subcommand == "semantic":
        handle_semantic(args)
    elif args.subcommand == "ask":
        prompt = " ".join(args.prompt)
        agent = BaizoAgent()
        response = agent.ask(prompt)
        print(f"\n{response}\n")
    elif args.subcommand == "chat":
        agent = BaizoAgent()
        agent.interactive_chat()
    elif args.subcommand == "stats":
        handle_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
