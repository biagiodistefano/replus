import unittest
import os

from replus import Engine

__HERE__ = os.path.dirname(os.path.abspath(__file__))

test_models_path = os.path.join(__HERE__, "test_models")
engine = Engine(test_models_path)


class TestEngine(unittest.TestCase):

    def test_parser_regex(self):
        patterns = [p.pattern for k, p, t in engine.patterns if k == "tests"]
        expected = [
            r"This is an unnamed number group: (?:\d).",
            r"I can match (?P<abg_0>alpha|beta|gamma) and (?P<abg_1>alpha|beta|gamma), and then re-match the last (?P=abg_1) or the second last (?P=abg_0)",
        ]
        for i, p in enumerate(patterns):
            self.assertEqual(p, expected[i])

    def test_match(self):
        matches = engine.parse("Today it's january 1st 1970")
        self.assertEqual(len(matches), 1)
        date = matches[0]
        self.assertEqual(date.value, "january 1st 1970")
        month = date.group("month_name")
        self.assertEqual(month.value, "january")
        day = date.group("day")
        self.assertEqual(day.value, "1")
        year = date.group("year")
        self.assertEqual(year.value, "1970")


if __name__ == "__main__":
    unittest.main(verbosity=2)
