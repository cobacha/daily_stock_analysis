# Stock Name Disk Cache Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将股票名称查询结果持久化到磁盘（`data/stock_names_cache.json`），进程重启后无需重新查询数据源。

**Architecture:**
- 新增 `src/data/stock_name_disk_cache.py`：封装 JSON 磁盘缓存的原子读写。
- 在 `DataFetcherManager` 新增私有方法 `_ensure_cache_loaded()`，通过双重检查锁（DCL）保证磁盘缓存只被加载一次，统一被 `get_stock_name` 和 `batch_get_stock_names` 调用。
- 磁盘写入策略：**批量刷盘**，仅在 `prefetch_stock_names` / `batch_get_stock_names` 结束后调用 `flush_to_disk()`，避免线程爆炸。

**Tech Stack:** Python 标准库（`json`, `pathlib`, `threading`），无新依赖。

**已知局限：** 若股票改名（如 ST 变更），磁盘缓存将返回旧名称，直至用户手动删除 `data/stock_names_cache.json`。本次不引入 TTL 机制（YAGNI）。

---

## Chunk 1: 磁盘缓存模块

### Task 1: 新建 `StockNameDiskCache` 类

**Files:**
- Create: `src/data/stock_name_disk_cache.py`
- Test: `tests/test_stock_name_disk_cache.py`

- [ ] **Step 1: 写失败测试**

```python
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
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis
python -m pytest tests/test_stock_name_disk_cache.py -v 2>&1 | head -20
```
期望：`ModuleNotFoundError: No module named 'src.data.stock_name_disk_cache'`

- [ ] **Step 3: 实现 `StockNameDiskCache`**

```python
# src/data/stock_name_disk_cache.py
# -*- coding: utf-8 -*-
"""持久化磁盘缓存：将股票名称保存为 JSON 文件，跨进程重启保留。"""
from __future__ import annotations

import json
import logging
import os
import tempfile
import threading
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_PATH = Path(__file__).parents[2] / "data" / "stock_names_cache.json"


class StockNameDiskCache:
    """线程安全的股票名称磁盘缓存（JSON，原子写入）。"""

    def __init__(self, path: "Path | None" = None) -> None:
        self._path = Path(path) if path else _DEFAULT_CACHE_PATH
        self._lock = threading.Lock()

    def load(self) -> Dict[str, str]:
        """从磁盘读取缓存。文件不存在或 JSON 损坏时返回 {}，不抛异常。"""
        if not self._path.exists():
            return {}
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
        except Exception as e:
            logger.warning(f"[股票名称缓存] 读取失败，将重建: {e}")
        return {}

    def save(self, mapping: Dict[str, str]) -> None:
        """原子写入（tempfile 与目标同目录 + os.replace），线程安全。"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with self._lock:
                # 在同目录创建 tempfile，确保与目标在同一文件系统，os.replace 不跨设备
                fd, tmp = tempfile.mkstemp(
                    dir=self._path.parent,
                    prefix=".stock_names_",
                    suffix=".tmp",
                )
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as f:
                        json.dump(mapping, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, self._path)
                except Exception:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
                    raise
        except Exception as e:
            logger.warning(f"[股票名称缓存] 写入失败: {e}")
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/test_stock_name_disk_cache.py -v
```
期望：7 tests PASSED

- [ ] **Step 5: 提交**

```bash
git add src/data/stock_name_disk_cache.py tests/test_stock_name_disk_cache.py
git commit -m "feat: add StockNameDiskCache for persistent JSON-backed name storage"
```

---

## Chunk 2: 集成到 DataFetcherManager（含 prefetch 和 batch 刷盘）

### Task 2: 预加载 + `_ensure_cache_loaded` + `flush_to_disk`

**Files:**
- Modify: `data_provider/base.py`
- Modify: `tests/test_data_fetcher_prefetch_stock_names.py`（追加集成测试）

**设计：**
- 新增 `_ensure_cache_loaded()`：DCL 保护，首次调用时读磁盘合并进 `_stock_name_cache`，两处调用方（`get_stock_name`、`batch_get_stock_names`）均调用此方法。
- 新增 `flush_to_disk()`：将 `_stock_name_cache` 快照写磁盘。
- 在 `prefetch_stock_names`（非 bulk 路径）末尾和 `batch_get_stock_names` 返回前各调用一次 `flush_to_disk()`。

- [ ] **Step 1: 写集成测试（追加到 `tests/test_data_fetcher_prefetch_stock_names.py` 末尾）**

```python
import json
import tempfile
from pathlib import Path
from src.data.stock_name_disk_cache import StockNameDiskCache


class TestDiskCacheIntegration(unittest.TestCase):
    def _make_manager(self, disk_cache: StockNameDiskCache):
        """创建带指定磁盘缓存的 DataFetcherManager stub。"""
        manager = DataFetcherManager.__new__(DataFetcherManager)
        manager._fetchers = []
        manager._disk_cache = disk_cache
        manager.get_realtime_quote = MagicMock(return_value=None)
        return manager

    def test_get_stock_name_loads_disk_cache_on_first_call(self):
        """磁盘已有名称，首次 get_stock_name 应直接命中，不查 fetcher。"""
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "names.json"
            p.write_text(json.dumps({"600519": "磁盘茅台"}))
            manager = self._make_manager(StockNameDiskCache(p))
            dummy = MagicMock()
            manager._fetchers = [dummy]

            name = DataFetcherManager.get_stock_name(manager, "600519", allow_realtime=False)

            self.assertEqual(name, "磁盘茅台")
            dummy.get_stock_name.assert_not_called()

    def test_disk_cache_loaded_only_once(self):
        """多次调用 get_stock_name，磁盘只读取一次（_disk_cache_loaded 标志）。"""
        with tempfile.TemporaryDirectory() as d:
            disk = StockNameDiskCache(Path(d) / "names.json")
            disk.save({"000001": "平安银行"})
            manager = self._make_manager(disk)

            with patch.object(disk, "load", wraps=disk.load) as mock_load:
                DataFetcherManager.get_stock_name(manager, "000001", allow_realtime=False)
                DataFetcherManager.get_stock_name(manager, "000001", allow_realtime=False)
                self.assertEqual(mock_load.call_count, 1)

    def test_flush_to_disk_saves_memory_cache(self):
        with tempfile.TemporaryDirectory() as d:
            disk = StockNameDiskCache(Path(d) / "names.json")
            manager = self._make_manager(disk)
            manager._stock_name_cache = {"TSLA": "特斯拉"}
            manager._disk_cache_loaded = True

            DataFetcherManager.flush_to_disk(manager)

            self.assertEqual(disk.load().get("TSLA"), "特斯拉")

    def test_flush_to_disk_silent_on_empty_cache(self):
        """空缓存时 flush 不报错，不写文件。"""
        with tempfile.TemporaryDirectory() as d:
            disk = StockNameDiskCache(Path(d) / "names.json")
            manager = self._make_manager(disk)
            manager._stock_name_cache = {}
            manager._disk_cache_loaded = True

            DataFetcherManager.flush_to_disk(manager)  # 不应抛异常
            self.assertFalse((Path(d) / "names.json").exists())

    def test_prefetch_writes_new_names_to_disk(self):
        """prefetch_stock_names 结束后新名称应持久化到磁盘。"""
        with tempfile.TemporaryDirectory() as d:
            disk = StockNameDiskCache(Path(d) / "names.json")
            manager = self._make_manager(disk)
            dummy = MagicMock()
            dummy.name = "DummyFetcher"
            dummy.get_stock_name.return_value = "测试股票"
            manager._fetchers = [dummy]

            DataFetcherManager.prefetch_stock_names(manager, ["999999"], use_bulk=False)

            saved = disk.load()
            self.assertEqual(saved.get("999999"), "测试股票")

    def test_batch_get_stock_names_writes_to_disk(self):
        """batch_get_stock_names 结束后名称应持久化到磁盘。"""
        with tempfile.TemporaryDirectory() as d:
            disk = StockNameDiskCache(Path(d) / "names.json")
            manager = self._make_manager(disk)
            dummy = MagicMock()
            dummy.name = "DummyFetcher"
            dummy.get_stock_name.return_value = "批量测试"
            dummy.get_stock_list = MagicMock(return_value=None)
            manager._fetchers = [dummy]

            DataFetcherManager.batch_get_stock_names(manager, ["888888"])

            saved = disk.load()
            self.assertEqual(saved.get("888888"), "批量测试")

    def test_batch_preloads_disk_cache_before_missing_check(self):
        """batch_get_stock_names 应先预加载磁盘，避免磁盘已有的名称被误当 missing 重查。"""
        with tempfile.TemporaryDirectory() as d:
            disk = StockNameDiskCache(Path(d) / "names.json")
            disk.save({"600519": "磁盘茅台"})
            manager = self._make_manager(disk)
            dummy = MagicMock()
            dummy.name = "DummyFetcher"
            manager._fetchers = [dummy]

            result = DataFetcherManager.batch_get_stock_names(manager, ["600519"])

            self.assertEqual(result.get("600519"), "磁盘茅台")
            # 磁盘已有，不应触发 fetcher
            dummy.get_stock_name.assert_not_called()
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/test_data_fetcher_prefetch_stock_names.py::TestDiskCacheIntegration -v 2>&1 | head -40
```
期望：7 tests FAILED（方法或属性不存在）

- [ ] **Step 3: 在 `data_provider/base.py` 顶部导入**

在现有 `from src.data.stock_mapping import ...` 之后添加：

```python
from src.data.stock_name_disk_cache import StockNameDiskCache
```

- [ ] **Step 4: 新增 `_ensure_cache_loaded` 私有方法**

在 `get_stock_name` 方法之前（类内部）插入：

```python
    def _ensure_cache_loaded(self) -> None:
        """首次调用时将磁盘缓存一次性合并进内存缓存（DCL，线程安全）。"""
        if hasattr(self, '_disk_cache_loaded') and self._disk_cache_loaded:
            return
        if not hasattr(self, '_init_lock'):
            self._init_lock = __import__('threading').RLock()
        with self._init_lock:
            if hasattr(self, '_disk_cache_loaded') and self._disk_cache_loaded:
                return  # 二次检查，防止并发重复加载
            if not hasattr(self, '_disk_cache'):
                self._disk_cache = StockNameDiskCache()
            disk_data = self._disk_cache.load()
            if not hasattr(self, '_stock_name_cache'):
                self._stock_name_cache = disk_data
            else:
                # 内存缓存已存在（测试 mock 场景）：仅补充磁盘中有但内存中没有的条目
                for k, v in disk_data.items():
                    self._stock_name_cache.setdefault(k, v)
            self._disk_cache_loaded = True
            if disk_data:
                logger.info(f"[股票名称] 从磁盘缓存预加载 {len(disk_data)} 条记录")
```

- [ ] **Step 5: 修改 `get_stock_name` 的缓存初始化段**

将现有代码：
```python
        # 1. 先检查缓存
        if hasattr(self, '_stock_name_cache') and stock_code in self._stock_name_cache:
            return self._stock_name_cache[stock_code]

        # 初始化缓存
        if not hasattr(self, '_stock_name_cache'):
            self._stock_name_cache = {}
```

替换为：
```python
        # 确保磁盘缓存已预加载（首次调用时执行一次，后续为 no-op）
        self._ensure_cache_loaded()

        # 1. 检查内存缓存（含磁盘预加载数据）
        if stock_code in self._stock_name_cache:
            return self._stock_name_cache[stock_code]
```

- [ ] **Step 6: 在 `batch_get_stock_names` 的内存缓存检查之前调用 `_ensure_cache_loaded`**

找到 `batch_get_stock_names` 方法头部（约第 1290 行），将：
```python
        # 1. 先检查缓存
        if not hasattr(self, '_stock_name_cache'):
            self._stock_name_cache = {}
```
替换为：
```python
        # 确保磁盘缓存已预加载（磁盘中已有的名称直接命中，不触发网络查询）
        self._ensure_cache_loaded()
```

- [ ] **Step 7: 新增 `flush_to_disk` 方法**

在 `_ensure_cache_loaded` 方法之后插入：

```python
    def flush_to_disk(self) -> None:
        """将当前内存缓存中的全部名称写入磁盘持久化文件。"""
        if not hasattr(self, '_stock_name_cache') or not self._stock_name_cache:
            return
        if not hasattr(self, '_disk_cache'):
            self._disk_cache = StockNameDiskCache()
        self._disk_cache.save(dict(self._stock_name_cache))
        logger.info(f"[股票名称] 已刷盘 {len(self._stock_name_cache)} 条记录")
```

- [ ] **Step 8: 在 `prefetch_stock_names` 非 bulk 路径末尾调用 `flush_to_disk`**

找到 `prefetch_stock_names` 方法中的 `for code in stock_codes:` 循环之后（非 bulk 路径），追加：

```python
        # 批量预取完毕后统一刷盘（bulk 路径由 batch_get_stock_names 负责刷盘）
        self.flush_to_disk()
```

完整方法应形如：
```python
    def prefetch_stock_names(self, stock_codes, use_bulk=False):
        if not stock_codes:
            return
        stock_codes = [normalize_stock_code(c) for c in stock_codes]
        if use_bulk:
            self.batch_get_stock_names(stock_codes)  # 内部会刷盘
            return
        for code in stock_codes:
            self.get_stock_name(code, allow_realtime=False)
        self.flush_to_disk()
```

- [ ] **Step 9: 在 `batch_get_stock_names` 的 `return result` 之前调用 `flush_to_disk`**

找到方法末尾，将 `return result` 替换为：

```python
        self.flush_to_disk()
        return result
```

- [ ] **Step 10: 运行全部相关测试**

```bash
python -m pytest tests/test_data_fetcher_prefetch_stock_names.py -v
```
期望：全部 PASSED（含新增 7 个集成测试）

- [ ] **Step 11: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -v --timeout=30 -x 2>&1 | tail -30
```

- [ ] **Step 12: 提交**

```bash
git add data_provider/base.py tests/test_data_fetcher_prefetch_stock_names.py
git commit -m "feat: integrate disk cache into DataFetcherManager with DCL preload and batch flush"
```

---

## 验收标准

1. 首次运行 `prefetch_stock_names` 或 `batch_get_stock_names` 后，`data/stock_names_cache.json` 存在并包含查询到的名称。
2. 重启进程后，已缓存的股票名称直接从内存（磁盘预加载）命中，不触发数据源查询。
3. `get_stock_name` 和 `batch_get_stock_names` 的磁盘预加载均通过 `_ensure_cache_loaded()` 统一入口，不存在绕过 DCL 的裸初始化路径。
4. 磁盘文件损坏时，程序正常运行（降级为空缓存），日志输出 warning。
5. 所有原有测试继续通过。

## 注意事项

- `data/` 目录已存在（含 `stock_analysis.db`），`StockNameDiskCache` 默认路径为 `data/stock_names_cache.json`。
- 磁盘写入**不在每次 `get_stock_name` 调用时发生**，只在 `prefetch_stock_names` / `batch_get_stock_names` 结束后统一刷盘。
- `_init_lock` 使用 `RLock` 允许同一线程递归调用（防死锁）。
- **已知局限**：若股票改名（如 ST 变更），旧缓存将持续返回旧名称，直至手动删除 `data/stock_names_cache.json`。
