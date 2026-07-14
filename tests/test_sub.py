import pytest

from replus import Group, NoSuchGroupError, OverlappingReplacementError, Replus


@pytest.fixture(scope="module")
def serial_engine() -> Replus:
    templates = {
        "serial": {
            "prefix": ["[1lI]"],
            "digits": ["\\d{6}"],
            "serial": ["{{prefix}}{{digits}}"],
            "$PATTERNS": ["{{serial}}"],
        }
    }
    return Replus(templates)


def test_sub_literal(serial_engine: Replus) -> None:
    result = serial_engine.sub("ID 1809900 and 1809900", {"prefix": "l"})
    assert result == "ID l809900 and l809900"


def test_sub_callable_receives_group(serial_engine: Replus) -> None:
    result = serial_engine.sub(
        "ID 1809900 and I809900",
        {"prefix": lambda g: g.value.replace("1", "l").replace("I", "l")},
    )
    assert result == "ID l809900 and l809900"


def test_sub_only_touches_matched_spans(serial_engine: Replus) -> None:
    # the stray "1" outside any match must survive
    result = serial_engine.sub("1 unmatched, 1809900 matched", {"prefix": "l"})
    assert result == "1 unmatched, l809900 matched"


def test_sub_replacement_is_literal_not_escaped(serial_engine: Replus) -> None:
    result = serial_engine.sub("1809900", {"prefix": "\\g<0>$1"})
    assert result == "\\g<0>$1809900"


def test_sub_replaces_every_repetition(engine: Replus) -> None:
    result = engine.sub("foobar 34 of 1997 15 of 1988 45 of 1975", {"num": "NN"})
    assert result == "foobar NN of 1997 NN of 1988 NN of 1975"


def test_sub_multiple_sibling_keys(engine: Replus) -> None:
    result = engine.sub("Today is 25/12/1970", {"day": "DD", "month": "MM"})
    assert result == "Today is DD/MM/1970"


def test_sub_key_unmatched_in_alternative_is_skipped() -> None:
    templates = {"t": {"a": ["x"], "b": ["y"], "ab": ["{{a}}|{{b}}"], "$PATTERNS": ["{{ab}}"]}}
    assert Replus(templates).sub("x", {"b": "Z"}) == "x"


def test_sub_unknown_key_raises(serial_engine: Replus) -> None:
    with pytest.raises(NoSuchGroupError, match="prefix_typo"):
        serial_engine.sub("1809900", {"prefix_typo": "l"})


def test_sub_overlapping_edits_raise(engine: Replus) -> None:
    with pytest.raises(OverlappingReplacementError, match="date"):
        engine.sub("Today is 25/12/1970", {"date": "X", "day": "Y"})


def test_sub_overlapped_matching_rejected(serial_engine: Replus) -> None:
    with pytest.raises(ValueError, match="overlapped"):
        serial_engine.sub("1809900", {"prefix": "l"}, overlapped=True)


def test_sub_overlapped_false_is_accepted(serial_engine: Replus) -> None:
    assert serial_engine.sub("1809900", {"prefix": "l"}, overlapped=False) == "l809900"


def test_sub_empty_replacements_is_noop(serial_engine: Replus) -> None:
    assert serial_engine.sub("ID 1809900", {}) == "ID 1809900"


def test_sub_no_match_returns_input(serial_engine: Replus) -> None:
    assert serial_engine.sub("nothing here", {"prefix": "l"}) == "nothing here"


def test_sub_respects_filters(engine: Replus) -> None:
    text = "Today is 25/12/1970"
    assert engine.sub(text, {"day": "DD"}, exclude=["date"]) == text


def test_sub_callable_can_use_rep_index(engine: Replus) -> None:
    def only_first(group: Group) -> str:
        return "NN" if group.rep_index == 0 else group.value

    result = engine.sub("foobar 34 of 1997 15 of 1988", {"num": only_first})
    assert result == "foobar NN of 1997 15 of 1988"
