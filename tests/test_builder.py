import pytest
import regex

from replus import Replus
from replus.builder import build_patterns
from replus.exceptions import (
    CircularReferenceError,
    InvalidBackreferenceError,
    PatternBuildError,
    UnknownTemplateGroupError,
)

from .conftest import found


def test_direct_cycle() -> None:
    with pytest.raises(CircularReferenceError, match=r"a -> a"):
        Replus({"t": {"a": ["{{a}}"], "$PATTERNS": ["{{a}}"]}})


def test_transitive_cycle_reports_path() -> None:
    templates = {"t": {"a": ["{{b}}"], "b": ["{{c}}"], "c": ["{{a}}"], "$PATTERNS": ["{{a}}"]}}
    with pytest.raises(CircularReferenceError, match=r"(a -> b -> c -> a|b -> c -> a -> b|c -> a -> b -> c)"):
        Replus(templates)


def test_diamond_reference_is_not_a_cycle() -> None:
    templates = {
        "t": {
            "top": ["{{left}} {{right}}"],
            "left": ["{{base}}"],
            "right": ["{{base}}"],
            "base": ["x"],
            "$PATTERNS": ["{{top}}"],
        }
    }
    engine = Replus(templates)
    assert engine.patterns[0].regex.pattern == "(?P<top_0>(?P<left_0>(?P<base_0>x)) (?P<right_0>(?P<base_1>x)))"


def test_cycle_check_resolves_prefixed_definitions() -> None:
    # {{number}} inside a shared key resolves to the "?:number" definition in the graph
    templates = {"t": {"wrapper": ["num: {{number}}"], "?:number": ["\\d"], "$PATTERNS": ["{{wrapper}}"]}}
    engine = Replus(templates)
    assert engine.patterns[0].regex.pattern == r"(?P<wrapper_0>num: (?:\d))"


def test_cycle_check_ignores_backreferences_and_unknowns() -> None:
    # a backreference inside a shared key is not an expansion edge, and an
    # undefined reference in a never-used key must not break the build
    templates = {
        "t": {
            "abg": ["alpha", "beta"],
            "pair": ["{{abg}}-{{#abg}}"],
            "unused": ["{{missing}}"],
            "also_unused": ["{{?>missing}}"],
            "$PATTERNS": ["{{pair}}"],
        }
    }
    engine = Replus(templates)
    assert engine.patterns[0].regex.pattern == "(?P<pair_0>(?P<abg_0>alpha|beta)-(?P=abg_0))"


def test_many_placeholders_do_not_recurse() -> None:
    # 0.3.0 recursed once per placeholder expansion; thousands blew the stack
    count = 2000
    template = " ".join(["{{w}}"] * count)
    engine = Replus({"t": {"w": ["x"], "$PATTERNS": [template]}})
    assert len(engine.patterns[0].group_names) == count
    match = engine.search(" ".join(["x"] * count))
    assert match is not None


def test_backreference_before_group() -> None:
    with pytest.raises(InvalidBackreferenceError, match="abg_-1"):
        Replus({"t": {"abg": ["alpha"], "$PATTERNS": ["{{#abg}} {{abg}}"]}})


def test_backreference_distance_too_far() -> None:
    with pytest.raises(InvalidBackreferenceError, match="abg_-1"):
        Replus({"t": {"abg": ["alpha"], "$PATTERNS": ["{{abg}} {{#abg@2}}"]}})


def test_backreference_to_undefined_key() -> None:
    with pytest.raises(UnknownTemplateGroupError, match="#missing"):
        Replus({"t": {"$PATTERNS": ["{{#missing}}"]}})


def test_unknown_special_group() -> None:
    with pytest.raises(UnknownTemplateGroupError, match=r"\?:invalid"):
        Replus({"t": {"$PATTERNS": ["{{?:invalid}}"]}})


def test_unknown_group_names_template() -> None:
    with pytest.raises(UnknownTemplateGroupError, match="does not exist"):
        Replus({"t": {"$PATTERNS": ["This is an invalid group: {{invalid}}."]}})


def test_compile_failure_wraps_cause() -> None:
    with pytest.raises(PatternBuildError, match="'t'") as exc_info:
        Replus({"t": {"bad": ["(unbalanced"], "$PATTERNS": ["{{bad}}"]}})
    assert isinstance(exc_info.value.__cause__, regex.error)


def test_special_group_advances_counter() -> None:
    # an unnamed {{?:key}} advances key's counter, exactly like 0.3.x
    engine = Replus({"t": {"abg": ["a", "b"], "$PATTERNS": ["{{abg}} {{?:abg}} {{abg}}"]}})
    assert engine.patterns[0].regex.pattern == "(?P<abg_0>a|b) (?:a|b) (?P<abg_2>a|b)"
    # 0.3.0 probed abg_0, abg_1, ... and stopped at the gap, losing abg_2
    match = found(engine.search("a b a"))
    assert [g.name for g in match.groups("abg")] == ["abg_0", "abg_2"]


def test_group_keys_survive_numeric_suffixes() -> None:
    # a user key that itself ends in _<digit> must not be mangled (0.3.0 stripped it)
    engine = Replus({"t": {"part_2": ["x+"], "$PATTERNS": ["{{part_2}} {{part_2}}"]}})
    compiled = engine.patterns[0]
    assert compiled.group_names == ("part_2_0", "part_2_1")
    assert compiled.group_keys == {"part_2_0": "part_2", "part_2_1": "part_2"}
    match = engine.search("xx xxx")
    assert match is not None
    assert found(match.group("part_2")).key == "part_2"
    assert [g.value for g in match.groups("part_2")] == ["xx", "xxx"]


def test_whitespace_noise_group_is_non_capturing() -> None:
    patterns = build_patterns({"greet": ["hello world"]}, {"t": ["{{greet}}"]}, whitespace_noise=r"[\s\-]+")
    assert patterns[0].regex.pattern == r"(?P<greet_0>hello(?:[\s\-]+)world)"


def test_flags_are_applied() -> None:
    patterns = build_patterns({"greet": ["hello"]}, {"t": ["{{greet}}"]}, flags=regex.IGNORECASE)
    assert patterns[0].regex.search("HELLO") is not None
