from __future__ import annotations

import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .parsers import extract_document_text
from .filters import DEFAULT_IGNORED_DIRS
from .search import SearchResult


def get_default_db_path() -> Path:
    home = Path.home()
    baizo_dir = home / ".baizo"
    baizo_dir.mkdir(parents=True, exist_ok=True)
    return baizo_dir / "index.db"


class LocalIndexer:
    """Fast local SQLite FTS5 index for instant sub-millisecond desktop queries."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or get_default_db_path()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE,
                    filename TEXT,
                    is_dir INTEGER,
                    size INTEGER,
                    mtime REAL,
                    indexed_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS fts_files USING fts5(
                    filename,
                    path,
                    content,
                    tokenize='porter unicode61'
                )
                """
            )
            conn.commit()

    def index_file(
        self,
        file_path: Path,
        index_content: bool = True,
        max_file_size: int = 15_000_000,
    ) -> bool:
        """Add or update a single file in the index."""
        try:
            norm_path = os.path.normcase(str(file_path.resolve()))
            name = file_path.name
            is_dir = file_path.is_dir()
            stat = file_path.stat()
            size = stat.st_size if not is_dir else 0
            mtime = stat.st_mtime
        except OSError:
            return False

        content_text = ""
        if index_content and not is_dir and size <= max_file_size:
            content_text = extract_document_text(file_path, max_size_bytes=max_file_size)

        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM files WHERE path = ?", (norm_path,))
            existing = cursor.fetchone()
            if existing:
                cursor.execute(
                    """
                    UPDATE files SET filename = ?, is_dir = ?, size = ?, mtime = ?, indexed_at = ? WHERE path = ?
                    """,
                    (name, 1 if is_dir else 0, size, mtime, now, norm_path),
                )
                cursor.execute("DELETE FROM fts_files WHERE path = ?", (norm_path,))
            else:
                cursor.execute(
                    """
                    INSERT INTO files (path, filename, is_dir, size, mtime, indexed_at) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (norm_path, name, 1 if is_dir else 0, size, mtime, now),
                )
            cursor.execute(
                """
                INSERT INTO fts_files (filename, path, content) VALUES (?, ?, ?)
                """,
                (name, norm_path, content_text),
            )
            conn.commit()
        return True

    def delete_file_from_index(self, file_path: Path) -> bool:
        """Remove a deleted file from the index."""
        try:
            norm_path = os.path.normcase(str(file_path.resolve()))
        except Exception:
            norm_path = os.path.normcase(str(file_path))
        with self._get_connection() as conn:
            conn.execute("DELETE FROM files WHERE path = ?", (norm_path,))
            conn.execute("DELETE FROM fts_files WHERE path = ?", (norm_path,))
            conn.commit()
        return True

    def index_directory(
        self,
        root: Path,
        index_content: bool = False,
        max_file_size: int = 15_000_000,
        verbose: bool = False,
    ) -> Dict[str, int]:
        root = root.resolve()
        if not root.exists():
            raise FileNotFoundError(f"Directory not found: {root}")

        added = 0
        updated = 0
        skipped = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            for current, dirs, files in os.walk(root, topdown=True):
                dirs[:] = [
                    d for d in dirs
                    if d.casefold() not in DEFAULT_IGNORED_DIRS and not d.startswith(".")
                ]

                current_path = Path(current)
                all_entries = [(d, True) for d in dirs] + [(f, False) for f in files]

                for name, is_dir in all_entries:
                    if name.startswith("."):
                        continue

                    file_path = current_path / name
                    norm_path = os.path.normcase(str(file_path))

                    try:
                        stat = file_path.stat()
                        size = stat.st_size if not is_dir else 0
                        mtime = stat.st_mtime
                    except OSError:
                        continue

                    cursor.execute("SELECT mtime, size FROM files WHERE path = ?", (norm_path,))
                    existing = cursor.fetchone()

                    if existing and existing["mtime"] == mtime and existing["size"] == size:
                        skipped += 1
                        continue

                    content_text = ""
                    if index_content and not is_dir and size <= max_file_size:
                        content_text = extract_document_text(file_path, max_size_bytes=max_file_size)

                    now = time.time()
                    if existing:
                        cursor.execute(
                            """
                            UPDATE files
                            SET filename = ?, is_dir = ?, size = ?, mtime = ?, indexed_at = ?
                            WHERE path = ?
                            """,
                            (name, 1 if is_dir else 0, size, mtime, now, norm_path),
                        )
                        cursor.execute("DELETE FROM fts_files WHERE path = ?", (norm_path,))
                        cursor.execute(
                            """
                            INSERT INTO fts_files (filename, path, content) VALUES (?, ?, ?)
                            """,
                            (name, norm_path, content_text),
                        )
                        updated += 1
                    else:
                        cursor.execute(
                            """
                            INSERT INTO files (path, filename, is_dir, size, mtime, indexed_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (norm_path, name, 1 if is_dir else 0, size, mtime, now),
                        )
                        cursor.execute(
                            """
                            INSERT INTO fts_files (filename, path, content) VALUES (?, ?, ?)
                            """,
                            (name, norm_path, content_text),
                        )
                        added += 1

                if (added + updated) % 1000 == 0:
                    conn.commit()

            conn.commit()

        return {"added": added, "updated": updated, "skipped": skipped}

    def search(self, query: str, limit: int = 50) -> List[SearchResult]:
        """Search the FTS index using SQLite full-text search match syntax."""
        query = query.strip().strip('"').strip("'")
        if not query:
            return []

        words = re.findall(r"\w+", query)
        if not words:
            return []
        fts_query = " ".join(f"{w}*" for w in words)

        results: List[SearchResult] = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT f.path, f.filename, f.is_dir, f.size, f.mtime,
                           snippet(fts_files, 2, '...', '...', '...', 12) AS fts_snippet
                    FROM fts_files fts
                    JOIN files f ON f.path = fts.path
                    WHERE fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (fts_query, limit),
                )
                rows = cursor.fetchall()
            except sqlite3.OperationalError:
                cursor.execute(
                    """
                    SELECT f.path, f.filename, f.is_dir, f.size, f.mtime,
                           '' AS fts_snippet
                    FROM files f
                    LEFT JOIN fts_files fts ON f.path = fts.path
                    WHERE f.filename LIKE ? OR f.path LIKE ? OR fts.content LIKE ?
                    LIMIT ?
                    """,
                    (f"%{query}%", f"%{query}%", f"%{query}%", limit),
                )
                rows = cursor.fetchall()

            for r in rows:
                snippet_text = r["fts_snippet"] if "fts_snippet" in r.keys() and r["fts_snippet"] else None
                results.append(
                    SearchResult(
                        path=Path(r["path"]),
                        is_dir=bool(r["is_dir"]),
                        size=r["size"],
                        mtime=r["mtime"],
                        snippet=snippet_text,
                    )
                )
        return results

    def get_stats(self) -> Dict[str, int]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) AS total_files FROM files WHERE is_dir = 0")
            files_count = cursor.fetchone()["total_files"]
            cursor.execute("SELECT COUNT(*) AS total_dirs FROM files WHERE is_dir = 1")
            dirs_count = cursor.fetchone()["total_dirs"]
            return {"files": files_count, "directories": dirs_count}

    def clear(self) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM files")
            conn.execute("DELETE FROM fts_files")
            conn.commit()
