# Replus v1.0.0 Revamp — Design

**Date:** 2026-07-14
**Branch:** `revamp/v1.0.0`
**Status:** Executed autonomously overnight; owner reviews in the morning.

## Goal

Bring replus from a 2023-era Poetry project to a modern 2026 Python library at v1.0.0,
keeping the core idea intact: JSON/dict regex pattern templates with `{{group}}`
placeholders, compiled into named-group `regex` patterns, queried through nested
`Match`/`Group` objects.

Non-goals: changing the template syntax, changing match/overlap semantics, adding new
matching features. Template files written for 0.3.0 must work unchanged on 1.0.0.

## Tooling decisions

| Area | 0.3.0 | 1.0.0 | Why |
|---|---|---|---|
| Package manager | Poetry 1.x | uv (`uv_build` backend) | Requested; single fast tool for lock, venv, build, publish |
| Layout | flat `replus/` | `src/replus/` | Import isolation in tests; modern default |
| Metadata | `[tool.poetry]` | PEP 621 `[project]` | Standard |
| Lint/format | ruff 0.0.287 (lint only) | current ruff, lint + format, broad ruleset | One tool, no black needed |
| Type checker | mypy | ty | Requested; Astral stack consistency. `py.typed` shipped |
| Tests | pytest + pytest-cov | same, `fail_under = 100` | Requested 100% coverage, enforced not aspirational |
| Python | ^3.11 | >=3.11, tested 3.11–3.14 | Keep floor, prove currency |
| Version source | 3 places | `[project].version` only; `__version__` via `importlib.metadata` | Kills the triple-bump gotcha |
| Changelog | `CHANGES` (stale) | `CHANGELOG.md`, Keep-a-Changelog format | Standard |

Considered and rejected: mkdocs-material (RTD + autodoc story is smoother with Sphinx;
we keep Sphinx and modernize the theme), keeping mypy alongside ty (two checkers, two
configs, no added value), dropping the dict-loading path (it is genuinely useful and
tested), deprecation aliases for old exception names (v1.0.0 is the clean-break moment;
the migration is documented instead).

## Architecture

Split the 720-line `__init__.py` into focused modules under `src/replus/`:

- `exceptions.py` — hierarchy rooted at `ReplusError` (see below).
- `loader.py` — `load_templates(source)`: accepts a directory path or dict-of-dicts,
  merges non-`$PATTERNS` keys into the shared namespace, extracts runnable patterns.
  Raises `DuplicatePatternKeyError` (was a bare `KeyError`).
- `builder.py` — template compilation. Owns the placeholder grammar, dependency-graph
  cycle detection, and expansion. Produces `CompiledPattern` objects.
- `results.py` — `AbstractMatch`, `Match`, `Group` (all with `__slots__`).
- `engine.py` — `Replus`: wires loader + builder, exposes `parse` / `search` /
  `finditer` / `purge_overlaps`.
- `__init__.py` — public re-exports only. Public API: `Replus`, `Match`, `Group`,
  all exceptions, `__version__`.

New internal type — `CompiledPattern` (frozen dataclass): `type` (template file stem),
`regex` (compiled), `template` (source string), `group_names` (ordered), `group_keys`
(name → key map), `order` (name → index map). This replaces the old parallel structures
(`patterns` tuple list + `all_groups` dict keyed by template *string*) and fixes the
`Group.key` bug structurally: keys are recorded at build time, never reverse-engineered
by stripping `_\d+` (which mangled user keys like `address_2`).

## Compilation semantics (preserved exactly)

The 0.3.0 builder expands the *leftmost* placeholder, then rescans from the start.
Group numbering (`key_0`, `key_1`, …) and backreference resolution (`{{#key}}`,
`{{#key@n}}`) depend on this order. The v1 builder keeps identical observable output
but iteratively (`while m := PLACEHOLDER_RE.search(...)`) instead of recursively — no
`RecursionError` on deep templates — and splices by match span instead of
`str.replace(..., 1)`.

Termination is guaranteed up front: before building, a dependency graph over template
keys (placeholder references, excluding `#` backreferences, resolving special-prefix
definitions like `"?:number"`) is checked by DFS; a cycle raises
`CircularReferenceError` naming the cycle path (`a -> b -> a`). 0.3.0 died with
`RecursionError` here.

One deliberate behavior change: `whitespace_noise` now injects a **non-capturing**
group `(?:...)` instead of a capturing one. Nothing in the API exposes numbered groups,
so this is invisible except to someone poking at `.match` directly. Documented in the
changelog.

## Exceptions

All inherit `ReplusError(Exception)`; consistent `*Error` naming; every internal
`assert` and bare `raise Exception` replaced:

| v1 | Replaces |
|---|---|
| `DuplicatePatternKeyError` | bare `KeyError` in `_load_models` |
| `CircularReferenceError` | `RecursionError` crash (new detection) |
| `UnknownTemplateGroupError` | `UnknownTemplateGroup` + one bare `Exception` |
| `InvalidBackreferenceError` | `assert` (which vanished under `python -O`) |
| `PatternBuildError` | `PatternBuildException`; still wraps unexpected compile failures, now with `raise ... from e` |
| `NoSuchGroupError` | `NoSuchGroup` |

`RepeatedSpecialGroup` (imported, never raised) is deleted.

## Runtime API

Kept as-is: `Replus(patterns_dir_or_dict, whitespace_noise=None, flags=regex.V0)`,
`parse()` (returns `list[Match]`, overlap-purged unless `overlapped=True`), `search()`,
all `Match`/`Group` navigation (`group`, `groups`, `first`, `last`, `reps`,
`start/end/span` with `group_name`/`rep_index`), `serialize()`/`json()` shapes, reprs,
`filters`/`exclude` and all `regex.finditer` passthrough kwargs.

Added: `finditer()` — lazy generator over raw (un-purged) matches; `parse()` is now
built on it. Modern typing throughout: PEP 604 unions, builtin generics, precise return
types (`parse() -> list[Match]`, not the old wrong `Union[List[Match], List[Group]]`).

Small fixes while there: the operator-precedence-dependent filter condition gets
explicit parentheses; `Group.groups()` uses the precomputed `order` map instead of
O(n) `list.index` per comparison; docstrings move from reST field style to Google
style (rendered via napoleon).

## Tests — 100% enforced

- Port all existing tests (both loading paths: JSON dir and dict).
- New: cycle detection (direct + transitive), duplicate keys, invalid source type,
  unknown group, unknown special group, invalid backreference, `PatternBuildError`
  wrapping, `Group.key` correctness for keys ending in `_\d`-like suffixes,
  `whitespace_noise`, `overlapped=True`, `purge_overlaps` edge cases (empty, single,
  contained, longer-wins), `serialize`/`json`, `reps`, `first`/`last`,
  `start`/`end`/`span` with names and `rep_index`, `finditer` laziness, filters/exclude.
- `[tool.coverage.report] fail_under = 100` so CI fails on any regression.

## CI / release

- `ci.yml`: two jobs — `quality` (ruff check, ruff format --check, ty check) and `test`
  (matrix 3.11/3.12/3.13/3.14 via `astral-sh/setup-uv`, pytest with coverage, Codecov
  upload from 3.13 only). Runs on push to master + PRs.
- `release.yml`: on published GitHub release — `uv build` then PyPI **trusted
  publishing** (OIDC, `pypa/gh-action-pypi-publish`); no API token secrets. Requires
  one-time PyPI-side trusted-publisher setup (noted in morning summary).
- `dependabot.yml`: weekly, `github-actions` + `uv` ecosystems.
- Old `build.yml` / `python-publish.yml` removed.
- `.pre-commit-config.yaml` with ruff hooks (optional to use, cheap to have).

## Docs

Sphinx kept for RTD, but: Furo theme, MyST (Markdown pages), napoleon for Google
docstrings, sphinx-copybutton. Flattened to `docs/` (no `source/`): `index.md`,
`quickstart.md`, `templates.md` (full template-syntax reference — the best content
currently buried in the README), `api.md` (autodoc), `changelog.md` (includes
CHANGELOG.md). `.readthedocs.yaml` rebuilt on `build.commands` with uv. README slimmed
to pitch + quickstart + pointer to docs, plus a development section (uv commands).

## Risks / open questions for morning review

1. **ty is pre-1.0** — pinned in the dev group; if it misbehaves on some construct we
   add a targeted ignore comment rather than contorting the code.
2. **RTD build with uv** can't be verified locally; the Sphinx build itself is verified
   locally via `uv run sphinx-build`. If RTD chokes, fallback is a pip-based
   `.readthedocs.yaml` (5-minute change).
3. **Exception renames are a hard break** — mapped in CHANGELOG; aliases deliberately
   omitted. Cheap to add if you disagree.
4. **Trusted publishing** needs you to add the GitHub repo as a trusted publisher on
   PyPI before the first release.
