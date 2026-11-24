import unittest
from fractions import Fraction

from experiment import metrics, predict, quarter_number


class ExperimentTests(unittest.TestCase):
    def test_quarter_and_predictions(self):
        self.assertEqual(quarter_number("2024Q4"), 8099)
        self.assertEqual(predict(quarter_number("2025Q4"), 8099, True), 1)
        with self.assertRaises(ValueError):
            quarter_number("2024Q5")

    def test_constant_predictions_and_missing_precision(self):
        baseline = metrics([(0, 0)] * 547 + [(1, 0)] * 512)
        candidate = metrics([(0, 1)] * 547 + [(1, 1)] * 512)
        self.assertEqual(baseline["BA"], Fraction(1, 2))
        self.assertEqual(candidate["BA"], Fraction(1, 2))
        self.assertIsNone(baseline["precision1"])
        self.assertEqual(candidate["FP"], 547)
        self.assertEqual(candidate["TP"], 512)


if __name__ == "__main__":
    unittest.main()
