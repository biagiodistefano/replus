# Replus

[![PyPI](https://img.shields.io/pypi/v/replus?label=pypi)](https://pypi.org/project/replus/)
[![Python versions](https://img.shields.io/pypi/pyversions/replus)](https://pypi.org/project/replus/)
[![CI](https://github.com/biagiodistefano/replus/actions/workflows/ci.yml/badge.svg)](https://github.com/biagiodistefano/replus/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/biagiodistefano/replus/graph/badge.svg?token=ZD31QYQTGY)](https://codecov.io/gh/biagiodistefano/replus)
[![Documentation Status](https://readthedocs.org/projects/replus/badge/?version=latest)](https://replus.readthedocs.io/en/latest/?badge=latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**Template-based regular expression management**, powered by the [regex](https://github.com/mrabarnett/mrab-regex) library.

Define regex fragments as named template keys, compose them with `{{placeholders}}`,
and query matches through nested, named `Match`/`Group` objects — instead of
maintaining one unreadable 400-character pattern.

- **[Full documentation](https://replus.readthedocs.io/)**
- Fully typed, zero-magic, 100% test coverage; the only runtime dependency is `regex`.

## Installation

```bash
uv add replus
# or
pip install replus
```

Requires Python 3.11+.

## Quickstart

The engine loads pattern templates from `*.json` files in a directory (or a plain
dict). Every key defines a reusable fragment; only the patterns under `$PATTERNS`
are matched at runtime.

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

builds and compiles to:

```text
(?P<date_0>(?P<day_0>3[01]|[12][0-9]|0?[1-9])/(?P<month_0>0?[1-9]|1[012])/(?P<year_0>\d{4})|(?P<year_1>\d{4})-(?P<month_1>0?[1-9]|1[012])-(?P<day_1>3[01]|[12][0-9]|0?[1-9]))
```

Match and query by *template key* — the engine resolves which numbered alternative
actually matched:

```python
from replus import Replus

engine = Replus("patterns")

for match in engine.parse("Look at this date: 1970-12-25"):
    print(repr(match))
    # <[Match date] span(19, 29): 1970-12-25>

    date = match.group("date")
    print(repr(date.group("day")))    # <Group day_1 span(27, 29) @0: '25'>
    print(repr(date.group("month")))  # <Group month_1 span(24, 26) @0: '12'>
    print(repr(date.group("year")))   # <Group year_1 span(19, 23) @0: '1970'>

    print(match.json(indent=2))       # full nested serialization
```

Filter by pattern type (the template's file stem), or take the raw lazy stream:

```python
engine.parse(text, filters=["date"])   # only date patterns
engine.parse(text, exclude=["cities"]) # everything but cities
engine.search(text)                    # first match or None
engine.finditer(text)                  # lazy, unpurged iterator
```

Rewrite captured groups in place — e.g. to fix OCR errors only inside matches,
with a literal string or a callable receiving the `Group`:

```python
engine.sub("ID 1809900 and 1809900", {"prefix": "l"})
# 'ID l809900 and l809900'
engine.sub(text, {"prefix": lambda g: g.value.replace("1", "l")})
```

There's more: backreferences (`{{#key}}`, `{{#key@2}}`), unnamed/atomic groups and
lookarounds (`{{?:key}}`, `{{?>key}}`, `{{?=key}}`, …), repeated captures
(`group.reps()`), whitespace-noise injection, and overlap purging. See the
[template syntax reference](https://replus.readthedocs.io/en/latest/templates.html).

## Development

```bash
git clone https://github.com/biagiodistefano/replus.git
cd replus
uv sync --all-groups

uv run pytest --cov=replus   # tests (coverage gate: 100%)
uv run ruff check .          # lint
uv run ruff format .         # format
uv run ty check              # type check
uv run sphinx-build -b html docs docs/_build  # docs
```

## License

[MIT](LICENSE) © Biagio Distefano
