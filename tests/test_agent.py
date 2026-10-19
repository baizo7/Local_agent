from __future__ import annotations

from pathlib import Path

from baizo.agent.nlp_fallback import NaturalLanguageIntentEngine
from baizo.agent.tools import (
    tool_find_files,
    tool_get_system_info,
    tool_grep_content,
    tool_read_file,
)


def test_tool_get_system_info() -> None:
    info = tool_get_system_info()
    assert "os" in info
    assert "available_roots" in info
    assert len(info["available_roots"]) > 0


def test_tool_read_file(tmp_path: Path) -> None:
    sample = tmp_path / "read_sample.txt"
    sample.write_text("Line 1\nLine 2\nLine 3\n")

    res = tool_read_file(str(sample), start_line=1, max_lines=2)
    assert res["lines_read"] == 2
    assert "Line 1" in res["content"]


def test_tool_find_files(tmp_path: Path) -> None:
    (tmp_path / "search_target.py").write_text("pass")
    res = tool_find_files(query="search_target", root=str(tmp_path))
    assert res["count"] >= 1
    assert any("search_target.py" in r["name"] for r in res["results"])


def test_nlp_fallback_engine(tmp_path: Path) -> None:
    (tmp_path / "invoice_2026.pdf").write_bytes(b"%PDF-1.4 sample")

    engine = NaturalLanguageIntentEngine()
    reply, meta = engine.process("system info")
    assert meta["tool"] == "get_system_info"
    assert "System" in reply

    reply, meta = engine.process(f"find invoice in {tmp_path}")
    assert meta["tool"] == "find_files"
    assert "invoice_2026.pdf" in reply


def test_nlp_standard_user_folders() -> None:
    engine = NaturalLanguageIntentEngine()
    reply, meta = engine.process("find my downloads folder")
    assert "Downloads" in reply
    assert "C:" in reply or "/" in reply

    reply, meta = engine.process("where is my desktop folder")
    assert "Desktop" in reply


def test_nlp_explicit_drive_folders() -> None:
    engine = NaturalLanguageIntentEngine()
    reply, meta = engine.process("find my d disk drive downloads folder")
    assert "D:" in reply
    assert "Downloads" in reply


