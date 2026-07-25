"""Tests for engine edge cases and parameter pass-throughs."""

from collections.abc import Callable

import pytest

from replus import Group, Match, Replus


def _first(engine: Replus, text: str, *, overlapped: bool = False) -> Match | None:
    """The contract search() must honour: the first match parse() would return."""
    return next(iter(engine.parse(text, overlapped=overlapped)), None)


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


@pytest.mark.parametrize(
    "run",
    [
        pytest.param(lambda e, t: e.parse(t, timeout=0.1), id="parse"),
        # finditer is lazy: force evaluation so the match actually runs.
        pytest.param(lambda e, t: list(e.finditer(t, timeout=0.1)), id="finditer"),
        pytest.param(lambda e, t: e.search(t, timeout=0.1), id="search"),
    ],
)
def test_timeout_actually_forwarded(run: Callable[[Replus, str], object]) -> None:
    # A catastrophic-backtracking pattern whose un-timed run takes seconds, capped by a
    # 0.1s timeout, must raise TimeoutError (the builtin — regex has no TimeoutError).
    # A count-only assertion would pass even if timeout were silently dropped; this proves
    # the parameter reaches regex. The runtime margin (seconds vs. 0.1s) keeps it reliable.
    engine = Replus({"evil": {"boom": ["(([a-z])+.)+[A-Z]([a-z])+$"], "$PATTERNS": ["{{boom}}"]}})
    text = "a" * 140
    with pytest.raises(TimeoutError):
        run(engine, text)


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


# --- search() must equal parse()[0], including on overlapping cross-type patterns ---


@pytest.mark.parametrize(
    ("patterns", "text"),
    [
        # (short-ending, long-ending) prefix/overlap shapes purge_overlaps resolves by length.
        ((r"\d\d", r"\d{6}"), "123456"),
        ((r"5\d", r"\d{10}"), "0123456789"),
        ((r"\d{4}", r"\d{4}-\d\d-\d\d"), "1970-12-25"),
        ((r"ab", r"abc"), "abc"),
        ((r"bc", r"abcd"), "abcd"),
    ],
)
@pytest.mark.parametrize("reverse", [False, True])
def test_search_equals_parse_first_on_overlap(patterns: tuple[str, str], text: str, reverse: bool) -> None:
    # Declaration order must not change the result: search() keeps the longest of an
    # overlapping run, exactly as parse()[0] does. A prior lazy-search regression bounded
    # the scan by an earlier/shorter match's start and silently returned the wrong match.
    ordered = list(reversed(patterns)) if reverse else list(patterns)
    templates = {f"t{i}": {f"g{i}": [pat], "$PATTERNS": [f"{{{{g{i}}}}}"]} for i, pat in enumerate(ordered)}
    engine = Replus(templates)

    expected = _first(engine, text)
    got = engine.search(text)
    assert got is not None
    assert expected is not None
    assert (got.type, got.value, got.span()) == (expected.type, expected.value, expected.span())


def test_search_overlapped_matches_parse_first(sample_engine: Replus) -> None:
    # overlapped=True is a documented parse() kwarg; search() must accept it (not crash
    # with a TypeError from the underlying compiled pattern) and match parse()[0].
    text = "hello 123 world"
    got = sample_engine.search(text, overlapped=True)
    expected = _first(sample_engine, text, overlapped=True)
    assert got is not None
    assert expected is not None
    assert (got.type, got.value, got.span()) == (expected.type, expected.value, expected.span())


def test_search_empty_result_matches_parse(sample_engine: Replus) -> None:
    # When nothing matches, search() returns None just like parse()[0].
    assert sample_engine.search("!!!") is None
    assert _first(sample_engine, "!!!") is None
