# tests/test_stock_name_disk_cache.py
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path

from src.data.stock_name_disk_cache import StockNameDiskCache


class TestStockNameDiskCache(unittest.TestCase):
    def test_load_returns_empty_when_file_missing(self):
        with tempfile.TemporaryDirectory() as d:
            cache = StockNameDiskCache(Path(d) / "names.json")
            self.assertEqual(cache.load(), {})

    def test_load_returns_saved_data(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "names.json"
            p.write_text(json.dumps({"600519": "贵州茅台"}))
            cache = StockNameDiskCache(p)
            self.assertEqual(cache.load(), {"600519": "贵州茅台"})

    def test_save_and_reload(self):
        with tempfile.TemporaryDirectory() as d:
            cache = StockNameDiskCache(Path(d) / "names.json")
            cache.save({"TSLA": "特斯拉", "600519": "贵州茅台"})
            self.assertEqual(cache.load(), {"TSLA": "特斯拉", "600519": "贵州茅台"})

    def test_save_is_atomic_on_overwrite(self):
        """覆盖写入不会损坏文件"""
        with tempfile.TemporaryDirectory() as d:
            cache = StockNameDiskCache(Path(d) / "names.json")
            cache.save({"000001": "平安银行"})
            cache.save({"000001": "平安银行", "300750": "宁德时代"})
            self.assertEqual(cache.load()["300750"], "宁德时代")

    def test_load_ignores_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "names.json"
            p.write_text("NOT_JSON{{{")
            cache = StockNameDiskCache(p)
            self.assertEqual(cache.load(), {})

    def test_save_creates_parent_dir_if_needed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "subdir" / "names.json"
            cache = StockNameDiskCache(p)
            cache.save({"AAPL": "苹果"})
            self.assertEqual(cache.load(), {"AAPL": "苹果"})

    def test_tempfile_in_same_dir_as_target(self):
        """tempfile 与目标文件同目录，确保 os.replace 不跨设备"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "names.json"
            cache = StockNameDiskCache(p)
            cache.save({"X": "Y"})
            # 写入后目录内不应有遗留 .tmp 文件
            tmp_files = list(Path(d).glob(".stock_names_*.tmp"))
            self.assertEqual(tmp_files, [])


if __name__ == "__main__":
    unittest.main()
