import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
import baseline
import demo


class DemoTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'history.sqlite3')
        self.db = demo.connect(self.path)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_rule_changes_route_same_model(self):
        a = demo.create(self.db, 'enough', 'enough')
        b = demo.create(self.db, 'insufficient', 'insufficient')
        self.assertEqual(a['model']['prediction'], b['model']['prediction'])
        self.assertEqual((a['route'], b['route']), ('expert_action', 'manual_review'))
        with self.assertRaises(ValueError):
            demo.act(self.db, 'insufficient', 'confirm', 'reason')
        h = demo.act(self.db, 'insufficient', 'review', 'missing', recipient='reviewer', next_step='check')
        self.assertEqual(h['actions'][0]['status'], 'pending_review')
        self.assertIsNone(h['actions'][0]['result_class'])

    def test_correct_and_reread(self):
        demo.create(self.db, 'synthetic', 'enough')
        demo.act(self.db, 'synthetic', 'correct', 'synthetic reason', corrected=1)
        self.db.close()
        self.db = demo.connect(self.path)
        h = demo.history(self.db, 'synthetic')
        self.assertEqual(h['model']['prediction']['class'], 0)
        self.assertEqual(h['actions'][0]['result_class'], 1)
        self.assertFalse(h['actions'][0]['model_updated'])
        with self.assertRaises(ValueError):
            demo.act(self.db, 'synthetic', 'confirm', 'again')

    def test_failure_does_not_forge_class(self):
        h = demo.create(self.db, 'failure', 'enough', True)
        self.assertEqual(h['model']['error']['code'], 'model_unavailable')
        with self.assertRaises(ValueError):
            demo.act(self.db, 'failure', 'correct', 'reason', corrected=1)
        h = demo.act(self.db, 'failure', 'review', 'failure', recipient='reviewer', next_step='inspect')
        self.assertIsNone(h['actions'][0]['result_class'])
        self.assertEqual(h['actions'][0]['status'], 'pending_review')

    def test_invalid_and_duplicate_do_not_record(self):
        with self.assertRaises(ValueError):
            demo.create(self.db, 'invalid id', 'enough')
        self.assertEqual(self.db.execute('select count(*) from cases').fetchone()[0], 0)
        demo.create(self.db, 'valid', 'enough')
        with self.assertRaises(sqlite3.IntegrityError):
            demo.create(self.db, 'valid', 'enough')
        with self.assertRaises(ValueError):
            demo.act(self.db, 'valid', 'correct', 'reason', corrected=True)
        self.assertEqual(demo.history(self.db, 'valid')['actions'], [])

    def test_model_original_and_hash_check(self):
        self.assertEqual(baseline.handle(json.dumps({'schema_version':'1.0','request_id':'x'}))['prediction']['class'], 0)
        path = Path(self.tmp.name) / 'tampered.json'
        path.write_text('{}')
        self.assertEqual(baseline.handle(json.dumps({'schema_version':'1.0','request_id':'x'}), path)['error']['code'], 'model_unavailable')

    def test_review_chain(self):
        demo.create(self.db, 'chain', 'enough')
        h = demo.act(self.db, 'chain', 'review', 'check', recipient='reviewer', next_step='inspect')
        first = h['actions'][0]['id']
        h = demo.act(self.db, 'chain', 'confirm', 'checked')
        self.assertEqual(h['actions'][1]['previous_id'], first)


if __name__ == '__main__':
    unittest.main()
