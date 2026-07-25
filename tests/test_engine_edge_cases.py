"""Tests for engine edge cases and parameter pass-throughs."""

import pytest

from replus import Group, Replus


@pytest.fixture(scope="module")
def sample_engine() -> Replus:
    templates = {
        "alpha": {
            "word": ["\\b[a-zA-Z]+\\b"],
            "alpha_pat": ["{{word}}"],
            "$PATTERNS": ["{{alpha_pat}}"],
        },
        "num": {
            "digits": ["\\d+"],
            "num_pat": ["{{digits}}"],
            "$PATTERNS": ["{{num_pat}}"],
        },
    }
    return Replus(templates)


def test_timeout_and_concurrent_pass_through(sample_engine: Replus) -> None:
    # Verify timeout and concurrent parameters execute without error
    matches = sample_engine.parse("hello 123 world 456", concurrent=True, timeout=5.0)
    assert len(matches) == 4

    iter_matches = list(sample_engine.finditer("hello 123", concurrent=True, timeout=5.0))
    assert len(iter_matches) == 2

    search_match = sample_engine.search("hello 123", concurrent=True, timeout=5.0)
    assert search_match is not None
    assert search_match.type == "alpha"


def test_sub_empty_string_replacement(sample_engine: Replus) -> None:
    # Verify replacing captures with empty string "" strips matched text
    result = sample_engine.sub("hello 123 world", {"word": ""})
    assert result == " 123 "


def test_sub_zero_width_replacements() -> None:
    # Verify sub handles zero-width match captures cleanly
    templates = {
        "boundary": {
            "start": ["^"],
            "rule": ["{{start}}hello"],
            "$PATTERNS": ["{{rule}}"],
        }
    }
    engine = Replus(templates)
    res = engine.sub("hello world", {"start": "[START]"})
    assert res == "[START]hello world"


def test_sub_callable_exception_propagates(sample_engine: Replus) -> None:
    # Verify user exception inside replacement callable propagates out
    def failing_replacer(g: Group) -> str:
        raise RuntimeError("Custom replacer failure")

    with pytest.raises(RuntimeError, match="Custom replacer failure"):
        sample_engine.sub("hello 123", {"word": failing_replacer})


def test_combined_filters_and_exclude(sample_engine: Replus) -> None:
    # Test simultaneous filters and exclude parameters
    text = "hello 123 world 456"

    # Only run 'alpha', but exclude 'alpha' -> yields nothing
    matches = sample_engine.parse(text, filters=["alpha"], exclude=["alpha"])
    assert matches == []

    # Run 'alpha' and 'num', but exclude 'num' -> yields only 'alpha'
    matches_filtered = sample_engine.parse(text, filters=["alpha", "num"], exclude=["num"])
    assert len(matches_filtered) == 2
    assert all(m.type == "alpha" for m in matches_filtered)
