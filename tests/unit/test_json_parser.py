"""Tests for defensive LLM JSON response parsing."""

from __future__ import annotations

import inspect

from backend.app.services.llm import json_parser
from backend.app.services.llm.json_parser import JsonParseError, extract_json_object
from pytest import raises


def test_extract_json_object_parses_raw_json() -> None:
    assert extract_json_object('{"status":"ok"}') == {"status": "ok"}


def test_extract_json_object_parses_markdown_fenced_json() -> None:
    assert extract_json_object('```json\n{"status":"ok"}\n```') == {"status": "ok"}


def test_extract_json_object_parses_leading_trailing_whitespace() -> None:
    assert extract_json_object('\n  {"status":"ok"}  \n') == {"status": "ok"}


def test_extract_json_object_parses_one_object_with_extra_text() -> None:
    assert extract_json_object('Result follows: {"status":"ok"} done.') == {"status": "ok"}


def test_extract_json_object_rejects_invalid_json() -> None:
    with raises(JsonParseError):
        extract_json_object("not-json")


def test_json_parser_does_not_use_eval() -> None:
    source = inspect.getsource(json_parser)

    assert "eval(" not in source
