from replus import Group, Match, Replus


def test_repr(engine: Replus) -> None:
    match = engine.search("Today is january 1st 1970")
    assert repr(match) == "<[Match date] span(9, 25): january 1st 1970>"
    assert repr(match.group("year")) == "<Group year_1 span(21, 25) @0: '1970'>"


def test_nested_group_query(engine: Replus) -> None:
    match = engine.search("Today is january 1st 1970")
    date_group = match.group("date")
    assert date_group.group("day").value == "1"
    assert [g.value for g in date_group.groups("year")] == ["1970"]
    assert date_group.group("day").groups() == []


def test_group_query_for_unmatched_key(engine: Replus) -> None:
    match = engine.search("Today is january 1st 1970")
    assert match.group("bogus") is None
    assert match.groups("bogus") == []


def test_group_serialize_shape(engine: Replus) -> None:
    year = engine.search("Today is january 1st 1970").group("year")
    assert year.serialize() == {
        "key": "year",
        "name": "year_1",
        "offset": {"start": 21, "end": 25},
        "value": "1970",
        "groups": {},
    }


def test_reps_of_single_group_is_empty(engine: Replus) -> None:
    match = engine.search("Today is january 1st 1970")
    assert match.group("year").reps() == []


def test_reps_navigate_their_own_span(engine: Replus) -> None:
    match = engine.search("foobar 34 of 1997 15 of 1988 45 of 1975")
    reps = match.group("numyear").reps()
    assert [rep.value for rep in reps] == ["34 of 1997", "15 of 1988", "45 of 1975"]
    assert reps[2].group("num").value == "45"
    assert reps[2].group("fooyear").value == "1975"


def test_explicit_rep_index(engine: Replus) -> None:
    numyear = engine.search("foobar 34 of 1997 15 of 1988 45 of 1975").group("numyear")
    assert numyear.start(rep_index=1) == 18
    assert numyear.end(rep_index=0) == 17
    assert numyear.span(rep_index=2) == (29, 39)


def test_purge_overlaps_empty_and_single(engine: Replus) -> None:
    assert Replus.purge_overlaps([]) == []
    matches = engine.parse("Today is january 1st 1970")
    assert Replus.purge_overlaps(matches) == matches


def test_purge_keeps_longest_of_contained_and_tied_matches() -> None:
    templates = {
        "t": {
            "w": ["xyzzy"],
            "m": ["yzz"],
            "i": ["zz"],
            "y": ["y"],
            "$PATTERNS": ["{{w}}", "{{m}}", "{{i}}", "{{y}}"],
        }
    }
    matches = Replus(templates).parse("xyzzy")
    assert [m.value for m in matches] == ["xyzzy"]


def test_purge_replaces_shorter_prefix_match() -> None:
    templates = {"t": {"aa": ["aa"], "a4": ["aaaa"], "$PATTERNS": ["{{aa}}", "{{a4}}"]}}
    matches = Replus(templates).parse("aaaa")
    assert [m.value for m in matches] == ["aaaa"]


def test_purge_keeps_disjoint_matches() -> None:
    templates = {"t": {"aa": ["aa"], "a4": ["aaaa"], "$PATTERNS": ["{{aa}}", "{{a4}}"]}}
    matches = Replus(templates).parse("aa aa")
    assert [m.value for m in matches] == ["aa", "aa"]


def test_parse_overlapped_returns_sorted_unpurged() -> None:
    templates = {"t": {"nn": ["\\d\\d"], "$PATTERNS": ["{{nn}}"]}}
    matches = Replus(templates).parse("123", overlapped=True)
    assert [m.value for m in matches] == ["12", "23"]


def test_finditer_is_lazy_and_unpurged() -> None:
    templates = {"t": {"aa": ["aa"], "a4": ["aaaa"], "$PATTERNS": ["{{aa}}", "{{a4}}"]}}
    engine = Replus(templates)
    iterator = engine.finditer("aaaa")
    first = next(iterator)
    assert isinstance(first, Match)
    assert first.value == "aa"
    assert len([first, *iterator]) == 3  # (0,2), (2,4), (0,4): no purging


def test_group_captured_outside_match_span_is_excluded() -> None:
    # a named group inside a lookbehind captures before the match starts;
    # groups() must only return captures within the match's own span
    templates = {"t": {"abg": ["alpha"], "$PATTERNS": ["(?<={{abg}})x"]}}
    match = Replus(templates).search("alphax")
    assert match is not None
    assert match.value == "x"
    assert match.groups() == []


def test_exclude(engine: Replus) -> None:
    assert engine.parse("Today is january 1st 1970", exclude=["date"]) == []


def test_group_type() -> None:
    templates = {"t": {"num": ["\\d+"], "$PATTERNS": ["{{num}}"]}}
    match = Replus(templates).search("42")
    assert isinstance(match.group("num"), Group)
    assert match.type == "t"
    assert match.length == 2
    assert match.all_group_names == ("num_0",)
