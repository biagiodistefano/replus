# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Replus is a PyPI library that wraps the `regex` package for template-based regex pattern management. Patterns are defined as JSON templates (or dicts) with `{{group}}` placeholders that get compiled into named-group regexes.

## Commands

Dependency management is via Poetry (virtualenv created in-project at `.venv`):

```bash
poetry install                                    # install deps
poetry run pytest                                 # run all tests
poetry run pytest tests/test_replus.py::test_match  # run a single test
poetry run pytest --cov=. tests/ --cov-report=xml # tests with coverage (what CI runs)
poetry run ruff check .                           # lint (line-length 120)
poetry run mypy replus                            # type check (disallow_untyped_defs is on)
```

Docs are Sphinx-based (`docs/`), built on Read the Docs: `make -C docs html`.

## Architecture

The entire library lives in two files:

- `replus/__init__.py` — everything: the `Replus` engine plus the `Match`/`Group` result classes (both extending `AbstractMatch`).
- `replus/exceptions.py` — exception hierarchy rooted at `ReplusException`.

### Template compilation flow

1. `Replus._load_models()` accepts either a directory of `*.json` files or a dict of dicts. All non-`$PATTERNS` keys across all files are merged into one shared namespace (`patterns_src`) — duplicate keys across files raise `KeyError`. Only entries under each file's `$PATTERNS` key are compiled as top-level runnable patterns; the file's stem becomes the match "type" used for `filters`/`exclude` in `parse()`.
2. `_build_patterns()` / `_build_pattern()` recursively expand `{{key}}` placeholders (matched by the `group_pattern` class attribute). Each expansion of a key becomes a named group `key_N`, where `N` is a per-template counter (`group_counter` resets per pattern) — this numbering is why the same logical group appears as `day_0`, `day_1`, etc. in the compiled regex.
3. Special placeholder prefixes: `{{?:key}}`/`{{?>key}}`/lookarounds/inline-flag prefixes produce unnamed groups; `{{#key}}` and `{{#key@n}}` produce backreferences to the n-th previous expansion of `key`. Keys may also be defined with the prefix in the template (e.g. `"?:number"`) and referenced without it.
4. `all_groups` maps each pattern template string to its ordered list of generated group names; `Match`/`Group.groups()` rely on this ordering (a `Group`'s children are the groups that come after it in that list and fall within its span).

### Runtime results

`parse()` runs `regex.finditer` for every compiled pattern and wraps hits in `Match` objects. Unless `overlapped=True`, results go through `purge_overlaps()`, which keeps the longest of overlapping matches. `Group.group("name")` navigates nested groups by key (without the `_N` suffix); repeated captures are exposed via `rep_index`/`reps()`.

### Tests

`tests/test_models/` contains equivalent template definitions both as `.json` files and as `.py` dicts — the dict versions are the JSON ones translated to Python, and tests exercise both loading paths. `tests/invalid_models/` holds deliberately broken templates for error-path tests. Remember that backslashes in JSON templates must be double-escaped (`\\d`).

## Gotchas

- The version string is duplicated in `pyproject.toml`, `replus/__init__.py` (`__version__`), and the README title — keep them in sync when bumping.
