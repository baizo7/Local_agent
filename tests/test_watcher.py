from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from baizo.core.indexer import LocalIndexer
from baizo.core.watcher import IndexSyncHandler


def test_index_sync_handler(tmp_path: Path) -> None:
    db_file = tmp_path / "watcher_test.db"
    indexer = LocalIndexer(db_path=db_file)
    handler = IndexSyncHandler(indexer, index_content=True)

    # 1. Test creation event
    doc = tmp_path / "live_doc.txt"
    doc.write_text("Real-time streaming index sync content")
    event_created = MagicMock(src_path=str(doc))
    handler.on_created(event_created)

    search_res = indexer.search("streaming")
    assert len(search_res) >= 1
    assert any("live_doc.txt" in r.path.name for r in search_res)

    # 2. Test modified event
    doc.write_text("Updated contents with quantum entanglement")
    event_modified = MagicMock(src_path=str(doc))
    handler.on_modified(event_modified)

    search_updated = indexer.search("quantum")
    assert len(search_updated) >= 1

    # 3. Test deleted event
    event_deleted = MagicMock(src_path=str(doc))
    handler.on_deleted(event_deleted)

    search_after_del = indexer.search("quantum")
    assert len(search_after_del) == 0
