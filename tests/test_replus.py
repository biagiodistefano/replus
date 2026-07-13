"""The 0.3.0 test suite, ported: locks the behavior v1.0.0 promised to preserve."""

from pathlib import Path

import pytest
import regex

import replus
from replus import Replus, exceptions


def test_version() -> None:
    assert replus.__version__ == "1.0.0"


def test_parser_regex(engine: Replus) -> None:
    patterns = [p.regex.pattern for p in engine.patterns if p.type == "tests"]
    expected = [
        r"This is an unnamed number group: (?:\d).",
        r"I can match (?P<abg_0>alpha|beta|gamma) and "
        r"(?P<abg_1>alpha|beta|gamma), and then re-match the last (?P=abg_1) or the second last (?P=abg_0)",
        r"Here is some (?:spam) and some (?>eggs)",
        r"(?<!foo|bar) blah blah, (?!foo|bar) foo foo, (?<=foo|bar) bar bar, (?=foo|bar) yoyo",
        r"(?<=alpha|beta|gamma) (?<!alpha|beta|gamma) (?!alpha|beta|gamma) (?=alpha|beta|gamma)",
    ]
    assert patterns == expected


def test_flags(models_dir: Path) -> None:
    engine_i = Replus(models_dir, flags=regex.IGNORECASE)
    assert len(engine_i.parse("Today it's January 1st 1970")) == 1
    engine_ii = Replus(models_dir)
    assert len(engine_ii.parse("Today it's January 1st 1970")) == 0


def test_match(engine: Replus) -> None:
    matches = engine.parse("Today is january 1st 1970")
    assert len(matches) == 1
    date_ = matches[0]
    assert date_.value == "january 1st 1970"
    assert date_.group("month_name").value == "january"
    assert date_.group("day").value == "1"
    assert date_.group("year").value == "1970"


def test_search_returns_none(engine: Replus) -> None:
    assert engine.search("Today is january 1st 19xx") is None


def test_match_with_no_groups(models_dir: Path) -> None:
    match = Replus(models_dir).search("Pattern with no groups")
    assert match is not None
    assert match.first() is None
    assert match.last() is None


def test_first(engine: Replus) -> None:
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    first = date_match.first()
    assert first is not None
    assert first.value == "january 1st 1970"


def test_last(engine: Replus) -> None:
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    last = date_match.last()
    assert last is not None
    assert last.value == "1970"


def test_start_end(engine: Replus) -> None:
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    assert date_match.start() == 9
    assert date_match.start("year") == 21
    assert date_match.end() == 25
    assert date_match.end("year") == 25


def test_start_end_no_such_group(engine: Replus) -> None:
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    with pytest.raises(exceptions.NoSuchGroupError):
        date_match.start("foo")
    with pytest.raises(exceptions.NoSuchGroupError):
        date_match.end("foo")


def test_span(engine: Replus) -> None:
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    assert date_match.span() == (9, 25)
    assert date_match.span("year") == (21, 25)


def test_span_no_such_group(engine: Replus) -> None:
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    with pytest.raises(exceptions.NoSuchGroupError):
        date_match.span("foo")


def test_repeat(engine: Replus) -> None:
    repeat_match = engine.search("foobar 34 of 1997 15 of 1988 45 of 1975")
    assert len(repeat_match.group("numyear").reps()) == 3


def test_partial(engine: Replus) -> None:
    partial_match = engine.search("march 3rd", partial=True)
    assert partial_match is not None, "Did not match"
    assert partial_match.partial


def test_build_pattern_error() -> None:
    patterns = {"test": {"test": ["This is a test (pattern"], "$PATTERNS": ["{{test}}"]}}
    with pytest.raises(exceptions.PatternBuildError):
        Replus(patterns)


def test_whitespace_noise() -> None:
    patterns = {"test": {"test": ["This is a test (pattern)"], "$PATTERNS": ["{{test}}"]}}
    noisy_engine = Replus(patterns, whitespace_noise="#")
    matches = noisy_engine.parse("This#is#a#test#pattern")
    assert len(matches) == 1
    assert matches[0].value == "This#is#a#test#pattern"


def test_json(engine: Replus) -> None:
    matches = engine.parse("Here is some spam and some eggs")
    assert matches[0].json() == '{"type": "tests", "offset": {"start": 0, "end": 31}, "value": "Here is some spam and some eggs", "groups": {}}'  # noqa: E501
    matches = engine.parse("Today is january 1st 1970")
    assert matches[0].json() == '{"type": "date", "offset": {"start": 9, "end": 25}, "value": "january 1st 1970", "groups": {"date": [{"key": "date", "name": "date_0", "offset": {"start": 9, "end": 25}, "value": "january 1st 1970", "groups": {"month_name": [{"key": "month_name", "name": "month_name_0", "offset": {"start": 9, "end": 16}, "value": "january", "groups": {}}], "day": [{"key": "day", "name": "day_1", "offset": {"start": 17, "end": 18}, "value": "1", "groups": {}}], "year": [{"key": "year", "name": "year_1", "offset": {"start": 21, "end": 25}, "value": "1970", "groups": {}}]}}]}}'  # noqa: E501


def test_patterns_duplicate(invalid_models_dir: Path) -> None:
    with pytest.raises(exceptions.DuplicatePatternKeyError):
        Replus(invalid_models_dir / "duplicate")


def test_patterns_invalid_special(invalid_models_dir: Path) -> None:
    with pytest.raises(exceptions.UnknownTemplateGroupError):
        Replus(invalid_models_dir / "special")


def test_patterns_invalid_group(invalid_models_dir: Path) -> None:
    with pytest.raises(exceptions.UnknownTemplateGroupError):
        Replus(invalid_models_dir / "group")


def test_init_wrong_type() -> None:
    with pytest.raises(TypeError):
        Replus(1)  # type: ignore[arg-type]
