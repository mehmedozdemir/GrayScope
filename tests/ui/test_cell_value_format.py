"""Tests for the cell-value formatters (pure functions, no Qt app needed)."""
from __future__ import annotations

from app.ui.components.cell_value_dialog import (
    auto_format,
    format_json,
    format_xml,
    format_yaml,
)


def test_format_json_pretty_prints():
    out = format_json('{"b":2,"a":[1,2]}')
    assert out is not None
    assert "\n" in out and '  "b": 2' in out


def test_format_json_invalid_returns_none():
    assert format_json("not json") is None


def test_format_xml_pretty_prints_multiline():
    out = format_xml("<root><a>1</a><b>2</b></root>")
    assert out is not None
    assert out.count("\n") >= 3
    assert "<a>1</a>" in out


def test_format_xml_invalid_returns_none():
    assert format_xml("just text") is None


def test_format_yaml_roundtrips_mapping():
    out = format_yaml("a: 1\nb:\n  - x\n  - y\n")
    assert out is not None
    assert "a: 1" in out and "- x" in out


def test_auto_format_detects_json_and_falls_back_to_plain():
    kind, text = auto_format('{"a":1}')
    assert kind == "JSON"
    assert auto_format("merhaba dünya") == ("Düz metin", "merhaba dünya")
