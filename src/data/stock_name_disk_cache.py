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
