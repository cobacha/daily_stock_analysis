# 大盘分析缓存 + 前端展示 + 年度走势 实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 前端价格走势新增年度周期，后端为大盘 AI 复盘增加当日缓存，前端新增首页顶部大盘横条和独立大盘分析页。

**Architecture:** 后端复用 `AnalysisHistory` 表存储大盘复盘（`code='MARKET_CN'`），新增 `MarketService` 封装缓存逻辑，新增 `/api/v1/market` 路由。前端新增 `market.ts` API 客户端、`MarketTopBar` 组件、`MarketPage` 页面，并在 `ReportPriceHistory` 增加 `1y` 周期。

**Tech Stack:** Python/FastAPI, SQLAlchemy, React/TypeScript, Recharts, Tailwind CSS

**测试命令:** `.venv/bin/pytest tests/ -q --tb=short`

---

## Chunk 1: 后端 — MarketService + 缓存

### Task 1: 新建 `src/services/market_service.py`

**Files:**
- Create: `src/services/market_service.py`
- Test: `tests/test_market_service.py`

- [ ] **Step 1: 写测试（先失败）**

```python
# tests/test_market_service.py
# -*- coding: utf-8 -*-
import sys
from unittest.mock import MagicMock, patch

for _mod in ("litellm", "google.generativeai", "google.genai", "anthropic"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest


class TestMarketServiceCache:
    def _make_service(self):
        with patch("src.services.market_service.DatabaseManager") as mock_db_cls, \
             patch("src.services.market_service.AnalysisRepository") as mock_repo_cls:
            mock_db = MagicMock()
            mock_db_cls.get_instance.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo_cls.return_value = mock_repo
            from src.services.market_service import MarketService
            svc = MarketService.__new__(MarketService)
            svc.repo = mock_repo
            return svc, mock_repo

    def test_returns_cached_result_when_hit(self):
        """缓存命中时直接返回，不调用 LLM"""
        svc, mock_repo = self._make_service()
        from src.services.market_service import MARKET_CACHE_CODE, MARKET_REVIEW_TYPE
        cached_record = MagicMock()
        cached_record.analysis_summary = "今日复盘文字"
        cached_record.raw_result = '{"indices": []}'
        mock_repo.get_post_close_cache.return_value = cached_record

        result = svc.get_cached_review(region="cn")

        mock_repo.get_post_close_cache.assert_called_once_with(
            MARKET_CACHE_CODE["cn"], MARKET_REVIEW_TYPE
        )
        assert result is cached_record

    def test_returns_none_when_no_cache(self):
        svc, mock_repo = self._make_service()
        mock_repo.get_post_close_cache.return_value = None
        result = svc.get_cached_review(region="cn")
        assert result is None

    def test_save_review_calls_repo_save(self):
        """save_review 将 overview + text 序列化存入 AnalysisHistory"""
        svc, mock_repo = self._make_service()
        mock_repo.save.return_value = 1

        overview_dict = {"date": "2026-03-17", "indices": []}
        svc.save_review(region="cn", overview_dict=overview_dict, review_text="复盘内容")

        assert mock_repo.save.called
        call_kwargs = mock_repo.save.call_args
        # report_type must be MARKET_REVIEW_TYPE
        from src.services.market_service import MARKET_REVIEW_TYPE
        assert call_kwargs.kwargs.get("report_type") == MARKET_REVIEW_TYPE or \
               call_kwargs.args[2] == MARKET_REVIEW_TYPE
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/bin/pytest tests/test_market_service.py -v
```
预期：`ModuleNotFoundError` 或 `ImportError`（文件尚未创建）

- [ ] **Step 3: 实现 `src/services/market_service.py`**

```python
# -*- coding: utf-8 -*-
"""
大盘复盘服务 — 负责缓存查询与保存
"""
import json
import logging
import uuid
from typing import Optional, Dict, Any

from src.storage import DatabaseManager
from src.repositories.analysis_repo import AnalysisRepository

logger = logging.getLogger(__name__)

# 大盘复盘在 AnalysisHistory 中的特殊标识
MARKET_CACHE_CODE: Dict[str, str] = {
    "cn": "MARKET_CN",
    "us": "MARKET_US",
}
MARKET_REVIEW_TYPE = "market_review"


class MarketService:
    """大盘复盘缓存服务"""

    def __init__(self, db_manager=None):
        self.repo = AnalysisRepository(db_manager or DatabaseManager.get_instance())

    def get_cached_review(self, region: str = "cn"):
        """查询当日大盘复盘缓存，命中返回 AnalysisHistory 记录，否则返回 None"""
        code = MARKET_CACHE_CODE.get(region, MARKET_CACHE_CODE["cn"])
        return self.repo.get_post_close_cache(code, MARKET_REVIEW_TYPE)

    def save_review(
        self,
        region: str,
        overview_dict: Dict[str, Any],
        review_text: str,
    ) -> None:
        """将大盘复盘结果保存到 AnalysisHistory"""
        code = MARKET_CACHE_CODE.get(region, MARKET_CACHE_CODE["cn"])
        query_id = str(uuid.uuid4())

        # 构造一个轻量 result 对象供 save() 使用
        class _FakeResult:
            pass

        result = _FakeResult()
        result.code = code
        result.name = "大盘复盘"
        result.sentiment_score = 50
        result.trend_prediction = ""
        result.operation_advice = ""
        result.analysis_summary = review_text
        result.decision_type = "hold"
        result.confidence_level = "中"
        result.success = True

        self.repo.save(
            result=result,
            query_id=query_id,
            report_type=MARKET_REVIEW_TYPE,
            news_content=None,
            context_snapshot=overview_dict,
        )
        logger.info(f"[大盘] 复盘缓存已保存 region={region} code={code}")
```

- [ ] **Step 4: 运行测试，确认通过**

```bash
.venv/bin/pytest tests/test_market_service.py -v
```
预期：3 tests PASSED

- [ ] **Step 5: 提交**

```bash
git add src/services/market_service.py tests/test_market_service.py
git commit -m "feat: add MarketService for daily market review caching"
```

---

### Task 2: 新建 `api/v1/endpoints/market.py`

**Files:**
- Create: `api/v1/endpoints/market.py`
- Modify: `api/v1/router.py`
- Test: `tests/test_market_api.py`

- [ ] **Step 1: 写测试（先失败）**

```python
# tests/test_market_api.py
# -*- coding: utf-8 -*-
import sys
from unittest.mock import MagicMock, patch, AsyncMock

for _mod in ("litellm", "google.generativeai", "google.genai", "anthropic"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest
from fastapi.testclient import TestClient


class TestMarketApi:
    def _make_client(self):
        with patch("src.services.market_service.DatabaseManager"), \
             patch("src.services.market_service.AnalysisRepository"):
            from api.app import create_app
            app = create_app()
            return TestClient(app, raise_server_exceptions=False)

    def test_get_review_returns_200_with_cached_data(self):
        """缓存命中时 GET /api/v1/market/review 返回 200"""
        client = self._make_client()
        cached = MagicMock()
        cached.analysis_summary = "今日复盘"
        cached.raw_result = '{"date":"2026-03-17","indices":[],"up_count":2000,"down_count":1500,"flat_count":100,"limit_up_count":30,"limit_down_count":2,"total_amount":8000.0,"top_sectors":[],"bottom_sectors":[]}'
        cached.created_at = MagicMock()
        cached.created_at.isoformat.return_value = "2026-03-17T16:30:00"

        with patch("api.v1.endpoints.market.MarketService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc_cls.return_value = mock_svc
            mock_svc.get_cached_review.return_value = cached

            resp = client.get("/api/v1/market/review?region=cn")
            assert resp.status_code == 200
            data = resp.json()
            assert data["cached"] is True
            assert data["review_text"] == "今日复盘"

    def test_post_refresh_triggers_regeneration(self):
        """POST /api/v1/market/review/refresh 强制重跑"""
        client = self._make_client()
        with patch("api.v1.endpoints.market.MarketService") as mock_svc_cls, \
             patch("api.v1.endpoints.market._run_market_review") as mock_run:
            mock_svc = MagicMock()
            mock_svc_cls.return_value = mock_svc
            mock_run.return_value = {"date": "2026-03-17", "indices": [], "review_text": "新复盘", "cached": False}

            resp = client.post("/api/v1/market/review/refresh?region=cn")
            assert resp.status_code == 200
```

- [ ] **Step 2: 运行测试，确认失败**

```bash
.venv/bin/pytest tests/test_market_api.py -v
```

- [ ] **Step 3: 实现 `api/v1/endpoints/market.py`**

```python
# -*- coding: utf-8 -*-
"""大盘复盘 API 端点"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from src.services.market_service import MarketService

logger = logging.getLogger(__name__)
router = APIRouter()


def _run_market_review(region: str) -> dict:
    """
    实际执行大盘复盘生成（同步）。
    导入放在函数内，避免启动时加载重量级依赖。
    """
    from src.core.market_review import run_market_review
    from src.market_analyzer import MarketOverview

    result = run_market_review(region=region)
    # run_market_review 返回 (overview, review_text) 或 None
    if result is None:
        raise HTTPException(status_code=503, detail="大盘数据获取失败，请稍后重试")

    overview: MarketOverview = result.get("overview")
    review_text: str = result.get("review_text", "")

    # 序列化 overview
    overview_dict = _overview_to_dict(overview, review_text)

    # 保存缓存
    svc = MarketService()
    svc.save_review(region=region, overview_dict=overview_dict, review_text=review_text)

    overview_dict["cached"] = False
    return overview_dict


def _overview_to_dict(overview, review_text: str) -> dict:
    """将 MarketOverview 转为可序列化字典"""
    if overview is None:
        return {"date": "", "indices": [], "review_text": review_text}
    return {
        "date": overview.date,
        "indices": [idx.to_dict() for idx in overview.indices],
        "up_count": overview.up_count,
        "down_count": overview.down_count,
        "flat_count": overview.flat_count,
        "limit_up_count": overview.limit_up_count,
        "limit_down_count": overview.limit_down_count,
        "total_amount": overview.total_amount,
        "top_sectors": overview.top_sectors,
        "bottom_sectors": overview.bottom_sectors,
        "review_text": review_text,
    }


def _record_to_response(record, region: str) -> dict:
    """将 AnalysisHistory 缓存记录转为响应字典"""
    raw: dict = {}
    if record.raw_result:
        try:
            raw = json.loads(record.raw_result)
        except Exception:
            pass
    # context_snapshot 里存的 overview_dict
    ctx: dict = {}
    if hasattr(record, "context_snapshot") and record.context_snapshot:
        try:
            ctx = json.loads(record.context_snapshot) if isinstance(record.context_snapshot, str) else record.context_snapshot
        except Exception:
            pass

    data = ctx or raw
    return {
        "region": region,
        "cached": True,
        "date": data.get("date", ""),
        "indices": data.get("indices", []),
        "up_count": data.get("up_count", 0),
        "down_count": data.get("down_count", 0),
        "flat_count": data.get("flat_count", 0),
        "limit_up_count": data.get("limit_up_count", 0),
        "limit_down_count": data.get("limit_down_count", 0),
        "total_amount": data.get("total_amount", 0.0),
        "top_sectors": data.get("top_sectors", []),
        "bottom_sectors": data.get("bottom_sectors", []),
        "review_text": record.analysis_summary or data.get("review_text", ""),
        "generated_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/review")
def get_market_review(region: str = Query("cn", pattern="^(cn|us)$")):
    """
    获取当日大盘复盘。
    - 有缓存：直接返回
    - 无缓存：触发生成（同步，首次较慢）
    """
    svc = MarketService()
    cached = svc.get_cached_review(region=region)
    if cached:
        return _record_to_response(cached, region)

    # 无缓存，同步生成
    return _run_market_review(region)


@router.post("/review/refresh")
def refresh_market_review(region: str = Query("cn", pattern="^(cn|us)$")):
    """强制重新生成大盘复盘（忽略当日缓存）"""
    return _run_market_review(region)
```

- [ ] **Step 4: 注册路由到 `api/v1/router.py`**

在文件末尾 `portfolio` 路由之后添加：
```python
from api.v1.endpoints import analysis, auth, history, stocks, backtest, system_config, agent, usage, portfolio, market

# ...（现有路由不变）...

router.include_router(
    market.router,
    prefix="/market",
    tags=["Market"],
)
```

- [ ] **Step 5: 运行测试**

```bash
.venv/bin/pytest tests/test_market_api.py tests/test_market_service.py -v
```

- [ ] **Step 6: 运行全量测试，确认无回归**

```bash
.venv/bin/pytest tests/ -q --tb=short
```

- [ ] **Step 7: 提交**

```bash
git add api/v1/endpoints/market.py api/v1/router.py tests/test_market_api.py
git commit -m "feat: add /api/v1/market/review endpoint with daily cache"
```

---

### Task 3: 适配 `run_market_review` 返回结构

`src/core/market_review.py` 当前 `run_market_review()` 的返回值需要确认是否包含 `overview` 和 `review_text`。

**Files:**
- Read + possibly Modify: `src/core/market_review.py`

- [ ] **Step 1: 读取 `src/core/market_review.py`，检查返回值**

```bash
grep -n "def run_market_review\|return " src/core/market_review.py | head -30
```

- [ ] **Step 2: 确认/修改返回结构**

如果 `run_market_review()` 当前不返回 `{"overview": ..., "review_text": ...}`，则修改为：

```python
# 在 run_market_review() 末尾，将原来的 return 改为：
return {"overview": overview, "review_text": review_text}
```

如果已经返回该结构，跳过此步。

- [ ] **Step 3: 运行相关测试确认不回归**

```bash
.venv/bin/pytest tests/ -q --tb=short -x
```

- [ ] **Step 4: 如有修改则提交**

```bash
git add src/core/market_review.py
git commit -m "refactor: market_review returns dict with overview and review_text"
```

---

## Chunk 2: 前端 — 年度走势

### Task 4: `ReportPriceHistory.tsx` 新增年度周期

**Files:**
- Modify: `apps/dsa-web/src/components/report/ReportPriceHistory.tsx`

- [ ] **Step 1: 修改 `PeriodKey` 类型，新增 `'1y'`**

将：
```typescript
type PeriodKey = 'today' | '5d' | '10d' | 'month' | 'quarter';
```
改为：
```typescript
type PeriodKey = 'today' | '5d' | '10d' | 'month' | 'quarter' | '1y';
```

- [ ] **Step 2: 在 `PERIODS` 数组末尾追加年度配置**

在 `quarter` 配置块之后，闭合 `]` 之前，追加：
```typescript
  {
    key: '1y',
    label: '年度',
    statLabels: ['年初开盘', '最新收盘', '年内最高', '年内最低'],
    filter: (data, now) => {
      const yearStart = `${now.getFullYear()}-01`;
      return data.filter((d) => d.date >= yearStart);
    },
    xLabel: (date, idx, total) => {
      // 每隔约30条（约1个月）显示一个月份标签
      const step = Math.max(1, Math.floor(total / 12));
      return idx % step === 0 || idx === total - 1
        ? `${date.slice(5, 7)}月`
        : '';
    },
  },
```

- [ ] **Step 3: 修改数据获取逻辑——1y 时拉取 365 天**

将：
```typescript
    stocksApi
      .getHistory(stockCode, 180) // 拉取180天数据覆盖所有周期
```
改为：
```typescript
    const days = activePeriod === '1y' ? 365 : 180;
    stocksApi
      .getHistory(stockCode, days) // 1y 周期拉取365天，其他180天
```

注意：`useEffect` 依赖数组也要加入 `activePeriod`：
```typescript
  }, [stockCode, activePeriod]);
```

- [ ] **Step 4: 本地验证**

```bash
cd apps/dsa-web && npm run build 2>&1 | tail -20
```
预期：构建成功，无 TypeScript 错误

- [ ] **Step 5: 提交**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis
git add apps/dsa-web/src/components/report/ReportPriceHistory.tsx
git commit -m "feat: add 1-year period to price history chart"
```

---

## Chunk 3: 前端 — 大盘 API 客户端 + 组件 + 页面

### Task 5: 新建 `apps/dsa-web/src/api/market.ts`

**Files:**
- Create: `apps/dsa-web/src/api/market.ts`

- [ ] **Step 1: 创建文件**

```typescript
// apps/dsa-web/src/api/market.ts
import apiClient from './index';

export type MarketIndexData = {
  code: string;
  name: string;
  current: number;
  change: number;
  change_pct: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  amplitude: number;
};

export type SectorData = {
  name: string;
  change_pct: number;
  [key: string]: unknown;
};

export type MarketReviewResponse = {
  region: string;
  cached: boolean;
  date: string;
  indices: MarketIndexData[];
  up_count: number;
  down_count: number;
  flat_count: number;
  limit_up_count: number;
  limit_down_count: number;
  total_amount: number;
  top_sectors: SectorData[];
  bottom_sectors: SectorData[];
  review_text: string;
  generated_at: string | null;
};

export const marketApi = {
  async getReview(region = 'cn'): Promise<MarketReviewResponse> {
    const resp = await apiClient.get('/api/v1/market/review', {
      params: { region },
      timeout: 120000, // 首次生成可能需要较长时间
    });
    return resp.data as MarketReviewResponse;
  },

  async refreshReview(region = 'cn'): Promise<MarketReviewResponse> {
    const resp = await apiClient.post('/api/v1/market/review/refresh', null, {
      params: { region },
      timeout: 120000,
    });
    return resp.data as MarketReviewResponse;
  },
};
```

- [ ] **Step 2: 提交**

```bash
git add apps/dsa-web/src/api/market.ts
git commit -m "feat: add market API client"
```

---

### Task 6: 新建 `MarketTopBar.tsx`（首页顶部横条）

**Files:**
- Create: `apps/dsa-web/src/components/market/MarketTopBar.tsx`
- Modify: `apps/dsa-web/src/pages/HomePage.tsx`

- [ ] **Step 1: 创建组件目录并实现组件**

```typescript
// apps/dsa-web/src/components/market/MarketTopBar.tsx
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { marketApi, type MarketReviewResponse } from '../../api/market';

const fmt = (v: number) => v.toFixed(2);
const fmtPct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
const colorOf = (v: number) =>
  v > 0 ? 'text-[#ff4d4d]' : v < 0 ? 'text-[#00d46a]' : 'text-muted-text';

export const MarketTopBar: React.FC = () => {
  const [data, setData] = useState<MarketReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const load = () => {
      marketApi
        .getReview('cn')
        .then((res) => { if (!cancelled) { setData(res); setLoading(false); } })
        .catch(() => { if (!cancelled) setLoading(false); });
    };

    load();

    // 若后台正在生成（loading 状态），每 5s 轮询一次，最多 60s
    let pollCount = 0;
    const timer = setInterval(() => {
      if (data !== null || pollCount > 12) { clearInterval(timer); return; }
      pollCount++;
      load();
    }, 5000);

    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  if (loading) {
    return (
      <div className="w-full bg-elevated border-b border-white/5 px-4 py-2 flex items-center gap-4 overflow-x-auto">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-4 w-24 bg-white/5 rounded animate-pulse flex-shrink-0" />
        ))}
      </div>
    );
  }

  if (!data || data.indices.length === 0) return null;

  // 只展示前3个主要指数
  const mainIndices = data.indices.slice(0, 3);
  // 取复盘文字前60字作为摘要
  const summary = data.review_text ? data.review_text.replace(/#{1,6}\s*/g, '').slice(0, 60) : '';

  return (
    <div className="w-full bg-elevated border-b border-white/5 px-4 py-2 flex items-center gap-4 overflow-x-auto text-xs">
      {/* 主要指数 */}
      {mainIndices.map((idx) => (
        <div key={idx.code} className="flex items-center gap-1.5 flex-shrink-0">
          <span className="text-muted-text">{idx.name}</span>
          <span className="font-mono text-white">{fmt(idx.current)}</span>
          <span className={`font-mono ${colorOf(idx.change_pct)}`}>{fmtPct(idx.change_pct)}</span>
        </div>
      ))}

      {/* 成交额 */}
      {data.total_amount > 0 && (
        <div className="flex items-center gap-1 flex-shrink-0 text-muted-text">
          <span>成交额</span>
          <span className="text-white font-mono">{data.total_amount.toFixed(0)}亿</span>
        </div>
      )}

      {/* 分隔 */}
      <div className="w-px h-3 bg-white/10 flex-shrink-0" />

      {/* AI 复盘摘要（可点击进入大盘页） */}
      {summary && (
        <Link
          to="/market"
          className="text-muted-text hover:text-white transition-colors truncate max-w-xs flex-shrink min-w-0"
          title="查看完整大盘复盘"
        >
          {summary}…
        </Link>
      )}

      {/* 跳转箭头 */}
      <Link
        to="/market"
        className="ml-auto flex-shrink-0 text-cyan hover:text-cyan/80 transition-colors"
        title="查看大盘分析"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </Link>
    </div>
  );
};
```

- [ ] **Step 2: 在 `HomePage.tsx` 顶部引入 `MarketTopBar`**

在 `HomePage.tsx` 的 import 区域添加：
```typescript
import { MarketTopBar } from '../components/market/MarketTopBar';
```

找到 `return (` 开始的 JSX，在最顶层容器内的第一个子元素之前插入：
```tsx
<MarketTopBar />
```

具体位置：找到 HomePage return 中的最外层 `<div` 或 `<>` 后的第一行，在其前插入 `<MarketTopBar />`。

- [ ] **Step 3: 构建验证**

```bash
cd apps/dsa-web && npm run build 2>&1 | tail -20
```

- [ ] **Step 4: 提交**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis
git add apps/dsa-web/src/components/market/MarketTopBar.tsx apps/dsa-web/src/pages/HomePage.tsx
git commit -m "feat: add MarketTopBar to homepage with indices and AI summary"
```

---

### Task 7: 新建 `MarketPage.tsx`（独立大盘分析页）

**Files:**
- Create: `apps/dsa-web/src/pages/MarketPage.tsx`
- Modify: `apps/dsa-web/src/App.tsx`（添加路由 + 导航图标）

- [ ] **Step 1: 创建 `MarketPage.tsx`**

```typescript
// apps/dsa-web/src/pages/MarketPage.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { marketApi, type MarketReviewResponse } from '../api/market';
import { Card } from '../components/common';

const fmt = (v: number) => v.toFixed(2);
const fmtPct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
const colorOf = (v: number) =>
  v > 0 ? 'text-[#ff4d4d]' : v < 0 ? 'text-[#00d46a]' : 'text-muted-text';
const bgOf = (v: number) =>
  v > 0 ? 'bg-[#ff4d4d]/10' : v < 0 ? 'bg-[#00d46a]/10' : 'bg-white/5';

const MarketPage: React.FC = () => {
  const [data, setData] = useState<MarketReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    marketApi
      .getReview('cn')
      .then(setData)
      .catch(() => setError('大盘数据获取失败，请稍后重试'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleRefresh = () => {
    setRefreshing(true);
    setError(null);
    marketApi
      .refreshReview('cn')
      .then(setData)
      .catch(() => setError('复盘刷新失败，请稍后重试'))
      .finally(() => setRefreshing(false));
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* 页头 */}
      <div className="sticky top-0 z-10 bg-base border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold text-white">大盘分析</h1>
          {data && (
            <p className="text-xs text-muted-text mt-0.5">
              {data.date}
              {data.cached && <span className="ml-2 text-cyan/60">已缓存</span>}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={loading || refreshing}
          className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
        >
          {refreshing ? (
            <span className="w-3 h-3 border border-white/20 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          刷新复盘
        </button>
      </div>

      <div className="flex-1 px-4 py-4 space-y-4 max-w-3xl mx-auto w-full">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
            <span className="ml-3 text-sm text-muted-text">正在获取大盘数据…</span>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {!loading && data && (
          <>
            {/* 主要指数 */}
            <Card variant="bordered" padding="md">
              <h2 className="text-sm font-semibold text-white mb-3">主要指数</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {data.indices.map((idx) => (
                  <div key={idx.code} className={`rounded-lg p-3 ${bgOf(idx.change_pct)}`}>
                    <p className="text-xs text-muted-text mb-1">{idx.name}</p>
                    <p className="text-lg font-mono font-semibold text-white">{fmt(idx.current)}</p>
                    <p className={`text-sm font-mono ${colorOf(idx.change_pct)}`}>
                      {fmtPct(idx.change_pct)}
                      <span className="text-xs ml-1">({fmt(idx.change)})</span>
                    </p>
                  </div>
                ))}
              </div>
            </Card>

            {/* 涨跌统计 */}
            {data.up_count > 0 && (
              <Card variant="bordered" padding="md">
                <h2 className="text-sm font-semibold text-white mb-3">涨跌统计</h2>
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-3 text-center">
                  {[
                    { label: '上涨', value: data.up_count, color: 'text-[#ff4d4d]' },
                    { label: '下跌', value: data.down_count, color: 'text-[#00d46a]' },
                    { label: '平盘', value: data.flat_count, color: 'text-muted-text' },
                    { label: '涨停', value: data.limit_up_count, color: 'text-[#ff4d4d]' },
                    { label: '跌停', value: data.limit_down_count, color: 'text-[#00d46a]' },
                  ].map((item) => (
                    <div key={item.label}>
                      <p className="text-xs text-muted-text mb-1">{item.label}</p>
                      <p className={`text-xl font-mono font-bold ${item.color}`}>{item.value}</p>
                    </div>
                  ))}
                </div>
                {data.total_amount > 0 && (
                  <p className="mt-3 text-xs text-muted-text text-right">
                    两市成交额 <span className="text-white font-mono">{data.total_amount.toFixed(0)} 亿</span>
                  </p>
                )}
              </Card>
            )}

            {/* 板块涨跌榜 */}
            {(data.top_sectors.length > 0 || data.bottom_sectors.length > 0) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {data.top_sectors.length > 0 && (
                  <Card variant="bordered" padding="md">
                    <h2 className="text-sm font-semibold text-[#ff4d4d] mb-3">涨幅榜 Top5</h2>
                    <div className="space-y-2">
                      {data.top_sectors.map((s, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-white">{s.name}</span>
                          <span className="font-mono text-[#ff4d4d]">+{s.change_pct?.toFixed(2)}%</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
                {data.bottom_sectors.length > 0 && (
                  <Card variant="bordered" padding="md">
                    <h2 className="text-sm font-semibold text-[#00d46a] mb-3">跌幅榜 Top5</h2>
                    <div className="space-y-2">
                      {data.bottom_sectors.map((s, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-white">{s.name}</span>
                          <span className="font-mono text-[#00d46a]">{s.change_pct?.toFixed(2)}%</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </div>
            )}

            {/* AI 复盘全文 */}
            {data.review_text && (
              <Card variant="bordered" padding="md">
                <h2 className="text-sm font-semibold text-white mb-3">AI 复盘</h2>
                <div className="prose prose-invert prose-sm max-w-none text-sm text-secondary-text leading-relaxed whitespace-pre-wrap">
                  {data.review_text}
                </div>
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default MarketPage;
```

- [ ] **Step 2: 在 `App.tsx` 添加路由和导航图标**

**2a.** 在 import 区域末尾添加：
```typescript
import MarketPage from './pages/MarketPage';
```

**2b.** 在 `NAV_ITEMS` 数组中，在 `chat` 和 `portfolio` 之间插入：
```typescript
    {
        key: 'market',
        label: '大盘',
        to: '/market',
        icon: MarketIcon,
    },
```

**2c.** 在 `ChatIcon` 定义之后添加 `MarketIcon`：
```typescript
const MarketIcon: React.FC<{ active?: boolean }> = ({active}) => (
    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 2 : 1.5}
              d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z"/>
    </svg>
);
```

**2d.** 在 `<Routes>` 中添加：
```tsx
<Route path="/market" element={<MarketPage/>}/>
```

- [ ] **Step 3: 构建验证**

```bash
cd apps/dsa-web && npm run build 2>&1 | tail -20
```

- [ ] **Step 4: 运行全量后端测试**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis
.venv/bin/pytest tests/ -q --tb=short
```

- [ ] **Step 5: 提交**

```bash
git add apps/dsa-web/src/pages/MarketPage.tsx apps/dsa-web/src/App.tsx
git commit -m "feat: add MarketPage with full market overview and AI review"
```

---

## Chunk 4: 前端构建 & 最终验证

### Task 8: 构建前端并确认完整功能

**Files:**
- Read: `apps/dsa-web/package.json`（确认构建命令）

- [ ] **Step 1: 完整前端构建**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis/apps/dsa-web
npm run build
```
预期：build 成功，产物在 `../../static/`

- [ ] **Step 2: 后端全量测试**

```bash
cd /Users/11069760/claude-test/daily_stock_analysis
.venv/bin/pytest tests/ -q --tb=short
```
预期：所有测试通过（≥775 passed）

- [ ] **Step 3: 提交构建产物（如需要）**

```bash
git add static/
git commit -m "chore: rebuild frontend with market analysis and yearly chart"
```

---

## 完成后验收清单

- [ ] 价格走势图有"年度"选项，切换后显示当年所有交易日数据，X 轴按月份标注
- [ ] 首页顶部横条显示上证/深证/创业板涨跌幅 + 成交额 + AI 复盘摘要
- [ ] 首页横条点击跳转到 `/market` 页面
- [ ] 导航栏有"大盘"图标
- [ ] 大盘分析页显示：指数卡片 + 涨跌统计 + 板块榜 + AI 复盘全文
- [ ] 大盘分析页"刷新复盘"按钮可强制重新生成
- [ ] 当日已生成过的大盘复盘，再次访问直接从缓存返回（不重复调用 LLM）
- [ ] 全量测试 `≥775 passed`
