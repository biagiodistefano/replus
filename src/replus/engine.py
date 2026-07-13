"""The Replus engine: loads templates, compiles them, and runs them over strings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import regex

from .builder import CompiledPattern, build_patterns
from .loader import TemplateSource, load_templates
from .results import Match, purge_overlaps

if TYPE_CHECKING:
    from collections.abc import Iterator


class Replus:
    """Builds and compiles regular expressions from templates, and matches them.

    Attributes:
        patterns_src: The merged placeholder namespace from every template source.
        patterns_all: The runnable patterns per template name (``$PATTERNS`` entries).
        patterns: The compiled patterns, as :class:`~replus.builder.CompiledPattern` objects.
        whitespace_noise: The whitespace-replacement pattern, if any.
        flags: The ``regex`` flags patterns were compiled with.
    """

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
        self.patterns: list[CompiledPattern] = build_patterns(
            self.patterns_src,
            self.patterns_all,
            flags=flags,
            whitespace_noise=whitespace_noise,
        )

    def finditer(
        self,
        string: str,
        *,
        filters: list[str] | None = None,
        exclude: list[str] | None = None,
        pos: int | None = None,
        endpos: int | None = None,
        flags: int = 0,
        overlapped: bool = False,
        partial: bool = False,
        concurrent: bool | None = None,
        timeout: float | None = None,
        ignore_unused: bool = False,
        **kwargs: Any,
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
            flags: Extra flags forwarded to :func:`regex.finditer`.
            overlapped: Allow overlapping matches of the same pattern.
            partial: Allow partial matches.
            concurrent: Release the GIL while matching.
            timeout: Timeout in seconds for the matching.
            ignore_unused: Ignore unused positional or keyword arguments in ``kwargs``.
            **kwargs: Any further arguments accepted by :func:`regex.finditer`.

        Yields:
            One :class:`~replus.results.Match` per raw regex match.
        """
        for compiled in self.patterns:
            if (filters and compiled.type not in filters) or (exclude and compiled.type in exclude):
                continue
            for match in regex.finditer(
                pattern=compiled.regex,
                string=string,
                flags=flags,
                pos=pos,
                endpos=endpos,
                overlapped=overlapped,
                partial=partial,
                concurrent=concurrent,
                timeout=timeout,
                ignore_unused=ignore_unused,
                **kwargs,
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
        flags: int = 0,
        overlapped: bool = False,
        partial: bool = False,
        concurrent: bool | None = None,
        timeout: float | None = None,
        ignore_unused: bool = False,
        **kwargs: Any,
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
            flags: Extra flags forwarded to :func:`regex.finditer`.
            overlapped: Allow overlapping matches (and skip overlap purging).
            partial: Allow partial matches.
            concurrent: Release the GIL while matching.
            timeout: Timeout in seconds for the matching.
            ignore_unused: Ignore unused positional or keyword arguments in ``kwargs``.
            **kwargs: Any further arguments accepted by :func:`regex.finditer`.

        Returns:
            The list of :class:`~replus.results.Match` objects, sorted by start offset.
        """
        matches = list(
            self.finditer(
                string,
                filters=filters,
                exclude=exclude,
                pos=pos,
                endpos=endpos,
                flags=flags,
                overlapped=overlapped,
                partial=partial,
                concurrent=concurrent,
                timeout=timeout,
                ignore_unused=ignore_unused,
                **kwargs,
            )
        )
        if not overlapped:
            return purge_overlaps(matches)
        matches.sort(key=lambda m: m._start)
        return matches

    def search(self, string: str, **kwargs: Any) -> Match | None:
        """Return the first match of :meth:`parse`, or None.

        Args:
            string: The string to match against.
            **kwargs: Same keyword arguments as :meth:`parse`.
        """
        return next(iter(self.parse(string, **kwargs)), None)

    purge_overlaps = staticmethod(purge_overlaps)
