tests = {
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
  "?=posahead": [
    "foo",
    "bar"
  ],
  "?<=posbehind": [
    "foo",
    "bar"
  ],
  "?!negahead": [
    "foo",
    "bar"
  ],
  "?<!negbehind": [
    "foo",
    "bar"
  ],
  "$PATTERNS": [
    "This is an unnamed number group: {{number}}.",
    "I can match {{abg}} and {{abg}}, and then re-match the last {{#abg}} or the second last {{#abg@2}}",
    "Here is some {{?:spam}} and some {{?>eggs}}",
    "{{negbehind}} blah blah, {{negahead}} foo foo, {{posbehind}} bar bar, {{posahead}} yoyo",
    "{{?<=abg}} {{?<!abg}} {{?!abg}} {{?=abg}}"
  ]
}
