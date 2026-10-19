from __future__ import annotations

from pathlib import Path

from baizo.core.indexer import LocalIndexer


def test_local_indexer(tmp_path: Path) -> None:
    db_file = tmp_path / "test_index.db"
    indexer = LocalIndexer(db_path=db_file)

    # Populate sample directory
    work_dir = tmp_path / "work"
    work_dir.mkdir()
    f1 = work_dir / "quantum_computing.txt"
    f1.write_text("Superposition and entanglement in quantum mechanics.")
    f2 = work_dir / "machine_learning.txt"
    f2.write_text("Deep neural networks and transformer architecture.")

    stats = indexer.index_directory(work_dir, index_content=True)
    assert stats["added"] >= 2

    # Query by filename
    res1 = indexer.search("quantum")
    assert len(res1) >= 1
    assert any("quantum_computing" in r.path.name for r in res1)

    # Query by content
    res2 = indexer.search("transformer")
    assert len(res2) >= 1
    assert any("machine_learning" in r.path.name for r in res2)

    # Check stats
    db_stats = indexer.get_stats()
    assert db_stats["files"] >= 2

    # Clear index
    indexer.clear()
    cleared_stats = indexer.get_stats()
    assert cleared_stats["files"] == 0
