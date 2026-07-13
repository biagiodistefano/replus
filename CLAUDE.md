# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Replus is a PyPI library (v1.0.0) that wraps the `regex` package for template-based regex
pattern management. Patterns are defined as JSON templates (or dicts) with `{{group}}`
placeholders that compile into named-group regexes, queried via nested `Match`/`Group` objects.

## Commands

Everything runs through uv (src layout, PEP 621, `uv_build` backend):

```bash
uv sync --all-groups                              # install all dependency groups
uv run pytest                                     # run all tests
uv run pytest tests/test_replus.py::test_match    # run a single test
uv run pytest --cov=replus                        # coverage — gate is 100% lines AND branches (fail_under=100)
uv run ruff check .                               # lint (line-length 120, broad ruleset)
uv run ruff format .                              # format
uv run ty check                                   # type check (types-regex stubs in dev group)
uv run sphinx-build -W -b html docs docs/_build   # build docs (Furo + MyST)
```

CI (`.github/workflows/ci.yml`) runs exactly these gates on 3.11–3.14. Releases publish to
PyPI via trusted publishing on GitHub release (`release.yml`). Version lives ONLY in
`pyproject.toml`; `__version__` reads package metadata.

## Architecture

`src/replus/` — the data flows loader → builder → engine → results:

- `loader.py` — merges all non-`$PATTERNS` keys from every source (JSON file or dict) into
  ONE shared namespace; duplicates raise `DuplicatePatternKeyError`. `$PATTERNS` entries
  become runnable patterns; the file stem/dict key becomes the match "type" used by
  `filters`/`exclude`.
- `builder.py` — expands `{{placeholders}}` into named groups `key_N`. Expansion is
  **leftmost-first with rescan** (iterative, not recursive): group numbering and
  `{{#key}}` backreference resolution depend on this exact order — do not "optimize" it.
  Cycles are rejected up front via a dependency-graph DFS (`CircularReferenceError`).
  Produces frozen `CompiledPattern` objects carrying group metadata (`group_names`,
  `group_keys` name→key, `order`).
- `results.py` — `Match`/`Group` (both `__slots__`). `Group.key` comes from the build-time
  `group_keys` map (never derived from the name). `purge_overlaps` keeps the longest of
  each overlapping run. `Group.groups()` returns only groups *after* it in creation order
  whose spans fall inside its own span.
- `engine.py` — `Replus`: `finditer` (lazy, raw) → `parse` (sorted, overlap-purged) →
  `search` (first or None). Kwargs after the string are keyword-only.
- All errors inherit `ReplusError` (`exceptions.py`); never use `assert` for validation.

## Behavioral contracts (locked by tests)

- `tests/test_replus.py` is the ported 0.3.0 suite: exact compiled pattern strings and
  byte-exact `serialize()`/`json()` output. Breaking these means breaking user templates.
- The counter quirk is intentional: `{{?:key}}` advances `key`'s counter without creating
  a named group (`{{abg}} {{?:abg}} {{abg}}` → `abg_0`, `abg_2`).
- `tests/test_models/` fixtures exist as both `.json` and `.py` dicts to exercise both
  loading paths; keep them in sync. `tests/invalid_models/` holds broken templates.
- JSON templates need double-escaped backslashes (`\\d`).

## Gotchas

- The 100% coverage gate includes **branch** coverage: an unreachable defensive branch
  will fail CI. Write code without dead branches rather than adding pragmas.
- In tests, use `found()` from `conftest.py` to narrow `Match | None` / `Group | None` —
  ty checks tests too.
- `docs/superpowers/` holds design specs/plans, excluded from the Sphinx build via
  `exclude_patterns` in `docs/conf.py`.
