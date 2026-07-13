# Quickstart

## Installation

```bash
uv add replus
# or
pip install replus
```

Requires Python 3.11+. The only runtime dependency is
[regex](https://pypi.org/project/regex/).

## Define pattern templates

The engine loads **pattern templates** from `*.json` files in a directory (or from a
plain dict of dicts). Every key defines a named fragment; fragments compose through
`{{placeholders}}`. Only the patterns under the special `$PATTERNS` key are matched
against at runtime.

`patterns/date.json`:

```json
{
  "day": ["3[01]", "[12][0-9]", "0?[1-9]"],
  "month": ["0?[1-9]", "1[012]"],
  "year": ["\\d{4}"],
  "date": ["{{day}}/{{month}}/{{year}}", "{{year}}-{{month}}-{{day}}"],
  "$PATTERNS": ["{{date}}"]
}
```

```{note}
Backslashes must be double-escaped in JSON: write `\\d` to get `\d`.
```

This compiles to a single pattern with automatically numbered named groups:

```text
(?P<date_0>(?P<day_0>3[01]|[12][0-9]|0?[1-9])/(?P<month_0>0?[1-9]|1[012])/(?P<year_0>\d{4})|(?P<year_1>\d{4})-(?P<month_1>0?[1-9]|1[012])-(?P<day_1>3[01]|[12][0-9]|0?[1-9]))
```

## Match and query

```python
from replus import Replus

engine = Replus("patterns")  # or a dict of dicts

for match in engine.parse("Look at this date: 1970-12-25"):
    print(repr(match))
    # <[Match date] span(19, 29): 1970-12-25>

    date = match.group("date")
    print(repr(date))
    # <Group date_0 span(19, 29) @0: '1970-12-25'>

    print(repr(date.group("day")))
    # <Group day_1 span(27, 29) @0: '25'>
    print(repr(date.group("month")))
    # <Group month_1 span(24, 26) @0: '12'>
    print(repr(date.group("year")))
    # <Group year_1 span(19, 23) @0: '1970'>
```

You query groups by their **template key** (`day`), not the generated group name
(`day_1`) — the engine resolves which alternative actually matched.

Every match serializes to a plain dict or JSON:

```python
match.serialize()   # nested dict of values, offsets, and groups
match.json(indent=2)
```

## Filtering by type

The stem of each template file (or the dict key) becomes the match **type**, so you
can select which pattern families run:

```python
engine.parse(text, filters=["date"])    # only date patterns
engine.parse(text, exclude=["cities"])  # everything but cities
```

## The three matching methods

| Method | Returns | Overlaps |
|---|---|---|
| `parse(text)` | `list[Match]`, sorted | purged (longest wins) unless `overlapped=True` |
| `search(text)` | first `Match` or `None` | same as `parse` |
| `finditer(text)` | lazy `Iterator[Match]` | raw, unpurged |

All three accept the same keyword arguments and forward the extras
(`pos`, `endpos`, `partial`, `timeout`, …) to
[`regex.finditer`](https://github.com/mrabarnett/mrab-regex/blob/hg/docs/Features.md).

Continue with the [template syntax reference](templates.md) for backreferences,
unnamed groups, lookarounds, and repeated captures.
