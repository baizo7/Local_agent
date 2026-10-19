from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable, List, Optional, Tuple


from .parsers import extract_document_text


@dataclass
class ContentMatch:
    path: Path
    line_number: int
    line_text: str
    match_span: Tuple[int, int]


def is_binary_file(path: Path, sample_size: int = 8192) -> bool:
    """Check if a file appears to be binary by looking for null bytes in initial sample."""
    ext = path.suffix.lower()
    if ext in {".pdf", ".docx", ".xlsx", ".pptx"}:
        return False
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
            return b"\x00" in chunk
    except OSError:
        return True


class ContentSearcher:
    """Fast text scanner for searching within file contents."""

    SUPPORTED_EXTENSIONS = {
        ".txt", ".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini",
        ".cfg", ".csv", ".tsv", ".js", ".jsx", ".ts", ".tsx", ".html",
        ".css", ".scss", ".xml", ".sql", ".sh", ".ps1", ".bat", ".cmd",
        ".c", ".cpp", ".h", ".hpp", ".rs", ".go", ".java", ".log",
        ".pdf", ".docx", ".xlsx", ".pptx",
    }

    def __init__(self, encodings: Optional[List[str]] = None) -> None:
        self.encodings = encodings or ["utf-8", "utf-8-sig", "latin-1", "cp1252"]

    def search_file(
        self,
        path: Path,
        pattern: str,
        is_regex: bool = False,
        max_matches_per_file: int = 10,
    ) -> List[ContentMatch]:
        if not path.is_file():
            return []

        ext = path.suffix.lower()
        compiled_re: Optional[re.Pattern] = None
        if is_regex:
            try:
                compiled_re = re.compile(pattern, re.IGNORECASE)
            except re.error:
                return []
        pattern_lower = pattern.lower()

        # Handle structured document formats (.pdf, .docx, .xlsx, .pptx)
        if ext in {".pdf", ".docx", ".xlsx", ".pptx"}:
            doc_text = extract_document_text(path)
            if not doc_text:
                return []
            matches: List[ContentMatch] = []
            for line_no, line in enumerate(doc_text.splitlines(), start=1):
                span: Optional[Tuple[int, int]] = None
                if compiled_re:
                    m = compiled_re.search(line)
                    if m:
                        span = m.span()
                else:
                    idx = line.lower().find(pattern_lower)
                    if idx != -1:
                        span = (idx, idx + len(pattern))

                if span:
                    matches.append(
                        ContentMatch(
                            path=path,
                            line_number=line_no,
                            line_text=line.rstrip("\r\n"),
                            match_span=span,
                        )
                    )
                    if len(matches) >= max_matches_per_file:
                        return matches
            return matches

        if is_binary_file(path):
            return []

        matches = []
        for encoding in self.encodings:
            try:
                with open(path, "r", encoding=encoding, errors="replace") as f:
                    for line_no, line in enumerate(f, start=1):
                        span: Optional[Tuple[int, int]] = None
                        if compiled_re:
                            m = compiled_re.search(line)
                            if m:
                                span = m.span()
                        else:
                            idx = line.lower().find(pattern_lower)
                            if idx != -1:
                                span = (idx, idx + len(pattern))

                        if span:
                            matches.append(
                                ContentMatch(
                                    path=path,
                                    line_number=line_no,
                                    line_text=line.rstrip("\r\n"),
                                    match_span=span,
                                )
                            )
                            if len(matches) >= max_matches_per_file:
                                return matches
                return matches
            except (UnicodeDecodeError, OSError):
                continue
        return matches

    def search_files(
        self,
        files: Iterable[Path],
        pattern: str,
        is_regex: bool = False,
        max_total_matches: int = 100,
    ) -> Generator[ContentMatch, None, None]:
        total = 0
        for file_path in files:
            file_matches = self.search_file(file_path, pattern, is_regex=is_regex)
            for m in file_matches:
                yield m
                total += 1
                if total >= max_total_matches:
                    return
