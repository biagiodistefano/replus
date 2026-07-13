# Changelog

All notable changes to this project are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-14

Full modernization. The template syntax, compiled patterns, group numbering, and
`serialize()`/`json()` output are **identical** to 0.3.0 — templates written for
0.3.0 work unchanged. The Python API has a few breaking changes listed below.

### Breaking changes

- Exceptions renamed; all now inherit `ReplusError` (was `ReplusException`):

  | 0.3.0 | 1.0.0 |
  |---|---|
  | `ReplusException` | `ReplusError` |
  | `UnknownTemplateGroup` | `UnknownTemplateGroupError` |
  | `NoSuchGroup` | `NoSuchGroupError` |
  | `PatternBuildException` | `PatternBuildError` |
  | `KeyError` (duplicate template key) | `DuplicatePatternKeyError` |
  | `AssertionError` (bad backreference) | `InvalidBackreferenceError` |
  | `RecursionError` (cyclic templates) | `CircularReferenceError` |
  | `RepeatedSpecialGroup` (never raised) | removed |

- Template errors now raise their specific exception instead of being wrapped in
  `PatternBuildException`: an undefined `{{placeholder}}` raises
  `UnknownTemplateGroupError`, a bad backreference raises
  `InvalidBackreferenceError`. `PatternBuildError` is reserved for patterns that
  fail to compile.
- `parse()` / `search()` / `finditer()` arguments after the string are keyword-only.
- `Match.all_group_names` is a tuple (was a list).
- `Replus.patterns` is a `list[CompiledPattern]` (was a list of tuples); the
  `group_counter` and `all_groups` engine attributes are gone — that metadata now
  lives on each `CompiledPattern`.
- `Match` is constructed from a `CompiledPattern` (only relevant if you built
  `Match` objects manually).
- `whitespace_noise` injects a non-capturing group `(?:...)` (was capturing).
- Requires Python >= 3.11.

### Added

- `Replus.finditer()`: lazy iterator over raw (unpurged, unsorted) matches.
- `CompiledPattern`: frozen dataclass exposing each pattern's regex, source
  template, and group metadata.
- Cycle detection: cyclic template references are rejected at load time with the
  full cycle path (0.3.0 crashed with `RecursionError`).
- Full type annotations and a `py.typed` marker.
- 100% test coverage (lines and branches), enforced in CI.

### Fixed

- `Group.key` no longer mangles user keys that end in `_<digit>` (e.g. `part_2`):
  group keys are recorded at build time instead of reverse-engineered from names.
- `match.groups(key)` no longer misses groups after an unnamed `{{?:key}}`
  expansion created a numbering gap.
- `whitespace_noise` patterns containing backslashes (e.g. `[\s\-]+`) no longer
  raise `bad escape`.
- Templates with thousands of placeholders no longer risk `RecursionError`:
  expansion is iterative.
- Template files load in deterministic (sorted) order.
- Loading templates from a dict no longer mutates the caller's dict.
- `coverage` and `pytest-cov` are no longer runtime dependencies.

### Changed

- Packaging: uv + PEP 621 + `src/` layout (was Poetry); single version source.
- Tooling: ruff (lint + format) and ty (type checking); CI tests Python 3.11-3.14;
  releases publish to PyPI via trusted publishing.
- Docs: rebuilt on Sphinx + Furo + MyST at [replus.readthedocs.io](https://replus.readthedocs.io).
- Internals split into focused modules (`loader`, `builder`, `results`, `engine`,
  `exceptions`); `Match`/`Group` use `__slots__`.

## [0.3.0] - 2023-09-04

Last release of the 0.x line, published to PyPI.

[1.0.0]: https://github.com/biagiodistefano/replus/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/biagiodistefano/replus/releases/tag/v0.3.0
