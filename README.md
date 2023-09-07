
# Replus v0.3.0

[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](https://opensource.org/licenses/MIT)
[![codecov](https://codecov.io/gh/biagiodistefano/replus/graph/badge.svg?token=ZD31QYQTGY)](https://codecov.io/gh/biagiodistefano/replus)
[![Documentation Status](https://readthedocs.org/projects/replus/badge/?version=latest)](https://replus.readthedocs.io/en/latest/?badge=latest)
![Build](https://github.com/biagiodistefano/replus/actions/workflows/build.yml/badge.svg)
[![PyPI](https://img.shields.io/pypi/v/replus?label=pypi)](https://pypi.org/project/replus/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/replus)

A wrapper for the `regex` library for advanced pattern management.

- Checkout the [Full documentation](https://replus.readthedocs.io/).

## Quickstart

### Installation

```bash
pip install replus
```

or clone this repo

```bash
git clone git@github.com:biagiodistefano/replus.git
```

and then run

```bash
python setup.py install
```

### Template creation

The Engine loads Regular Expression **pattern templates** written in \*.json files from the provided directory, builds and compiles them in the following fashion:

example of template `patterns/date.json`:

```json
{
  "day": [
    "3[01]",
    "[12][0-9]",
    "0?[1-9]"
  ],
  "month": [
    "0?[1-9]",
    "1[012]"
  ],
  "year": [
    "\\d{4}"
  ],
  "date": [
    "{{day}}/{{month}}/{{year}}",
    "{{year}}-{{month}}-{{day}}"
  ],
  "$PATTERNS": [
    "{{date}}"
  ]
}
```

will result in the following regex:

```
(?P<date_0>(?P<day_0>[12][0-9]|0?[1-9]|3[01])/(?P<month_0>0?[1-9]|1[012])/(?P<year_0>\d{4})|(?P<year_1>\d{4})-(?P<month_1>0?[1-9]|1[012])-(?P<day_1>[12][0-9]|0?[1-9]|3[01]))
```

Only the patterns under `$PATTERNS` will be matched against at runtime.

### Querying

It is possible to query as follows:

```python
from replus import Replus

engine = Replus('patterns')

for match in engine.parse("Look at this date: 2012-20-10"):
    print(match)
    # <[Match date] span(19, 29): 2012-12-10>

    date = match.group('date')
    print(date)
    # <[Group date_0] span(19, 29): 2012-12-10>

    day = date.group('day')
    print(day)
    # <[Group day_1] span(27, 29): 10>

    month = date.group('month')
    print(month)
    # <[Group month_1] span(24, 26): 12>

    year = date.group('year')
    print(year)
    # [Group year_1] span(19, 23): 2012>
```

### Filtering

it is possible to filter regexes by type, being the type given by the json's filename's stem. E.g., in the above example, results matched by the patterns under `patterns/date.json`'s `$PATTERNS` will have type `date`

```python
filters = ["dates", "cities"]
for match in engine.parse(my_string, *filters):
    # do stuff
```

### Extra features

There are two useful secondary features:

-  **non-capturing groups**: these are specified by using the "?:" prefix in the group name or key
-  **atomic groups**: these are specified by using the "?>" prefix in the group name or key
-  **dynamic backreferences**: use `#` to reference a previous group and `@<n>` to specify how many groups behind

template:

```json
{
  "?:number": [
    "\\d"
  ],
  "abg": [
    "alpha",
    "beta",
    "gamma"
  ],
  "spam": [
     "spam"
   ],
   "eggs": [
     "eggs"
   ],
  "patterns": [
    "This is an unnamed number group: {{number}}.",
    "I can match {{abg}} and {{abg}}, and then re-match the last {{#abg}} or the second last {{#abg@2}}",
    "Here is some {{?:spam}} and some {{?>eggs}}"
  ]
}
```

It will generate the following regexs:

```
This is an unnamed number group: (?:\d).
```

```
I can match (?P<abg_0>alpha|beta|gamma) and (?P<abg_1>alpha|beta|gamma), and then re-match the last (?P=abg_1) or the second last (?P=abg_0)
```

```
Here is some (?:spam) and some (?>eggs)
```

**N.B.**: in order to obtain an escape char, such as `\d`, in the pattern's model it **must** be double escaped: `\\d`
