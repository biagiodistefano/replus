"""Compilation of pattern templates into regular expressions.

Templates contain ``{{placeholders}}`` that expand into named groups. Expansion
is leftmost-first with rescan, so nested placeholders introduced by an expansion
are processed before later ones — group numbering (``key_0``, ``key_1``, …) and
backreference resolution depend on this order.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import regex

from .exceptions import (
    CircularReferenceError,
    InvalidBackreferenceError,
    PatternBuildError,
    UnknownTemplateGroupError,
)
from .loader import TemplateAlternatives

#: Grammar of a template placeholder: ``{{key}}``, ``{{?:key}}``, ``{{#key}}``, ``{{#key@2}}``, …
PLACEHOLDER = regex.compile(r"\{\{((?P<special>#|\?[:>!=]|\?[aimsxl]:|\?<[!=])?(?P<key>[\w_]+)(@(?P<index>\d+))?)\}\}")

#: Special prefixes a key may be *defined* with, e.g. ``"?:number": [...]``.
#: A plain ``{{number}}`` placeholder then expands to an unnamed group.
SPECIAL_PREFIXES = ("?:", "?>", "?!", "?=", "?<=", "?<!", "?a:", "?i:", "?m:", "?s:", "?x:", "?l:")

_WHITESPACE = regex.compile(r" +|\\\s+")


@dataclass(frozen=True, slots=True)
class CompiledPattern:
    """A compiled runnable pattern plus the group metadata generated while building it.

    Attributes:
        type: The match type — the stem of the template file (or dict key) it came from.
        regex: The compiled regular expression.
        template: The source template string, before expansion.
        group_names: Generated group names, in order of creation (``day_0``, ``day_1``, …).
        group_keys: Map of generated group name to its template key (``day_1`` → ``day``).
        order: Map of generated group name to its position in ``group_names``.
    """

    type: str
    regex: regex.Pattern[str]
    template: str
    group_names: tuple[str, ...]
    group_keys: dict[str, str]
    order: dict[str, int]


def build_patterns(
    shared: TemplateAlternatives,
    runnable: TemplateAlternatives,
    *,
    flags: int = regex.V0,
    whitespace_noise: str | None = None,
) -> list[CompiledPattern]:
    """Expand and compile every runnable pattern.

    Args:
        shared: The merged placeholder namespace (all non-``$PATTERNS`` keys).
        runnable: The runnable patterns per template name (the ``$PATTERNS`` entries).
        flags: ``regex`` flags to compile with.
        whitespace_noise: If given, every literal whitespace in the final pattern is
            replaced by this pattern, wrapped in a non-capturing group.

    Returns:
        One :class:`CompiledPattern` per runnable pattern, in source order.

    Raises:
        CircularReferenceError: If template keys reference each other in a cycle.
        UnknownTemplateGroupError: If a placeholder references an undefined key.
        InvalidBackreferenceError: If a backreference points before the first expansion.
        PatternBuildError: If the fully expanded pattern fails to compile.
    """
    _check_cycles(shared)
    compiled: list[CompiledPattern] = []
    for type_name, templates in runnable.items():
        for template in templates:
            expansion = _Expansion(shared, template)
            expanded = expansion.expand(whitespace_noise)
            try:
                pattern = regex.compile(expanded, flags=flags)
            except regex.error as e:
                raise PatternBuildError(f"error compiling pattern of type {type_name!r}: {e}", template) from e
            compiled.append(
                CompiledPattern(
                    type=type_name,
                    regex=pattern,
                    template=template,
                    group_names=tuple(expansion.group_names),
                    group_keys=expansion.group_keys,
                    order={name: i for i, name in enumerate(expansion.group_names)},
                )
            )
    return compiled


class _Expansion:
    """Expands one template, tracking group numbering along the way."""

    def __init__(self, shared: TemplateAlternatives, template: str) -> None:
        self.shared = shared
        self.template = template
        self.counter: Counter[str] = Counter()
        self.group_names: list[str] = []
        self.group_keys: dict[str, str] = {}

    def expand(self, whitespace_noise: str | None) -> str:
        pattern = self.template
        while (placeholder := PLACEHOLDER.search(pattern)) is not None:
            pattern = self._expand_one(placeholder, pattern)
        if whitespace_noise is not None:
            # replace via callable: backslashes in the noise pattern (e.g. \s) must stay literal
            replacement = f"(?:{whitespace_noise})"
            pattern = _WHITESPACE.sub(lambda _: replacement, pattern)
        return pattern

    def _expand_one(self, placeholder: regex.Match[str], pattern: str) -> str:
        key = placeholder.group("key")
        special = placeholder.group("special")
        alternatives = self.shared.get(key)
        if alternatives is not None:
            if special is None:
                replacement = self._named_group(key, alternatives)
            elif special == "#":
                replacement = self._backreference(key, placeholder)
            else:
                # unnamed special group; the counter still advances, exactly like 0.3.x
                replacement = f"({special}{'|'.join(alternatives)})"
                self.counter[key] += 1
        else:
            replacement = self._prefixed_definition(key, special)
        return pattern[: placeholder.start()] + replacement + pattern[placeholder.end() :]

    def _named_group(self, key: str, alternatives: list[str]) -> str:
        name = f"{key}_{self.counter[key]}"
        self.group_names.append(name)
        self.group_keys[name] = key
        self.counter[key] += 1
        return f"(?P<{name}>{'|'.join(alternatives)})"

    def _backreference(self, key: str, placeholder: regex.Match[str]) -> str:
        distance = int(placeholder.group("index") or 1)
        target = self.counter[key] - distance
        if target < 0:
            raise InvalidBackreferenceError(
                f"{{{{{placeholder.group(1)}}}}} references non-existing group {key}_{target}"
                f" (template: {self.template!r})"
            )
        return f"(?P={key}_{target})"

    def _prefixed_definition(self, key: str, special: str | None) -> str:
        if special is not None:
            raise UnknownTemplateGroupError(f"`{special}{key}` does not exist (template: {self.template!r})")
        for prefix in SPECIAL_PREFIXES:
            alternatives = self.shared.get(f"{prefix}{key}")
            if alternatives is not None:
                return f"({prefix}{'|'.join(alternatives)})"
        raise UnknownTemplateGroupError(f"`{key}` does not exist (template: {self.template!r})")


def _dependency_graph(shared: TemplateAlternatives) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for key, alternatives in shared.items():
        references: list[str] = []
        for alternative in alternatives:
            for placeholder in PLACEHOLDER.finditer(alternative):
                if placeholder.group("special") == "#":
                    continue  # backreferences do not expand, so they cannot recurse
                target = _resolve_definition(shared, placeholder.group("key"), placeholder.group("special"))
                if target is not None and target not in references:
                    references.append(target)
        graph[key] = references
    return graph


def _resolve_definition(shared: TemplateAlternatives, key: str, special: str | None) -> str | None:
    if key in shared:
        return key
    if special is None:
        for prefix in SPECIAL_PREFIXES:
            if f"{prefix}{key}" in shared:
                return f"{prefix}{key}"
    return None  # undefined: expansion will raise UnknownTemplateGroupError with context


def _check_cycles(shared: TemplateAlternatives) -> None:
    """Reject cyclic template references up front, so expansion always terminates."""
    graph = _dependency_graph(shared)
    done: set[str] = set()
    for root in graph:
        if root in done:
            continue
        path: list[str] = [root]
        on_path: set[str] = {root}
        stack = [(root, iter(graph[root]))]
        while stack:
            node, references = stack[-1]
            descended = False
            for ref in references:
                if ref in on_path:
                    cycle = [*path[path.index(ref) :], ref]
                    raise CircularReferenceError(f"circular template reference: {' -> '.join(cycle)}")
                if ref not in done:
                    path.append(ref)
                    on_path.add(ref)
                    stack.append((ref, iter(graph[ref])))
                    descended = True
                    break
            if not descended:
                stack.pop()
                path.pop()
                on_path.discard(node)
                done.add(node)
