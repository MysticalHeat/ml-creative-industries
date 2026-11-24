from datetime import date, timedelta
import unittest

from prepare import annotation_decision


class AnnotationTests(unittest.TestCase):
    def test_decision_table(self):
        filed = date(2025, 1, 1)
        cases = (
            ("реализация в день подачи", 0, None, 1),
            ("реализация на границе", 90, None, 1),
            ("реализация после границы", 91, None, 0),
            ("нет финального события", None, None, 0),
            ("есть только отклонение", None, 15, 0),
            ("реализация до подачи", -1, None, None),
            ("отклонение до подачи", None, -1, None),
            ("зарегистрированы оба исхода", 30, 45, None),
        )
        for name, realized_day, rejected_day, expected in cases:
            with self.subTest(name=name):
                actual = None if realized_day is None else filed + timedelta(days=realized_day)
                rejected = None if rejected_day is None else filed + timedelta(days=rejected_day)
                self.assertEqual(annotation_decision(filed, actual, rejected), expected)


if __name__ == "__main__":
    unittest.main()
