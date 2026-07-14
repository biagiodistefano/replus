from pathlib import Path

import pytest

from replus.exceptions import DuplicatePatternKeyError
from replus.loader import load_templates


def test_load_from_directory(models_dir: Path) -> None:
    shared, runnable = load_templates(models_dir)
    assert "day" in shared
    assert "abg" in shared
    assert set(runnable) == {"date", "repeated", "tests"}
    assert "$PATTERNS" not in shared


def test_load_from_dict() -> None:
    shared, runnable = load_templates({"greet": {"hi": ["hello"], "$PATTERNS": ["{{hi}}"]}})
    assert shared == {"hi": ["hello"]}
    assert runnable == {"greet": ["{{hi}}"]}


def test_load_skips_non_json_files(models_dir: Path) -> None:
    # test_models also contains __init__.py, date.py, repeated.py, tests.py
    shared, _ = load_templates(models_dir)
    assert "date" in shared  # from date.json, not shadowed or broken by date.py


def test_load_source_without_run_patterns() -> None:
    shared, runnable = load_templates({"fragments": {"word": ["\\w+"]}})
    assert shared == {"word": ["\\w+"]}
    assert runnable == {}


def test_load_does_not_mutate_caller_dict() -> None:
    template = {"hi": ["hello"], "$PATTERNS": ["{{hi}}"]}
    load_templates({"greet": template})
    assert template == {"hi": ["hello"], "$PATTERNS": ["{{hi}}"]}


def test_duplicate_key_across_sources(invalid_models_dir: Path) -> None:
    with pytest.raises(DuplicatePatternKeyError, match="'day'"):
        load_templates(invalid_models_dir / "duplicate")


def test_duplicate_error_names_both_origins() -> None:
    with pytest.raises(DuplicatePatternKeyError, match="in b, already defined in a"):
        load_templates({"a": {"word": ["\\w+"]}, "b": {"word": ["\\w+"]}})


def test_invalid_source_type() -> None:
    with pytest.raises(TypeError, match="got int"):
        load_templates(42)  # ty: ignore[invalid-argument-type]
