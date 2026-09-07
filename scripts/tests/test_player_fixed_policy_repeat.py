import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from player_fixed_policy_repeat import differences, first_difference


class RepeatComparisonTests(unittest.TestCase):
    def test_identical(self):
        self.assertEqual(first_difference(iter([{"x": [1, 2]}]), iter([{"x": [1, 2]}])), {"equal": True})

    def test_first_difference_keeps_previous_equal_state(self):
        a = [{"tick": 0, "ball": [0.0]}, {"tick": 1, "ball": [0.1]}]
        b = [{"tick": 0, "ball": [0.0]}, {"tick": 1, "ball": [0.2]}]
        result = first_difference(iter(a), iter(b))
        self.assertEqual(result["identicalPrefixRows"], 1)
        self.assertEqual(result["previousEqualRow"], a[0])
        self.assertEqual(result["differences"][0]["path"], ".ball[0]")

    def test_missing_tail_is_not_equal(self):
        result = first_difference(iter([1, 2]), iter([1]))
        self.assertFalse(result["equal"])
        self.assertEqual(result["leftRow"], 2)
        self.assertIsNone(result["rightRow"])

    def test_small_float_difference_is_retained(self):
        self.assertTrue(differences([1.0], [1.00000001]))

    def test_missing_field_is_retained(self):
        self.assertEqual(differences({"x": 1}, {})[0]["missing"], "right")

    def test_difference_limit(self):
        self.assertEqual(len(differences([1]*10, [2]*10, limit=3)), 3)
