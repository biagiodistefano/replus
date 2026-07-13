"""Match and Group result objects — structured, queryable views over ``regex`` matches."""

from __future__ import annotations

import abc
import json
from collections import defaultdict
from typing import TYPE_CHECKING, Any, TypeVar

import regex

from .exceptions import NoSuchGroupError

if TYPE_CHECKING:
    from .builder import CompiledPattern

_M = TypeVar("_M", bound="AbstractMatch")


def purge_overlaps(matches: list[_M]) -> list[_M]:
    """Drop overlapping matches, keeping the longest one of each overlapping run.

    Args:
        matches: Match or Group objects; sorted in place by start offset.

    Returns:
        The overlap-free list, sorted by start offset.
    """
    matches.sort(key=lambda m: m._start)  # noqa: SLF001
    if len(matches) <= 1:
        return matches
    purged = [matches[0]]
    for match in matches[1:]:
        if match._start >= purged[-1]._end:
            purged.append(match)
        elif match._end >= purged[-1]._end and match.length > purged[-1].length:
            purged.pop()
            purged.append(match)
    return purged


class AbstractMatch(abc.ABC):
    """Shared behavior of :class:`Match` and :class:`Group`."""

    __slots__ = ()

    rep_index: int = 0  # Group carries a real repetition index; Match is always 0

    # populated by subclasses
    value: str
    offset: dict[str, int]
    length: int
    _start: int
    _end: int
    _span: tuple[int, int]

    @abc.abstractmethod
    def groups(self, group_query: str | None = None, root: bool = False) -> list[Group]:
        """Return the nested groups, optionally only those of key ``group_query``."""

    @abc.abstractmethod
    def _own_start(self, rep_index: int) -> int: ...

    @abc.abstractmethod
    def _own_end(self, rep_index: int) -> int: ...

    @abc.abstractmethod
    def _serialize_head(self) -> dict[str, Any]: ...

    def start(self, group_name: str | None = None, rep_index: int | None = None) -> int:
        """Return the start offset of self, or of the group named ``group_name``.

        Args:
            group_name: Name of a nested group to locate instead of self.
            rep_index: Repetition index; defaults to this object's own.

        Raises:
            NoSuchGroupError: If ``group_name`` does not exist in this match.
        """
        if rep_index is None:
            rep_index = self.rep_index
        if group_name is not None:
            if (group := self.group(group_name)) is not None:
                return group.start(rep_index=rep_index)
            raise NoSuchGroupError(group_name)
        return self._own_start(rep_index)

    def end(self, group_name: str | None = None, rep_index: int | None = None) -> int:
        """Return the end offset of self, or of the group named ``group_name``.

        Args:
            group_name: Name of a nested group to locate instead of self.
            rep_index: Repetition index; defaults to this object's own.

        Raises:
            NoSuchGroupError: If ``group_name`` does not exist in this match.
        """
        if rep_index is None:
            rep_index = self.rep_index
        if group_name is not None:
            if (group := self.group(group_name)) is not None:
                return group.end(rep_index=rep_index)
            raise NoSuchGroupError(group_name)
        return self._own_end(rep_index)

    def span(self, group_name: str | None = None, rep_index: int | None = None) -> tuple[int, int]:
        """Return the ``(start, end)`` span of self, or of the group named ``group_name``.

        Args:
            group_name: Name of a nested group to locate instead of self.
            rep_index: Repetition index; defaults to this object's own.

        Raises:
            NoSuchGroupError: If ``group_name`` does not exist in this match.
        """
        if rep_index is None:
            rep_index = self.rep_index
        if group_name is not None:
            if (group := self.group(group_name)) is not None:
                return group.span(rep_index=rep_index)
            raise NoSuchGroupError(group_name)
        return self._own_start(rep_index), self._own_end(rep_index)

    def group(self, group_name: str) -> Group | None:
        """Return the first nested group whose key is ``group_name``, or None."""
        return next(iter(self.groups(group_name)), None)

    def first(self) -> Group | None:
        """Return the first nested group, or None."""
        return next(iter(self.groups()), None)

    def last(self) -> Group | None:
        """Return the last nested group, or None."""
        groups = self.groups()
        return groups[-1] if groups else None

    def serialize(self) -> dict[str, Any]:
        """Return a plain-dict representation of this object and its nested groups."""
        serialized = self._serialize_head()
        serialized["offset"] = self.offset
        serialized["value"] = self.value
        groups: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for group in self.groups(root=True):
            groups[group.key].append(group.serialize())
        serialized["groups"] = dict(groups)
        return serialized

    def json(self, *args: Any, **kwargs: Any) -> str:
        """Return :meth:`serialize` as a JSON string; arguments go to :func:`json.dumps`."""
        return json.dumps(self.serialize(), *args, **kwargs)


class Match(AbstractMatch):
    """A single hit of a runnable pattern.

    Attributes:
        type: The match type — the stem of the template file the pattern came from.
        compiled: The :class:`~replus.builder.CompiledPattern` that produced this match.
        match: The underlying :class:`regex.Match`.
        partial: Whether this is a partial match.
        value: The matched substring.
        offset: ``{"start": int, "end": int}`` of the match.
        pattern: The compiled pattern string.
        length: Number of matched characters.
        all_group_names: Every group name the pattern can produce, in creation order.
    """

    __slots__ = (
        "_end",
        "_span",
        "_start",
        "all_group_names",
        "compiled",
        "length",
        "match",
        "offset",
        "partial",
        "pattern",
        "type",
        "value",
    )

    def __init__(self, compiled: CompiledPattern, match: regex.Match[str]) -> None:
        self.compiled = compiled
        self.type = compiled.type
        self.match = match
        self.partial = match.partial
        self.value: str = match.group()
        self._start: int = match.start()
        self._end: int = match.end()
        self._span: tuple[int, int] = match.span()
        self.offset = {"start": self._start, "end": self._end}
        self.pattern: str = compiled.regex.pattern
        self.length = self._end - self._start
        self.all_group_names = compiled.group_names

    def groups(self, group_query: str | None = None, root: bool = False) -> list[Group]:
        """Return this match's groups, sorted by start offset.

        Args:
            group_query: Only return groups of this key (e.g. every ``day_N``).
            root: If True, drop groups contained in other returned groups.
        """
        names = self._names_for(group_query)
        groups = []
        for name in names:
            if self.match.group(name) is None:
                continue
            for rep_index, (start, end) in enumerate(self.match.spans(name)):
                if self._start <= start and end <= self._end:
                    groups.append(Group(self.match, name, self, rep_index=rep_index))
        groups.sort(key=lambda g: g._start)  # noqa: SLF001
        if root:
            return purge_overlaps(groups)
        return groups

    def _names_for(self, group_query: str | None) -> tuple[str, ...]:
        if group_query is None:
            return self.all_group_names
        return tuple(name for name in self.all_group_names if self.compiled.group_keys[name] == group_query)

    def _own_start(self, rep_index: int) -> int:
        return self.match.start()

    def _own_end(self, rep_index: int) -> int:
        return self.match.end()

    def _serialize_head(self) -> dict[str, Any]:
        return {"type": self.type}

    def __repr__(self) -> str:
        return f"<[Match {self.type}] span{self._span}: {self.value}>"


class Group(AbstractMatch):
    """A named group captured inside a :class:`Match`.

    Attributes:
        root: The :class:`Match` this group belongs to.
        match: The underlying :class:`regex.Match`.
        name: The generated group name, including its counter (e.g. ``day_1``).
        key: The template key of the group (e.g. ``day``).
        value: The captured substring for this repetition.
        rep_index: Which repetition of the group this object represents.
        offset: ``{"start": int, "end": int}`` of the capture.
        length: Number of captured characters.
    """

    __slots__ = (
        "_end",
        "_span",
        "_start",
        "key",
        "length",
        "match",
        "name",
        "offset",
        "rep_index",
        "root",
        "value",
    )

    def __init__(self, match: regex.Match[str], group_name: str, root: Match, rep_index: int = 0) -> None:
        self.root = root
        self.match = match
        self.name = group_name
        self.key: str = root.compiled.group_keys[group_name]
        self.value: str = match.captures(group_name)[rep_index]
        self.rep_index: int = rep_index
        self._start: int = match.starts(group_name)[rep_index]
        self._end: int = match.ends(group_name)[rep_index]
        self._span: tuple[int, int] = (self._start, self._end)
        self.offset = {"start": self._start, "end": self._end}
        self.length = self._end - self._start

    def groups(self, group_query: str | None = None, root: bool = False) -> list[Group]:
        """Return the groups nested inside this one, sorted by start offset.

        Args:
            group_query: Only return groups of this key (e.g. every ``day_N``).
            root: If True, drop groups contained in other returned groups.
        """
        order = self.root.compiled.order
        my_position = order[self.name]
        groups = []
        for name in self.root._names_for(group_query):  # noqa: SLF001
            # children only: groups created after this one, captured within its span
            if order[name] <= my_position or self.match.group(name) is None:
                continue
            for rep_index, (start, end) in enumerate(self.match.spans(name)):
                if self._start <= start and end <= self._end:
                    groups.append(Group(self.match, name, self.root, rep_index=rep_index))
        groups.sort(key=lambda g: g._start)  # noqa: SLF001
        if root:
            return purge_overlaps(groups)
        return groups

    def reps(self) -> list[Group]:
        """Return every repetition of this group as its own :class:`Group`, or ``[]`` if single."""
        repetitions = len(self.match.starts(self.name))
        if repetitions > 1:
            return [Group(self.match, self.name, self.root, rep_index=i) for i in range(repetitions)]
        return []

    def _own_start(self, rep_index: int) -> int:
        return self.match.starts(self.name)[rep_index]

    def _own_end(self, rep_index: int) -> int:
        return self.match.ends(self.name)[rep_index]

    def _serialize_head(self) -> dict[str, Any]:
        return {"key": self.key, "name": self.name}

    def __repr__(self) -> str:
        return f"<Group {self.name} span{self._span} @{self.rep_index}: '{self.value}'>"
