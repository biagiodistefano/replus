"""Exception hierarchy for replus.

Every error raised by replus inherits from :class:`ReplusError`, so callers can
catch a single type to handle any library failure.
"""


class ReplusError(Exception):
    """Base class for all replus errors."""


class DuplicatePatternKeyError(ReplusError):
    """A template key is defined by more than one source file or dict."""


class CircularReferenceError(ReplusError):
    """Template keys reference each other in a cycle and can never be expanded."""


class UnknownTemplateGroupError(ReplusError):
    """A ``{{placeholder}}`` references a key that is not defined in any template."""


class InvalidBackreferenceError(ReplusError):
    """A ``{{#key}}`` backreference points to a group that has not been expanded yet."""


class PatternBuildError(ReplusError):
    """A fully expanded template failed to compile into a regular expression."""


class NoSuchGroupError(ReplusError):
    """A queried group name does not exist in the match."""
