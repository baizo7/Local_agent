from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from .filters import DEFAULT_IGNORED_DIRS
from .indexer import LocalIndexer

try:
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False


class IndexSyncHandler(FileSystemEventHandler if HAS_WATCHDOG else object):  # type: ignore[misc]
    """Listens for filesystem changes and synchronizes them to the SQLite FTS5 database."""

    def __init__(self, indexer: LocalIndexer, index_content: bool = True) -> None:
        if HAS_WATCHDOG:
            super().__init__()
        self.indexer = indexer
        self.index_content = index_content

    def _should_ignore(self, path_str: str) -> bool:
        p = Path(path_str)
        for part in p.parts:
            if part.casefold() in DEFAULT_IGNORED_DIRS or part.startswith("."):
                return True
        return False

    def on_created(self, event: FileSystemEvent) -> None:
        if self._should_ignore(event.src_path):
            return
        p = Path(event.src_path)
        if p.exists():
            self.indexer.index_file(p, index_content=self.index_content)
            print(f"[watch] ➕ Added: {p.name}")

    def on_modified(self, event: FileSystemEvent) -> None:
        if self._should_ignore(event.src_path):
            return
        p = Path(event.src_path)
        if p.is_file():
            self.indexer.index_file(p, index_content=self.index_content)
            print(f"[watch] 🔄 Updated: {p.name}")

    def on_deleted(self, event: FileSystemEvent) -> None:
        p = Path(event.src_path)
        self.indexer.delete_file_from_index(p)
        print(f"[watch] 🗑️ Deleted: {p.name}")

    def on_moved(self, event: FileSystemEvent) -> None:
        src = Path(event.src_path)
        dest = Path(getattr(event, "dest_path", ""))
        self.indexer.delete_file_from_index(src)
        if dest.exists() and not self._should_ignore(str(dest)):
            self.indexer.index_file(dest, index_content=self.index_content)
            print(f"[watch] 📦 Moved: {src.name} -> {dest.name}")


def start_watcher(path: Path, index_content: bool = True, blocking: bool = True) -> Optional[Observer]:
    """Start watching a folder and synchronize all file changes directly to the index."""
    if not HAS_WATCHDOG:
        raise RuntimeError("watchdog is required for the directory watcher. Run: pip install watchdog")

    target = path.resolve()
    if not target.exists():
        raise FileNotFoundError(f"Path does not exist: {target}")

    indexer = LocalIndexer()
    event_handler = IndexSyncHandler(indexer, index_content=index_content)
    observer = Observer()
    observer.schedule(event_handler, str(target), recursive=True)
    observer.start()

    print(f"👀 Baizo Watcher started for '{target}' (content={index_content}).")
    print("Files created, updated, or deleted in this directory will be indexed automatically.")
    print("Press Ctrl+C to stop.\n")

    if blocking:
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\n🛑 Watcher stopped.")
        observer.join()
        return None

    return observer
