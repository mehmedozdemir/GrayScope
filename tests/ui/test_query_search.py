"""Tests for the result-grid search-term compiler (substring + wildcards)."""
from __future__ import annotations

from app.ui.pages.queries_page import compile_search


def test_empty_term_returns_none():
    assert compile_search("   ") is None


def test_substring_contains_match():
    pattern = compile_search("err")
    assert pattern.search("an error occurred")
    assert not pattern.search("all good")


def test_case_insensitive():
    assert compile_search("ERROR").search("internal error")


def test_star_wildcard():
    pattern = compile_search("err*500")
    assert pattern.search("error code 500")
    assert not pattern.search("error code 404")


def test_question_mark_wildcard():
    pattern = compile_search("cod?")
    assert pattern.search("status code")
    assert not pattern.search("co")
