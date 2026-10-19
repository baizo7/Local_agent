from __future__ import annotations

import fnmatch
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Set


DEFAULT_IGNORED_DIRS = {
    "$recycle.bin",
    "system volume information",
    "windows.old",
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
}


def parse_size_to_bytes(size_str: str) -> tuple[str, int]:
    """Parse a size filter string like '>10MB', '<500KB', '+1GB', '100M'.
    Returns (operator, bytes) where operator is '>' or '<' or '='.
    """
    s = size_str.strip()
    op = "="
    if s.startswith((">=", "<=")):
        op = s[:2]
        s = s[2:].strip()
    elif s.startswith((">", "+")):
        op = ">"
        s = s[1:].strip()
    elif s.startswith(("<", "-")):
        op = "<"
        s = s[1:].strip()

    units = {
        "b": 1,
        "k": 1024,
        "kb": 1024,
        "m": 1024**2,
        "mb": 1024**2,
        "g": 1024**3,
        "gb": 1024**3,
        "t": 1024**4,
        "tb": 1024**4,
    }

    match = re.match(r"^([\d.]+)\s*([a-zA-Z]*)$", s)
    if not match:
        raise ValueError(f"Invalid size specification: '{size_str}'. Example: '10MB', '>500KB'")

    number, unit = match.groups()
    val = float(number)
    unit_lower = unit.lower() or "b"
    multiplier = units.get(unit_lower, 1)
    return op, int(val * multiplier)


def parse_date_filter(date_str: str) -> tuple[str, float]:
    """Parse relative (e.g. '<7d', '>24h', '30m') or absolute date ('2026-01-01').
    Returns (operator, timestamp) where operator is '<' (newer than) or '>' (older than).
    """
    s = date_str.strip()
    op = "<"  # default to 'newer than' (within the last X)
    if s.startswith((">=", "<=")):
        op = s[:2]
        s = s[2:].strip()
    elif s.startswith(("<", "+")):
        op = "<"
        s = s[1:].strip()
    elif s.startswith((">", "-")):
        op = ">"
        s = s[1:].strip()

    now = time.time()
    rel_match = re.match(r"^(\d+)\s*([smhdwMy])$", s)
    if rel_match:
        qty, unit = rel_match.groups()
        q = int(qty)
        deltas = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
            "w": 604800,
            "M": 2592000,
            "y": 31536000,
        }
        seconds = q * deltas.get(unit, 86400)
        return op, now - seconds

    # Try ISO date parsing
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return op, dt.timestamp()
        except ValueError:
            pass

    raise ValueError(f"Invalid date/time format: '{date_str}'. Use e.g. '<7d', '24h', or '2026-01-01'.")


@dataclass
class SearchFilter:
    query: str = ""
    is_regex: bool = False
    file_type: Optional[str] = None  # 'file', 'dir', or None
    extensions: Set[str] = field(default_factory=set)
    min_size: Optional[int] = None
    max_size: Optional[int] = None
    modified_after: Optional[float] = None
    modified_before: Optional[float] = None
    include_hidden: bool = False
    ignored_dirs: Set[str] = field(default_factory=lambda: set(DEFAULT_IGNORED_DIRS))

    def __post_init__(self) -> None:
        self.query = self.query.strip().strip('"').strip("'")
        self._compiled_regex: Optional[re.Pattern] = None
        self._is_glob = False

        if self.is_regex and self.query:
            try:
                self._compiled_regex = re.compile(self.query, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Invalid regular expression '{self.query}': {e}")
        elif any(c in self.query for c in "*?[]"):
            self._is_glob = True
            self._query_casefold = self.query.casefold()
        else:
            self._query_casefold = self.query.casefold()

        # Normalize extensions to lowercase with leading dot
        if self.extensions:
            self.extensions = {
                ext.lower() if ext.startswith(".") else f".{ext.lower()}"
                for ext in self.extensions
            }

    def should_ignore_dir(self, name: str) -> bool:
        if not self.include_hidden and name.startswith(".") and name not in {".", ".."}:
            return True
        return name.casefold() in self.ignored_dirs

    def matches_name(self, name: str) -> bool:
        if not self.query:
            return True
        if self._compiled_regex is not None:
            return bool(self._compiled_regex.search(name))
        if self._is_glob:
            return fnmatch.fnmatch(name.casefold(), self._query_casefold)
        return self._query_casefold in name.casefold()

    def matches(self, name: str, is_dir: bool, stat_info: Optional[os.stat_result] = None) -> bool:
        if not self.include_hidden and name.startswith(".") and name not in {".", ".."}:
            return False

        if self.file_type == "file" and is_dir:
            return False
        if self.file_type == "dir" and not is_dir:
            return False

        if self.extensions and not is_dir:
            ext = Path(name).suffix.lower()
            if ext not in self.extensions:
                return False

        if not self.matches_name(name):
            return False

        if stat_info is not None:
            if not is_dir:
                if self.min_size is not None and stat_info.st_size < self.min_size:
                    return False
                if self.max_size is not None and stat_info.st_size > self.max_size:
                    return False
            if self.modified_after is not None and stat_info.st_mtime < self.modified_after:
                return False
            if self.modified_before is not None and stat_info.st_mtime > self.modified_before:
                return False

        return True
