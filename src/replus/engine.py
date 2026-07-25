"""The Replus engine: loads templates, compiles them, and runs them over strings."""

from __future__ import annotations

import heapq
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import regex

from .builder import CompiledPattern, build_patterns
from .exceptions import NoSuchGroupError, OverlappingReplacementError, UnsupportedOperationError
from .loader import TemplateSource, load_templates
from .results import Group, Match, purge_overlaps

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator, Mapping


class Replus:
    """Builds and compiles regular expressions from templates, and matches them.

    Attributes:
        patterns_src: The merged placeholder namespace from every template source.
        patterns_all: The runnable patterns per template name (``$PATTERNS`` entries).
        patterns: The compiled patterns, as :class:`~replus.builder.CompiledPattern` objects.
        whitespace_noise: The whitespace-replacement pattern, if any.
        flags: The ``regex`` flags patterns were compiled with.
    """

    patterns_src: dict[str, Any]
    patterns_all: dict[str, list[str]]
    patterns: list[CompiledPattern]
    whitespace_noise: str | None
    flags: int
    _known_keys: set[str]

    def __init__(
        self,
        patterns_dir_or_dict: TemplateSource,
        whitespace_noise: str | None = None,
        flags: int = regex.V0,
    ) -> None:
        """Instantiate the engine.

        Args:
            patterns_dir_or_dict: Path to a directory of ``*.json`` template files,
                or a dict mapping template names to template dicts.
            whitespace_noise: If given, literal whitespace in patterns matches this
                pattern instead (e.g. ``r"[\\s\\-]+"``).
            flags: ``regex`` flags to compile the patterns with.
        """
        self.patterns_src, self.patterns_all = load_templates(patterns_dir_or_dict)
        self.whitespace_noise = whitespace_noise
        self.flags = flags
        self.patterns = build_patterns(
            self.patterns_src,
            self.patterns_all,
            flags=flags,
            whitespace_noise=whitespace_noise,
        )
        self._known_keys = {key for compiled in self.patterns for key in compiled.group_keys.values()}

    def finditer(
        self,
        string: str,
        *,
        filters: list[str] | None = None,
        exclude: list[str] | None = None,
        pos: int | None = None,
        endpos: int | None = None,
        overlapped: bool = False,
        partial: bool = False,
        concurrent: bool | None = None,
        timeout: float | None = None,
    ) -> Iterator[Match]:
        """Lazily yield every match of every (selected) pattern, in pattern order.

        Unlike :meth:`parse`, overlapping matches are *not* purged and results are
        not sorted by position.

        Args:
            string: The string to match against.
            filters: Only run patterns of these types (template names); all if None.
            exclude: Skip patterns of these types.
            pos: Start position of the matching.
            endpos: End position of the matching.
            overlapped: Allow overlapping matches of the same pattern.
            partial: Allow partial matches.
            concurrent: Release the GIL while matching.
            timeout: Timeout in seconds for the matching.

        Yields:
            One :class:`~replus.results.Match` per raw regex match.

        Note:
            Regex ``flags`` are a compile-time setting: pass them once to
            :class:`Replus` (``Replus(..., flags=regex.IGNORECASE)``). They cannot be
            supplied per call, because the patterns are already compiled.
        """
        for compiled in self._selected_patterns(filters, exclude):
            yield from self._match_stream(
                compiled,
                string,
                pos=pos,
                endpos=endpos,
                overlapped=overlapped,
                partial=partial,
                concurrent=concurrent,
                timeout=timeout,
            )

    def _selected_patterns(self, filters: list[str] | None, exclude: list[str] | None) -> Iterator[CompiledPattern]:
        """Yield the compiled patterns kept after applying ``filters``/``exclude``, in order."""
        filter_set = set(filters) if filters is not None else None
        exclude_set = set(exclude) if exclude is not None else None
        for compiled in self.patterns:
            if (filter_set and compiled.type not in filter_set) or (exclude_set and compiled.type in exclude_set):
                continue
            yield compiled

    def _match_stream(
        self,
        compiled: CompiledPattern,
        string: str,
        *,
        pos: int | None,
        endpos: int | None,
        overlapped: bool,
        partial: bool,
        concurrent: bool | None,
        timeout: float | None,
    ) -> Iterator[Match]:
        """Yield the :class:`Match` objects of one compiled pattern, in start order."""
        for match in compiled.regex.finditer(
            string,
            pos=pos,
            endpos=endpos,
            overlapped=overlapped,
            partial=partial,
            concurrent=concurrent,
            timeout=timeout,
        ):
            yield Match(compiled, match)

    def parse(
        self,
        string: str,
        *,
        filters: list[str] | None = None,
        exclude: list[str] | None = None,
        pos: int | None = None,
        endpos: int | None = None,
        overlapped: bool = False,
        partial: bool = False,
        concurrent: bool | None = None,
        timeout: float | None = None,
    ) -> list[Match]:
        """Return every match, sorted by position.

        Unless ``overlapped`` is True, overlapping matches are purged, keeping the
        longest match of each overlapping run.

        Args:
            string: The string to match against.
            filters: Only run patterns of these types (template names); all if None.
            exclude: Skip patterns of these types.
            pos: Start position of the matching.
            endpos: End position of the matching.
            overlapped: Allow overlapping matches (and skip overlap purging).
            partial: Allow partial matches.
            concurrent: Release the GIL while matching.
            timeout: Timeout in seconds for the matching.

        Returns:
            The list of :class:`~replus.results.Match` objects, sorted by start offset.

        Note:
            Regex ``flags`` are a compile-time setting; see :meth:`finditer`.
        """
        matches = list(
            self.finditer(
                string,
                filters=filters,
                exclude=exclude,
                pos=pos,
                endpos=endpos,
                overlapped=overlapped,
                partial=partial,
                concurrent=concurrent,
                timeout=timeout,
            )
        )
        if not overlapped:
            return purge_overlaps(matches)
        matches.sort(key=lambda m: m._start)
        return matches

    def search(
        self,
        string: str,
        *,
        filters: list[str] | None = None,
        exclude: list[str] | None = None,
        pos: int | None = None,
        endpos: int | None = None,
        overlapped: bool = False,
        partial: bool = False,
        concurrent: bool | None = None,
        timeout: float | None = None,
    ) -> Match | None:
        """Return the first match of :meth:`parse`, or None.

        Returns the same match as ``next(iter(parse(...)), None)`` but evaluated
        lazily: each pattern is scanned only as far as needed to settle the first
        (leftmost, overlap-purged) match, rather than materializing every match
        first. Because matching stops early, an error a pattern would raise only
        *past* that first match (e.g. a ``timeout`` on catastrophic backtracking
        later in the string) may not surface here as it would in :meth:`parse`.

        Args:
            string: The string to match against.
            filters: Only run patterns of these types (template names); all if None.
            exclude: Skip patterns of these types.
            pos: Start position of the matching.
            endpos: End position of the matching.
            overlapped: Allow overlapping matches (and skip overlap purging).
            partial: Allow partial matches.
            concurrent: Release the GIL while matching.
            timeout: Timeout in seconds for the matching.

        Returns:
            The first :class:`~replus.results.Match` by position, or None.

        Note:
            Regex ``flags`` are a compile-time setting; see :meth:`finditer`.
        """
        # One lazy Match stream per selected pattern, each already ordered by start.
        streams = [
            self._match_stream(
                compiled,
                string,
                pos=pos,
                endpos=endpos,
                overlapped=overlapped,
                partial=partial,
                concurrent=concurrent,
                timeout=timeout,
            )
            for compiled in self._selected_patterns(filters, exclude)
        ]
        # heapq.merge yields matches in start order, ties broken by pattern index —
        # exactly the stable ordering parse() feeds to purge_overlaps.
        merged = heapq.merge(*streams, key=lambda match: match._start)
        winner = next(merged, None)
        if winner is None or overlapped:
            # overlapped mode skips purging, exactly like parse(): the earliest-start
            # match (stable by pattern order) is already the answer.
            return winner
        # Replay purge_overlaps' keep-longest rule over the first overlapping run.
        # The first match that starts at/after the winner's end opens a new run and
        # can never displace element [0], so we can stop there.
        for match in merged:
            if match._start >= winner._end:
                break
            if match._end >= winner._end and match.length > winner.length:
                winner = match
        return winner

    def sub(
        self,
        string: str,
        replacements: Mapping[str, str | Callable[[Group], str]],
        **parse_kwargs: Any,
    ) -> str:
        """Replace the captures of the given template keys inside every match.

        Only matched spans are touched; the rest of the string passes through
        unchanged. Every repetition of a group is replaced. A string replacement
        is inserted literally (no escape processing); a callable receives the
        :class:`~replus.results.Group` and returns the new text::

            engine.sub(text, {"prefix": lambda g: g.value.replace("1", "l")})

        Args:
            string: The string to match against.
            replacements: Map of template key to replacement text, or to a
                callable computing it from the captured :class:`~replus.results.Group`.
            **parse_kwargs: Same keyword arguments as :meth:`parse`, except
                ``overlapped``, which is not supported.

        Returns:
            The string with all replacements applied.

        Raises:
            NoSuchGroupError: If a key is not defined by any compiled pattern.
            OverlappingReplacementError: If two requested keys capture
                overlapping spans (e.g. a group and one of its children).
            UnsupportedOperationError: If ``overlapped=True`` is passed.
        """
        if parse_kwargs.pop("overlapped", False):
            raise UnsupportedOperationError("sub() does not support overlapped matching: edits would be ambiguous")
        if unknown := set(replacements) - self._known_keys:
            raise NoSuchGroupError(f"no pattern defines the group(s): {', '.join(sorted(unknown))}")

        edits: list[tuple[int, int, str, str]] = []  # (start, end, key, new_text)
        for match in self.parse(string, **parse_kwargs):
            for key, replacement in replacements.items():
                for group in match.groups(key):
                    new_text = replacement if isinstance(replacement, str) else replacement(group)
                    edits.append((group.start(), group.end(), key, new_text))

        edits.sort(key=lambda edit: edit[:2])
        for (_, end_a, key_a, _), (start_b, _, key_b, _) in pairwise(edits):
            if start_b < end_a:
                raise OverlappingReplacementError(f"replacements for {key_a!r} and {key_b!r} target overlapping spans")
        chunks: list[str] = []
        last_index = 0
        for start, end, _, new_text in edits:
            chunks.append(string[last_index:start])
            chunks.append(new_text)
            last_index = end
        chunks.append(string[last_index:])
        return "".join(chunks)

    purge_overlaps = staticmethod(purge_overlaps)
