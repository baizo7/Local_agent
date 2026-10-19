from __future__ import annotations

import concurrent.futures
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set, Tuple

from .drives import get_available_roots
from .filters import SearchFilter


@dataclass
class SearchResult:
    path: Path
    is_dir: bool
    size: int = 0
    mtime: float = 0.0
    snippet: Optional[str] = None

    @property
    def readable_size(self) -> str:
        if self.is_dir:
            return "<DIR>"
        bytes_val = float(self.size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}" if unit != "B" else f"{int(bytes_val)} B"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"

    @property
    def readable_mtime(self) -> str:
        if not self.mtime:
            return "-"
        dt = datetime.fromtimestamp(self.mtime)
        return dt.strftime("%Y-%m-%d %H:%M")


@dataclass
class SearchStats:
    total_scanned: int = 0
    duration_seconds: float = 0.0
    matched_count: int = 0


class SearchEngine:
    def __init__(self, max_workers: int = 8) -> None:
        self.max_workers = max_workers

    def search(
        self,
        filter_criteria: SearchFilter,
        roots: Optional[Iterable[Path]] = None,
        max_results: int = 100,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Tuple[List[SearchResult], List[str], SearchStats]:
        start_time = time.time()
        active_roots = list(roots or get_available_roots())
        valid_roots = [r.resolve() for r in active_roots if r.exists()]

        if not valid_roots:
            return [], ["No valid or accessible search roots found."], SearchStats()

        results: List[SearchResult] = []
        errors: List[str] = []
        seen: Set[str] = set()
        lock = threading.Lock()
        stop_event = threading.Event()
        total_scanned = 0

        def check_entry(candidate_path: Path, name: str, is_dir: bool) -> None:
            nonlocal total_scanned
            if stop_event.is_set():
                return

            stat_info: Optional[os.stat_result] = None
            needs_stat = (
                filter_criteria.min_size is not None
                or filter_criteria.max_size is not None
                or filter_criteria.modified_after is not None
                or filter_criteria.modified_before is not None
            )

            if needs_stat:
                try:
                    stat_info = candidate_path.stat()
                except OSError:
                    return

            if not filter_criteria.matches(name, is_dir, stat_info):
                return

            if stat_info is None:
                try:
                    stat_info = candidate_path.stat()
                except OSError:
                    stat_info = None

            size = stat_info.st_size if stat_info and not is_dir else 0
            mtime = stat_info.st_mtime if stat_info else 0.0

            try:
                key = os.path.normcase(str(candidate_path.resolve(strict=False)))
            except OSError:
                key = os.path.normcase(str(candidate_path))

            with lock:
                if key not in seen:
                    seen.add(key)
                    results.append(SearchResult(candidate_path, is_dir, size, mtime))
                    if len(results) >= max_results:
                        stop_event.set()

        def scan_worker(root: Path) -> None:
            nonlocal total_scanned
            local_scanned = 0

            def on_error(exc: OSError) -> None:
                with lock:
                    filename = getattr(exc, "filename", root)
                    errors.append(f"{filename}: {exc.strerror or exc}")

            for current, dirs, files in os.walk(
                root, topdown=True, onerror=on_error, followlinks=False
            ):
                if stop_event.is_set():
                    break

                dirs[:] = [d for d in dirs if not filter_criteria.should_ignore_dir(d)]

                current_path = Path(current)
                entries = [(d, True) for d in dirs] + [(f, False) for f in files]
                local_scanned += len(entries)

                for name, is_dir in entries:
                    if stop_event.is_set():
                        break
                    check_entry(current_path / name, name, is_dir)

            with lock:
                nonlocal total_scanned
                total_scanned += local_scanned
                if progress_callback:
                    progress_callback(total_scanned)

        # Fine-grained parallel dispatch: split drive roots into subtrees
        subroots: List[Path] = []
        for r in valid_roots:
            try:
                with os.scandir(r) as it:
                    has_subdirs = False
                    for entry in it:
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                if not filter_criteria.should_ignore_dir(entry.name):
                                    subroots.append(Path(entry.path))
                                    has_subdirs = True
                            elif entry.is_file(follow_symlinks=False):
                                check_entry(Path(entry.path), entry.name, False)
                        except OSError:
                            pass
                    if not has_subdirs:
                        subroots.append(r)
            except OSError:
                subroots.append(r)

        if not subroots:
            subroots = valid_roots

        workers = min(max(len(subroots), 1), self.max_workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(scan_worker, sr) for sr in subroots]
            concurrent.futures.wait(futures)

        duration = time.time() - start_time
        stats = SearchStats(
            total_scanned=total_scanned,
            duration_seconds=duration,
            matched_count=len(results),
        )
        return results, errors, stats
