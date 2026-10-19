from __future__ import annotations

from baizo.cli import build_parser


def test_cli_parser_find() -> None:
    parser = build_parser()
    args = parser.parse_args(["find", "report.pdf", "--root", "D:\\Docs", "--max-results", "10", "--open"])
    assert args.subcommand == "find"
    assert args.query == ["report.pdf"]
    assert args.root == ["D:\\Docs"]
    assert args.max_results == 10
    assert args.open is True


def test_cli_parser_grep() -> None:
    parser = build_parser()
    args = parser.parse_args(["grep", "def main", "--path", "D:\\src", "--ext", "py"])
    assert args.subcommand == "grep"
    assert args.pattern == "def main"
    assert args.path == "D:\\src"
    assert args.ext == "py"


def test_cli_parser_ask() -> None:
    parser = build_parser()
    args = parser.parse_args(["ask", "where", "is", "my", "code?"])
    assert args.subcommand == "ask"
    assert args.prompt == ["where", "is", "my", "code?"]


def test_cli_parser_index() -> None:
    parser = build_parser()
    args = parser.parse_args(["index", "add", "D:\\projects", "--content"])
    assert args.subcommand == "index"
    assert args.index_action == "add"
    assert args.path == "D:\\projects"
    assert args.content is True
