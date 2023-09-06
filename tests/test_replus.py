from pathlib import Path

import pytest
import regex

from replus import Replus
from replus import exceptions
from .test_models.date import date
from .test_models.repeated import repeated
from .test_models.tests import tests

HERE = Path(__file__).parent.absolute()

engine = Replus(dict(date=date, repeated=repeated, tests=tests))


def test_parser_regex():
    patterns = [p.pattern for k, p, t in engine.patterns if k == "tests"]
    expected = [
        r"This is an unnamed number group: (?:\d).",
        r"I can match (?P<abg_0>alpha|beta|gamma) and (?P<abg_1>alpha|beta|gamma), and then re-match the last (?P=abg_1) or the second last (?P=abg_0)",
        # noqa: E501
        r"Here is some (?:spam) and some (?>eggs)",
        r"(?<!foo|bar) blah blah, (?!foo|bar) foo foo, (?<=foo|bar) bar bar, (?=foo|bar) yoyo",
        r"(?<=alpha|beta|gamma) (?<!alpha|beta|gamma) (?!alpha|beta|gamma) (?=alpha|beta|gamma)"
    ]
    for i, p in enumerate(patterns):
        assert p == expected[i]


def test_flags():
    test_models_path = HERE / "test_models"
    engine_i = Replus(test_models_path, flags=regex.IGNORECASE)
    matches = engine_i.parse("Today it's January 1st 1970")
    assert len(matches) == 1
    engine_ii = Replus(test_models_path)
    matches = engine_ii.parse("Today it's January 1st 1970")
    assert len(matches) == 0


def test_match():
    matches = engine.parse("Today is january 1st 1970")
    assert len(matches) == 1
    date_ = matches[0]
    assert date_.value == "january 1st 1970"
    month = date_.group("month_name")
    assert month.value == "january"
    day = date_.group("day")
    assert day.value == "1"
    year = date_.group("year")
    assert year.value == "1970"


def test_search_returns_none():
    date_match = engine.search("Today is january 1st 19xx")
    assert date_match is None


def test_first():
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    first = date_match.first()
    assert first is not None


def test_start_end():
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    assert date_match.start() == 9
    assert date_match.start("year") == 21
    assert date_match.end() == 25
    assert date_match.end("year") == 25


def test_start_end_no_such_group():
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    with pytest.raises(exceptions.NoSuchGroup):
        _ = date_match.start("foo")
    with pytest.raises(exceptions.NoSuchGroup):
        _ = date_match.end("foo")


def test_span():
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    assert date_match.span() == (9, 25)
    assert date_match.span("year") == (21, 25)


def test_span_no_such_group():
    date_match = engine.search("Today is january 1st 1970", filters=["date"])
    with pytest.raises(exceptions.NoSuchGroup):
        _ = date_match.span("foo")


def test_repeat():
    repeat_match = engine.search("foobar 34 of 1997 15 of 1988 45 of 1975")
    assert len(repeat_match.group("numyear").reps()) == 3


def test_partial():
    partial_match = engine.search("march 3rd", partial=True)
    assert partial_match is not None, "Did not match"
    assert partial_match.partial


def test_build_pattern_error():
    _patterns = {
        "test": {
            "test": [
                "This is a test (pattern",
            ],
            "$PATTERNS": ["{{test}}"],
        }
    }
    with pytest.raises(exceptions.PatternBuildException):
        _ = Replus(_patterns)


def test_whitespace_noise():
    _patterns = {
        "test": {
            "test": [
                "This is a test (pattern)",
            ],
            "$PATTERNS": ["{{test}}"],
        }
    }
    _engine = Replus(_patterns, whitespace_noise="#")
    matches = _engine.parse("This#is#a#test#pattern")
    assert len(matches) == 1
    assert matches[0].value == "This#is#a#test#pattern"


def test_json():
    matches = engine.parse("Here is some spam and some eggs")
    assert matches[0].json() == '{"type": "tests", "offset": {"start": 0, "end": 31}, "value": "Here is some spam and some eggs", "groups": {}}'  # noqa: E501
    matches = engine.parse("Today is january 1st 1970")
    assert matches[0].json() == '{"type": "date", "offset": {"start": 9, "end": 25}, "value": "january 1st 1970", "groups": {"date": [{"key": "date", "name": "date_0", "offset": {"start": 9, "end": 25}, "value": "january 1st 1970", "groups": {"month_name": [{"key": "month_name", "name": "month_name_0", "offset": {"start": 9, "end": 16}, "value": "january", "groups": {}}], "day": [{"key": "day", "name": "day_1", "offset": {"start": 17, "end": 18}, "value": "1", "groups": {}}], "year": [{"key": "year", "name": "year_1", "offset": {"start": 21, "end": 25}, "value": "1970", "groups": {}}]}}]}}'  # noqa: E501


def test_patterns_wrong_type():
    invalid_models = HERE / "invalid_models"
    with pytest.raises(KeyError):
        _ = Replus(invalid_models)
