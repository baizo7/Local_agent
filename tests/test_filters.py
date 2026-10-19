from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from baizo.core.filters import (
    DEFAULT_IGNORED_DIRS,
    SearchFilter,
    parse_date_filter,
    parse_size_to_bytes,
)


def test_parse_size_to_bytes() -> None:
    op, sz = parse_size_to_bytes(">10MB")
    assert op == ">"
    assert sz == 10 * 1024 * 1024

    op, sz = parse_size_to_bytes("<500KB")
    assert op == "<"
    assert sz == 500 * 1024

    op, sz = parse_size_to_bytes("+1GB")
    assert op == ">"
    assert sz == 1024**3

    op, sz = parse_size_to_bytes("256B")
    assert op == "="
    assert sz == 256


def test_parse_size_invalid() -> None:
    with pytest.raises(ValueError):
        parse_size_to_bytes("invalid_size")


def test_parse_date_filter() -> None:
    op, ts = parse_date_filter("<7d")
    assert op == "<"
    assert ts < time.time()
    assert ts > time.time() - 86400 * 8

    op, ts = parse_date_filter("2026-01-01")
    assert op == "<"
    assert ts > 0


def test_filter_matches_name() -> None:
    filt = SearchFilter(query="test")
    assert filt.matches_name("test_file.py")
    assert filt.matches_name("my_TEST_case.txt")
    assert not filt.matches_name("other.doc")


def test_filter_glob() -> None:
    filt = SearchFilter(query="*.py")
    assert filt.matches_name("main.py")
    assert filt.matches_name("test_case.py")
    assert not filt.matches_name("main.py.bak")


def test_filter_regex() -> None:
    filt = SearchFilter(query=r"^log_\d{4}\.txt$", is_regex=True)
    assert filt.matches_name("log_2026.txt")
    assert not filt.matches_name("log_abc.txt")
    assert not filt.matches_name("test_log_2026.txt")


def test_filter_extensions_and_type(tmp_path: Path) -> None:
    test_file = tmp_path / "hello.py"
    test_file.write_text("print('hello')")
    stat = test_file.stat()

    filt_ext = SearchFilter(query="", extensions={".py"})
    assert filt_ext.matches("hello.py", is_dir=False, stat_info=stat)

    filt_wrong_ext = SearchFilter(query="", extensions={".pdf"})
    assert not filt_wrong_ext.matches("hello.py", is_dir=False, stat_info=stat)

    filt_type_dir = SearchFilter(query="", file_type="dir")
    assert not filt_type_dir.matches("hello.py", is_dir=False, stat_info=stat)

    filt_type_file = SearchFilter(query="", file_type="file")
    assert filt_type_file.matches("hello.py", is_dir=False, stat_info=stat)


def test_ignored_directories() -> None:
    filt = SearchFilter()
    assert filt.should_ignore_dir(".git")
    assert filt.should_ignore_dir("node_modules")
    assert filt.should_ignore_dir("__pycache__")
    assert not filt.should_ignore_dir("src")
