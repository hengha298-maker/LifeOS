import csv
import io
import tempfile
import unittest
from pathlib import Path
from lifeos.storage import (
    add_record, get_record, init_db, update_record, delete_record,
    list_records, records_csv
)

class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / 'data' / 'demo.db'
        self.item = dict(
            unit='虚构机组', system='TEST-1', equipment='示例设备',
            event_date='2026-01-01', symptom='测试缺陷', cause='示例',
            action='示例处理', status='待处理', notes='仅用于单元测试')
    def tearDown(self):
        self.temp.cleanup()
    def test_create_and_get(self):
        init_db(self.db)
        self.assertTrue(self.db.exists())
        key = add_record(self.item, self.db)
        self.assertEqual(get_record(key, self.db)['equipment'], '示例设备')
    def test_filters(self):
        add_record(self.item, self.db)
        self.assertEqual(len(list_records(system='TEST-1', keyword='缺陷', path=self.db)), 1)
        self.assertEqual(len(list_records(system='OTHER', path=self.db)), 0)
        self.assertEqual(len(list_records(start_date='2026-01-02', path=self.db)), 0)
        self.assertEqual(len(list_records(keyword='%', path=self.db)), 0)
    def test_update_delete(self):
        key = add_record(self.item, self.db)
        self.assertTrue(update_record(key, dict(self.item, status='已完成'), self.db))
        self.assertEqual(get_record(key, self.db)['status'], '已完成')
        self.assertTrue(delete_record(key, self.db))
        self.assertIsNone(get_record(key, self.db))
    def test_validation(self):
        with self.assertRaises(ValueError):
            add_record(dict(self.item, event_date='bad'), self.db)
        with self.assertRaises(ValueError):
            add_record(dict(self.item, system=''), self.db)
    def test_csv(self):
        add_record(self.item, self.db)
        content = records_csv(list_records(path=self.db))
        self.assertTrue(content.startswith(b'\xef\xbb\xbf'))
        rows = list(csv.DictReader(io.StringIO(content.decode('utf-8-sig'))))
        self.assertEqual(rows[0]['equipment'], '示例设备')

if __name__ == '__main__':
    unittest.main()
