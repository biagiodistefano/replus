"""Loading of pattern templates from JSON files or plain dicts."""

from __future__ import annotations

import json
import os
from collections.abc import Generator
from pathlib import Path
from typing import TypeAlias

from .exceptions import DuplicatePatternKeyError

TemplateAlternatives: TypeAlias = dict[str, list[str]]
TemplateSource: TypeAlias = "str | os.PathLike[str] | dict[str, TemplateAlternatives]"

RUN_PATTERNS_KEY = "$PATTERNS"


def load_templates(source: TemplateSource) -> tuple[TemplateAlternatives, TemplateAlternatives]:
    """Load pattern templates from a directory of ``*.json`` files or a dict of dicts.

    All keys except :data:`RUN_PATTERNS_KEY` are merged into a single shared
    namespace, usable as ``{{placeholders}}`` by any template. The entries under
    each source's ``$PATTERNS`` key become the runnable patterns of that source,
    keyed by the file stem (or dict key), which becomes the match *type*.

    Args:
        source: Path to a directory containing ``*.json`` template files, or a
            dict mapping template names to template dicts.

    Returns:
        A ``(shared, runnable)`` tuple: the merged placeholder namespace and the
        runnable patterns per template name.

    Raises:
        DuplicatePatternKeyError: If the same key is defined by two sources.
        TypeError: If ``source`` is neither a path nor a dict.
    """
    if isinstance(source, str | os.PathLike):
        items = _iter_path(source)
    elif isinstance(source, dict):
        items = ((name, name, template) for name, template in source.items())
    else:
        raise TypeError(f"'source' must be a str, os.PathLike or dict, got {type(source).__name__}")

    shared: TemplateAlternatives = {}
    runnable: TemplateAlternatives = {}
    origins: dict[str, str] = {}
    for origin, name, template in items:
        alternatives = dict(template)  # never mutate the caller's dict
        run_patterns = alternatives.pop(RUN_PATTERNS_KEY, None)
        if run_patterns:
            runnable[name] = run_patterns
        for key in alternatives:
            if key in origins:
                raise DuplicatePatternKeyError(
                    f"duplicate pattern key {key!r} in {origin}, already defined in {origins[key]}"
                )
            origins[key] = origin
        shared.update(alternatives)
    return shared, runnable


def _iter_path(path: str | os.PathLike[str]) -> Generator[tuple[str, str, TemplateAlternatives]]:
    for filepath in sorted(Path(path).absolute().iterdir()):
        if filepath.is_file() and filepath.suffix == ".json":
            with filepath.open("r", encoding="utf-8") as f:
                yield str(filepath), filepath.stem, json.load(f)
