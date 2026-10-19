from __future__ import annotations

import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.content import ContentSearcher
from ..core.drives import get_available_roots
from ..core.filters import SearchFilter, parse_date_filter, parse_size_to_bytes
from ..core.search import SearchEngine
from ..ui.explorer import open_path_in_file_manager


def tool_find_files(
    query: str = "",
    root: Optional[str] = None,
    extension: Optional[str] = None,
    file_type: Optional[str] = None,
    size: Optional[str] = None,
    modified: Optional[str] = None,
    limit: int = 25,
) -> Dict[str, Any]:
    """Search for files or folders by name, extension, size, or modification date."""
    if extension:
        file_type = file_type or "file"
    extensions = {extension} if extension else set()
    min_size, max_size = None, None
    if size:
        try:
            op, sz = parse_size_to_bytes(size)
            if op in (">", ">="):
                min_size = sz
            elif op in ("<", "<="):
                max_size = sz
            else:
                min_size = sz
        except ValueError as e:
            return {"error": str(e)}

    mod_after, mod_before = None, None
    if modified:
        try:
            op, ts = parse_date_filter(modified)
            if op in ("<", "<="):
                mod_after = ts
            else:
                mod_before = ts
        except ValueError as e:
            return {"error": str(e)}

    search_filter = SearchFilter(
        query=query,
        file_type=file_type,
        extensions=extensions,
        min_size=min_size,
        max_size=max_size,
        modified_after=mod_after,
        modified_before=mod_before,
    )

    roots = [Path(root)] if root else None
    engine = SearchEngine()
    results, errors, stats = engine.search(search_filter, roots=roots, max_results=limit)

    return {
        "count": len(results),
        "total_scanned": stats.total_scanned,
        "duration_seconds": round(stats.duration_seconds, 3),
        "results": [
            {
                "path": str(r.path),
                "name": r.path.name,
                "is_dir": r.is_dir,
                "size": r.readable_size,
                "modified": r.readable_mtime,
            }
            for r in results
        ],
    }


def tool_grep_content(
    pattern: str,
    path: str,
    extension: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Search inside files in a directory or single file for specific text or regex."""
    target_path = Path(path)
    if not target_path.exists():
        return {"error": f"Path does not exist: {path}"}

    searcher = ContentSearcher()
    if target_path.is_file():
        matches = searcher.search_file(target_path, pattern, max_matches_per_file=limit)
    else:
        exts = {f".{extension.lstrip('.')}".lower()} if extension else None
        files = []
        for curr, _, fnames in os.walk(target_path):
            for fn in fnames:
                if exts and Path(fn).suffix.lower() not in exts:
                    continue
                files.append(Path(curr) / fn)
                if len(files) >= 500:
                    break
            if len(files) >= 500:
                break
        matches = list(searcher.search_files(files, pattern, max_total_matches=limit))

    return {
        "pattern": pattern,
        "match_count": len(matches),
        "matches": [
            {
                "file": str(m.path),
                "line": m.line_number,
                "text": m.line_text.strip(),
            }
            for m in matches
        ],
    }


def tool_read_file(path: str, start_line: int = 1, max_lines: int = 50) -> Dict[str, Any]:
    """Read lines of text from a specified file."""
    target_path = Path(path)
    if not target_path.is_file():
        return {"error": f"Not a valid file: {path}"}

    try:
        lines: List[str] = []
        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, start=1):
                if idx < start_line:
                    continue
                if idx >= start_line + max_lines:
                    break
                lines.append(f"{idx}: {line.rstrip()}")

        return {
            "path": str(target_path),
            "start_line": start_line,
            "lines_read": len(lines),
            "content": "\n".join(lines),
        }
    except OSError as e:
        return {"error": f"Failed reading file: {e}"}


def tool_open_file(path: str) -> Dict[str, Any]:
    """Reveal a file or open a folder in the native file manager."""
    target_path = Path(path)
    if not target_path.exists():
        return {"success": False, "error": f"Path not found: {path}"}
    success = open_path_in_file_manager(target_path)
    return {"success": success, "path": str(target_path)}


def tool_get_system_info() -> Dict[str, Any]:
    """Get system summary, OS platform, and available drive roots."""
    roots = get_available_roots()
    return {
        "os": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "available_roots": [str(r) for r in roots],
        "cwd": os.getcwd(),
        "home": str(Path.home()),
    }


AGENT_TOOL_REGISTRY = {
    "find_files": tool_find_files,
    "grep_content": tool_grep_content,
    "read_file": tool_read_file,
    "open_file": tool_open_file,
    "get_system_info": tool_get_system_info,
}
