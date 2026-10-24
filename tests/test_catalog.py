import tempfile
import unittest
from pathlib import Path
from lifeos.storage import add_record, get_record
from lifeos.catalog import add_equipment, add_system, seed_example_structure, system_tree, system_timeline, sync_from_records

class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "data" / "lifeos.db"
        self.item = dict(unit="1号机组", system="1E", equipment="测试减速机",
                         event_date="2026-01-01", symptom="虚构卡顿",
                         cause="", action="", status="待处理", notes="")
    def tearDown(self):
        self.tmp.cleanup()
    def test_preserve_legacy_and_idempotence(self):
        key = add_record(self.item, self.db)
        sync_from_records(self.db)
        sync_from_records(self.db)
        nodes = system_tree(self.db)
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0]["equipment"][0]["name"], "测试减速机")
        self.assertEqual(nodes[0]["count"], 1)
        self.assertEqual(get_record(key, self.db)["symptom"], "虚构卡顿")
    def test_timeline_filters(self):
        add_record(self.item, self.db)
        add_record(dict(self.item, equipment="给煤机", event_date="2026-01-02"), self.db)
        self.assertEqual([x["event_date"] for x in system_timeline("1号机组","1E",path=self.db)],
                         ["2026-01-02","2026-01-01"])
        self.assertEqual(len(system_timeline("1号机组","1E","测试减速机",self.db)), 1)
    def test_seed_explicitly(self):
        self.assertEqual(system_tree(self.db), [])
        seed_example_structure(self.db)
        seed_example_structure(self.db)
        self.assertEqual(len(system_tree(self.db)), 10)
    def test_add_nodes(self):
        sid = add_system("1号机组","1E",path=self.db)
        self.assertEqual(sid, add_system("1号机组","1E",path=self.db))
        first = add_equipment(sid,"示例阀门","阀门/执行机构",self.db)
        self.assertEqual(first,add_equipment(sid,"示例阀门","阀门/执行机构",self.db))
        with self.assertRaises(ValueError):
            add_equipment(999,"错误系统",path=self.db)

if __name__ == "__main__":
    unittest.main()
