"""replus — template-based regular expression management, powered by the regex library.

Define regex fragments as named template keys, compose them with ``{{placeholders}}``,
and query matches through nested, named :class:`Match` / :class:`Group` objects.

:copyright: (c) 2022 Biagio Distefano.
:license: MIT
"""

from importlib.metadata import version as _version

from .builder import CompiledPattern
from .engine import Replus
from .exceptions import (
    CircularReferenceError,
    DuplicatePatternKeyError,
    InvalidBackreferenceError,
    NoSuchGroupError,
    PatternBuildError,
    ReplusError,
    UnknownTemplateGroupError,
)
from .results import AbstractMatch, Group, Match, purge_overlaps

__version__ = _version("replus")

__all__ = [
    "AbstractMatch",
    "CircularReferenceError",
    "CompiledPattern",
    "DuplicatePatternKeyError",
    "Group",
    "InvalidBackreferenceError",
    "Match",
    "NoSuchGroupError",
    "PatternBuildError",
    "Replus",
    "ReplusError",
    "UnknownTemplateGroupError",
    "__version__",
    "purge_overlaps",
]
