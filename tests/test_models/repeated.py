repeated = {
  "num": [
    "\\d+"
  ],
  "fooyear": [
    "19\\d\\d"
  ],
  "numyear": [
    "{{num}} of {{fooyear}}"
  ],
  "foobar": [
    "foobar",
    "barfoo",
    "foo",
    "bar"
  ],
  "$PATTERNS": [
    "{{foobar}} ({{numyear}} ?)+"
  ]
}
