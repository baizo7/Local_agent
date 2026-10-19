from __future__ import annotations

from pathlib import Path

from baizo.core.content import ContentSearcher, is_binary_file


def test_is_binary_file(tmp_path: Path) -> None:
    text_file = tmp_path / "plain.txt"
    text_file.write_text("Hello plain text world")
    assert not is_binary_file(text_file)

    bin_file = tmp_path / "binary.bin"
    bin_file.write_bytes(b"\x00\x01\x02\x03hello")
    assert is_binary_file(bin_file)


def test_content_searcher(tmp_path: Path) -> None:
    code_file = tmp_path / "sample.py"
    code_file.write_text(
        "import os\n\ndef main():\n    # TODO: implement authentication\n    print('ready')\n"
    )

    searcher = ContentSearcher()
    matches = searcher.search_file(code_file, "TODO")
    assert len(matches) == 1
    assert matches[0].line_number == 4
    assert "implement authentication" in matches[0].line_text


def test_content_searcher_regex(tmp_path: Path) -> None:
    log_file = tmp_path / "app.log"
    log_file.write_text(
        "INFO 2026-10-19 Starting\nERROR code=404 Not Found\nINFO 2026-10-19 Done\n"
    )

    searcher = ContentSearcher()
    matches = searcher.search_file(log_file, r"ERROR\s+code=\d+", is_regex=True)
    assert len(matches) == 1
    assert matches[0].line_number == 2
