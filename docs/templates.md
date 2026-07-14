# Template syntax

## Basics

A template source (one `.json` file, or one entry of a dict of dicts) maps **keys** to
lists of **alternatives**. When a key is expanded, its alternatives are joined with
`|`:

```json
{
  "abg": ["alpha", "beta", "gamma"],
  "$PATTERNS": ["I can match {{abg}}"]
}
```

compiles to:

```text
I can match (?P<abg_0>alpha|beta|gamma)
```

- Keys from *all* sources share one namespace: any template can reference any key,
  and defining the same key twice raises `DuplicatePatternKeyError`.
- Only the entries under `$PATTERNS` become runnable patterns; the source's file
  stem (or dict key) becomes their match *type*.
- Each expansion of a key gets a numbered group name: `abg_0`, `abg_1`, … Numbering
  is per runnable pattern, in order of expansion.
- Alternatives can reference other keys; cycles are rejected at load time with
  `CircularReferenceError` naming the cycle path.

## Backreferences

Use `{{#key}}` to re-match the text captured by the *previous* expansion of `key`,
and `{{#key@n}}` to reach `n` expansions back:

```json
{
  "abg": ["alpha", "beta", "gamma"],
  "$PATTERNS": ["{{abg}} and {{abg}}, again {{#abg}} and {{#abg@2}}"]
}
```

```text
(?P<abg_0>alpha|beta|gamma) and (?P<abg_1>alpha|beta|gamma), again (?P=abg_1) and (?P=abg_0)
```

A backreference pointing before the first expansion raises
`InvalidBackreferenceError` at load time.

## Unnamed and special groups

Two equivalent ways to produce groups that don't capture by name:

**Prefix the placeholder** — works for any special construct:

| Placeholder | Expands to |
|---|---|
| `{{?:key}}` | `(?:…)` non-capturing |
| `{{?>key}}` | `(?>…)` atomic |
| `{{?=key}}` / `{{?!key}}` | lookahead / negative lookahead |
| `{{?<=key}}` / `{{?<!key}}` | lookbehind / negative lookbehind |
| `{{?i:key}}` (also `a m s x l`) | scoped inline flag |

**Prefix the definition** — the key itself carries the prefix, and plain
`{{key}}` placeholders expand unnamed:

```json
{
  "?:number": ["\\d"],
  "$PATTERNS": ["This is an unnamed number group: {{number}}."]
}
```

```text
This is an unnamed number group: (?:\d).
```

```{note}
An unnamed expansion still advances the key's counter: `{{abg}} {{?:abg}} {{abg}}`
produces `abg_0` and `abg_2`. Querying by key (`match.groups("abg")`) returns both.
```

## Repeated captures

When a group matches several times (e.g. inside `(...)+`), each capture is
addressable:

```python
match = engine.search("foobar 34 of 1997 15 of 1988 45 of 1975")
numyear = match.group("numyear")
for rep in numyear.reps():
    print(rep.value, rep.group("num").value)
# 34 of 1997 34
# 15 of 1988 15
# 45 of 1975 45
```

`start()`, `end()` and `span()` accept a `rep_index` to address a specific
repetition.

## Whitespace noise

Pass `whitespace_noise` to the engine to make every literal space in your templates
match a pattern instead — useful for dirty text:

```python
engine = Replus("patterns", whitespace_noise=r"[\s\-_]+")
```

Every space in the compiled patterns becomes `(?:[\s\-_]+)`.

## Overlap purging

By default `parse()` drops overlapping matches, keeping the longest match of each
overlapping run. Pass `overlapped=True` to keep everything (results are then only
sorted by position), or use `finditer()` for the raw stream.
