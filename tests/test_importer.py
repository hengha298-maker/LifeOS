import tempfile
import unittest
from pathlib import Path
import pandas as pd
from lifeos.importer import guess_mapping, import_records, preview_import, read_table
from lifeos.storage import add_record, get_record, list_records

class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "data" / "lifeos.db"
        self.df = pd.DataFrame([
            {"机组":"1号机组","系统":"1E","设备":"示例磨煤机","日期":"2026-01-01","缺陷现象":"测试A"},
            {"机组":"1号机组","系统":"1E","设备":"示例磨煤机","日期":"2026-01-01","缺陷现象":"测试A"},
            {"机组":"1号机组","系统":"1E","设备":"示例磨煤机","日期":"错误日期","缺陷现象":"测试B"},
        ])
    def tearDown(self):
        self.tmp.cleanup()
    def test_preview_does_not_import(self):
        preview=preview_import(self.df,guess_mapping(list(self.df.columns)),path=self.db)
        self.assertEqual((len(preview["ready"]),len(preview["duplicates"]),len(preview["errors"])),(1,1,1))
        self.assertEqual(list_records(path=self.db),[])
    def test_import_and_backup(self):
        preview=preview_import(self.df,guess_mapping(list(self.df.columns)),path=self.db)
        count,backup=import_records(preview["ready"],self.db)
        self.assertEqual(count,1)
        self.assertTrue(backup.is_file())
        count_again,_=import_records(preview["ready"],self.db)
        self.assertEqual(count_again,0)
        self.assertEqual(len(list_records(path=self.db)),1)
    def test_bad_batch_no_writes(self):
        row=dict(unit="1号机组",system="1E",equipment="测试设备",event_date="2026-01-01",
                 symptom="测试",cause="",action="",status="待处理",notes="")
        key=add_record(row,self.db)
        with self.assertRaises(ValueError):
            import_records([row,dict(row,event_date="not a date")],self.db)
        self.assertEqual(len(list_records(path=self.db)),1)
        self.assertIsNotNone(get_record(key,self.db))
    def test_csv_and_limits(self):
        data="机组,系统,设备,日期,缺陷现象\n1号机组,1E,示例设备,2026-01-01,虚构\n".encode("utf-8-sig")
        self.assertEqual(len(read_table("test.csv",data)),1)
        with self.assertRaises(ValueError):
            read_table("test.pdf",data)
        with self.assertRaises(ValueError):
            read_table("test.csv",b"x"*(10*1024*1024+1))

if __name__=="__main__":
    unittest.main()
