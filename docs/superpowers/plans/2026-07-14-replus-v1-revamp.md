# Replus v1.0.0 Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Note:** This run is executed inline, autonomously, by the agent that wrote the spec
> (`docs/superpowers/specs/2026-07-14-replus-v1-revamp-design.md`). The spec is the
> source of truth for semantics; this plan pins order, files, interfaces, and gates.

**Goal:** Rebuild replus as a modern uv/ruff/ty Python library at v1.0.0 with 100% test coverage, renovated CI, and revamped docs — preserving template syntax and match semantics.

**Architecture:** Split the monolithic `replus/__init__.py` into `exceptions` / `loader` / `builder` / `results` / `engine` under a `src/` layout; templates compile to frozen `CompiledPattern` objects carrying group metadata (fixes `Group.key` structurally); leftmost-rescan expansion preserved but iterative, with dependency-graph cycle detection up front.

**Tech Stack:** uv (`uv_build` backend), regex, ruff (lint+format), ty, pytest + coverage (fail_under=100), Sphinx + Furo + MyST on RTD, GitHub Actions with trusted publishing.

## Global Constraints

- `requires-python = ">=3.11"`; CI matrix 3.11, 3.12, 3.13, 3.14.
- Only runtime dependency: `regex`.
- Template syntax and observable group numbering/backreference semantics identical to 0.3.0 (spec §Compilation semantics). Sole allowed behavior change: `whitespace_noise` group becomes non-capturing.
- All exceptions inherit `ReplusError`; no `assert` for validation; no bare `Exception`.
- Coverage gate 100% (`fail_under = 100`); ruff check + format and ty must pass clean.
- Version lives only in `[project].version`; `__version__` via `importlib.metadata`.

---

### Task 1: Packaging skeleton (uv + PEP 621 + src layout)

**Files:**
- Create: `pyproject.toml` (rewrite), `uv.lock`, `src/replus/py.typed`
- Move: `replus/*.py` → `src/replus/` (git mv, then rewrite in Tasks 2–6)
- Delete: `poetry.lock`, `poetry.toml`, `CHANGES`

**Interfaces:** Produces `[dependency-groups] dev` (pytest, pytest-cov, ruff, ty) and `docs` (sphinx, furo, myst-parser, sphinx-copybutton); `[tool.ruff]`, `[tool.ty]`, `[tool.pytest.ini_options]`, `[tool.coverage.*]` config.

- [ ] Rewrite pyproject with PEP 621 metadata (name replus, version 1.0.0, uv_build backend), tool configs
- [ ] `git mv` sources into `src/`, add `py.typed`, delete poetry artifacts
- [ ] Run: `uv sync --all-groups` → lock resolves; `uv run python -c "import replus"` → imports
- [ ] Commit: `build: migrate to uv, PEP 621, src layout`

### Task 2: `exceptions.py`

**Files:** Rewrite `src/replus/exceptions.py`; Test: `tests/test_exceptions.py`

**Interfaces:** Produces `ReplusError`, `DuplicatePatternKeyError`, `CircularReferenceError`, `UnknownTemplateGroupError`, `InvalidBackreferenceError`, `PatternBuildError`, `NoSuchGroupError` — all `ReplusError` subclasses (spec §Exceptions table).

- [ ] Write hierarchy test (each class subclasses ReplusError), watch fail, implement, pass
- [ ] Commit: `feat: v1 exception hierarchy`

### Task 3: `loader.py`

**Files:** Create `src/replus/loader.py`; Test: `tests/test_loader.py`

**Interfaces:** Produces `load_templates(source: str | os.PathLike[str] | dict[str, dict[str, list[str]]]) -> tuple[dict[str, list[str]], dict[str, list[str]]]` returning `(shared_src, runnable_patterns)`; raises `DuplicatePatternKeyError` on cross-file duplicates, `TypeError` on bad source type.

- [ ] Tests: dir loading (reuse `tests/test_models/*.json`), dict loading, duplicate key raises, non-json files skipped, bad type raises
- [ ] Implement; run `uv run pytest tests/test_loader.py -v` → PASS
- [ ] Commit: `feat: template loader with DuplicatePatternKeyError`

### Task 4: `builder.py` (core)

**Files:** Create `src/replus/builder.py`; Test: `tests/test_builder.py`

**Interfaces:** Produces `CompiledPattern` frozen dataclass (`type: str`, `regex: regex.Pattern[str]`, `template: str`, `group_names: tuple[str, ...]`, `group_keys: dict[str, str]`, `order: dict[str, int]`) and `build_patterns(shared_src, runnable, *, flags, whitespace_noise) -> list[CompiledPattern]`. Raises `CircularReferenceError` / `UnknownTemplateGroupError` / `InvalidBackreferenceError` / `PatternBuildError`.

- [ ] Port `test_parser_regex` expectations (exact 0.3.0 compiled strings) as the semantics lock
- [ ] Tests: cycle direct + transitive (error message contains `a -> b -> a` path), unknown group, unknown special, backref too far, compile failure wraps in PatternBuildError with cause, whitespace_noise non-capturing, `group_keys` correct for key named e.g. `part_2`
- [ ] Implement: placeholder regex (module constant), dependency graph + DFS, iterative leftmost expansion splicing by span, per-template counter
- [ ] Run: `uv run pytest tests/test_builder.py -v` → PASS
- [ ] Commit: `feat: iterative builder with cycle detection and CompiledPattern`

### Task 5: `results.py`

**Files:** Create `src/replus/results.py`; Test: covered by ported `tests/test_replus.py` + additions in Task 7

**Interfaces:** Produces `AbstractMatch` (start/end/span/group/first/last/serialize/json), `Match(compiled: CompiledPattern, match: regex.Match[str])`, `Group(match, name, root: Match, rep_index=0)`; `Group.key` read from `root.compiled.group_keys[name]`; ordering via `compiled.order`. Public attrs preserved: `type`, `value`, `offset`, `length`, `pattern`, `partial`, `all_group_names`, reprs unchanged.

- [ ] Implement with `__slots__`; keep serialize shape byte-identical
- [ ] Commit: `feat: Match/Group results with slots and structural group keys`

### Task 6: `engine.py` + `__init__.py`

**Files:** Create `src/replus/engine.py`; rewrite `src/replus/__init__.py`

**Interfaces:** Produces `Replus(patterns_dir_or_dict, whitespace_noise=None, flags=regex.V0)` with `finditer(...) -> Iterator[Match]`, `parse(...) -> list[Match]`, `search(...) -> Match | None`, `purge_overlaps(matches)` static; `__init__` re-exports `Replus, Match, Group`, exceptions, `__version__`.

- [ ] Implement engine on loader+builder; parenthesized filter logic; parse built on finditer
- [ ] Run ported legacy suite: `uv run pytest tests/test_replus.py -v` → PASS
- [ ] Commit: `feat: engine with finditer; public API assembly`

### Task 7: Test suite to 100%

**Files:** Rework `tests/` (keep `test_models/` fixtures + `invalid_models/`), add `tests/test_results.py`, extend all

- [ ] Port every 0.3.0 test; add spec §Tests list (overlapped, purge edge cases, reps, serialize/json, start/end/span variants, NoSuchGroupError, finditer laziness, filters/exclude, version import)
- [ ] Run: `uv run pytest --cov=replus --cov-report=term-missing` → 100%, gate on
- [ ] Commit: `test: full suite at 100% coverage`

### Task 8: Quality gates

- [ ] `uv run ruff check .` + `uv run ruff format .` + `uv run ty check` → all clean (fix findings; targeted ignores only where ty pre-1.0 misfires)
- [ ] Commit: `style: ruff format + lint/type clean`

### Task 9: CI renovation

**Files:** Create `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `.github/dependabot.yml`, `.pre-commit-config.yaml`; Delete `.github/workflows/build.yml`, `.github/workflows/python-publish.yml`

- [ ] ci.yml: `quality` job (ruff check, format --check, ty) + `test` matrix 3.11–3.14 with setup-uv, coverage xml, Codecov upload on 3.13
- [ ] release.yml: on release published → uv build → pypa/gh-action-pypi-publish (OIDC, `id-token: write`, environment `pypi`)
- [ ] Commit: `ci: uv-based workflows, trusted publishing, dependabot`

### Task 10: Docs revamp

**Files:** Create `docs/conf.py`, `docs/index.md`, `docs/quickstart.md`, `docs/templates.md`, `docs/api.md`, `docs/changelog.md`, `CHANGELOG.md`; rewrite `.readthedocs.yaml`, `README.md`, `CLAUDE.md`; Delete `docs/source/`, `docs/make.bat`, `docs/Makefile`, `docs/requirements.txt`

- [ ] Sphinx: Furo + MyST + autodoc/napoleon + copybutton; exclude `superpowers/` from toctree scan
- [ ] Run: `uv run sphinx-build -W -b html docs docs/_build` → succeeds
- [ ] CHANGELOG.md: Keep-a-Changelog v1.0.0 entry with full breaking-change table
- [ ] Commit: `docs: furo/myst revamp, new README, CHANGELOG`

### Task 11: Final verification

- [ ] Fresh: `uv sync --all-groups && uv run pytest --cov=replus && uv run ruff check . && uv run ruff format --check . && uv run ty check && uv run sphinx-build -W -b html docs docs/_build && uv build`
- [ ] All green → final commit if needed; leave branch for morning review (no push unless asked)
