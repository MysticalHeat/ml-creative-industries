import unittest
import csv
from pathlib import Path
from analysis import quarter, key_check, duplicate_check, SOURCE_FINDINGS, V1_LIMITATIONS

class Checks(unittest.TestCase):
    def test_quarter(self):
        self.assertLess(quarter('2025Q4'),quarter('2026Q1'))
        with self.assertRaises(ValueError): quarter('2025Q5')
    def test_missing_keys(self):
        self.assertEqual(key_check([{'split':'train'}],'author_id'),'не проверено: нет поля')
        self.assertEqual(duplicate_check([{'split':'train'}],'internal_id'),'не проверено: нет поля')
    def test_overlap_and_duplicates(self):
        r=[{'split':'train','k':'a'},{'split':'train','k':'a'}, {'split':'validation','k':'a'}, {'split':'test','k':'b'}]
        self.assertEqual(key_check(r,'k'),'ключей в нескольких частях: 1')
        self.assertEqual(duplicate_check(r,'k'),'строк сверх уникальных ключей: 2')
        r[0]['k']=''
        self.assertIn('пустые ключи',key_check(r,'k'))
    def test_incomplete_split(self):
        self.assertIn('отсутствует часть',key_check([{'split':'train','k':'a'}],'k'))
    def test_source_findings_and_v1_are_separate(self):
        self.assertIn('не являются верифицированными ключами людей', SOURCE_FINDINGS)
        self.assertIn('не проверка данного запуска по v1', SOURCE_FINDINGS)
        self.assertIn('парное сравнение до/после не выполнено', V1_LIMITATIONS)
        for name in ('quality_review.md', 'data_card_update.md'):
            text = (Path(__file__).parent / 'results' / name).read_text(encoding='utf-8')
            self.assertIn(SOURCE_FINDINGS, text)
            self.assertIn(V1_LIMITATIONS, text)
        with (Path(__file__).parent / 'results' / 'quality_checks.csv').open(encoding='utf-8', newline='') as f:
            checks = dict(list(csv.reader(f))[1:])
        self.assertEqual(checks['автор: пересечения частей'], 'не проверено: нет поля')
        self.assertIn('обнаружены совпадения', checks['защищённый источник: авторские поля, не проверка v1'])

if __name__ == '__main__': unittest.main()
