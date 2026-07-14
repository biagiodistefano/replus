# `engine.sub()` — group-targeted replacement — Design

**Date:** 2026-07-14
**Branch:** `revamp/v1.0.0` (folds into the v1.0.0 release / PR #14)
**Status:** Approved by owner (API shape chosen interactively; "sub" naming confirmed).

## Goal

Let users rewrite the text captured by specific template groups, in place, across all
matches — the driving use case is OCR-error correction (`1809900` → `l809900`) where
only matched spans may be touched and the rest of the document must pass through
byte-identical.

## API

```python
def sub(
    self,
    string: str,
    replacements: Mapping[str, str | Callable[[Group], str]],
    **parse_kwargs: Any,   # filters, exclude, pos, endpos, flags, partial, ...
) -> str
```

- Runs `parse()` (never overlapped; purged matches guarantee no cross-match edit
  collisions). Passing `overlapped=True` raises `ValueError`.
- For each match, every capture of each requested key — **including repetitions** —
  becomes one edit `(start, end, new_text)`.
- A `str` value is inserted **literally** (no regex replacement-escape processing).
- A callable receives the `Group` and returns the new text
  (`{"prefix": lambda g: g.value.replace("1", "l")}`).
- Edits are sorted and applied right-to-left so earlier offsets stay valid.
  Returns the new string.

## Errors

- Key not defined by **any** compiled pattern → `NoSuchGroupError` (typo guard).
  A valid key that simply didn't capture in a given match is skipped silently
  (normal alternation).
- Two edits whose spans overlap in the string (e.g. requesting both `date` and its
  child `day`) → **new** `OverlappingReplacementError(ReplusError)` — fail loud
  rather than guess which edit wins.

## Out of scope (YAGNI, recorded for later)

- `@n` single-repetition targeting — callables can branch on `g.rep_index`.
- Match-level rewrite templates (`"{{year}}-{{month}}-{{day}}"`) — the design
  alternative not chosen; `sub()` dispatching on replacement type keeps the door open.
- `count` limit.

## Implementation notes

- `engine.py`: ~40 lines; collect edits via `match.groups(key)` (already returns one
  `Group` per repetition, sorted); overlap check via `itertools.pairwise`; splice
  reversed.
- `exceptions.py`: add `OverlappingReplacementError`; export from `__init__`.
- Tests (`tests/test_sub.py`): literal / callable / repetitions / multi-key /
  unmatched-key skip / typo raises / overlap raises / `overlapped=True` raises /
  empty mapping no-op / filters passthrough / no-match passthrough. 100% branch
  gate stays.
- Docs: quickstart section with the OCR example, README bullet, CHANGELOG entry
  under 1.0.0 (unreleased), API page picks it up via autodoc.
