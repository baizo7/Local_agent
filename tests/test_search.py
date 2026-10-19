from __future__ import annotations

from pathlib import Path

from baizo.core.filters import SearchFilter
from baizo.core.search import SearchEngine, SearchResult


def test_search_engine_basic(tmp_path: Path) -> None:
    # Setup test tree
    sub = tmp_path / "subfolder"
    sub.mkdir()
    f1 = tmp_path / "document_report.txt"
    f1.write_text("content 1")
    f2 = sub / "financial_report.pdf"
    f2.write_text("content 2")
    f3 = sub / "random_notes.md"
    f3.write_text("content 3")

    engine = SearchEngine()
    filt = SearchFilter(query="report")
    results, errors, stats = engine.search(filt, roots=[tmp_path])

    assert len(results) == 2
    names = {r.path.name for r in results}
    assert "document_report.txt" in names
    assert "financial_report.pdf" in names
    assert stats.matched_count == 2
    assert stats.duration_seconds >= 0.0


def test_search_engine_max_results(tmp_path: Path) -> None:
    for i in range(10):
        (tmp_path / f"item_{i}.txt").write_text("test")

    engine = SearchEngine()
    filt = SearchFilter(query="item")
    results, errors, stats = engine.search(filt, roots=[tmp_path], max_results=3)

    assert len(results) == 3


def test_search_result_readable_properties(tmp_path: Path) -> None:
    f = tmp_path / "size_test.txt"
    f.write_text("A" * 2048)  # 2 KB

    res = SearchResult(path=f, is_dir=False, size=f.stat().st_size, mtime=f.stat().st_mtime)
    assert "KB" in res.readable_size
    assert "-" != res.readable_mtime
