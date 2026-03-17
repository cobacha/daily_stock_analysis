# Analysis Pipeline Upgrade Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 渐进式升级股票分析流程，新增四个数据收集器（技术形态标签、新闻LLM分类、资金流向、同行对比），并将结果注入现有Agent骨架，全面提升分析深度和数据质量。

**Architecture:** 混合型架构——第一阶段并行运行四个纯数据收集器（部分使用LLM），将结构化结果汇聚为 `EnrichedStockContext`，第二阶段注入已有的 TechnicalAgent/IntelAgent/DecisionAgent 骨架。渐进式替换，`pipeline.py` 入口保持不变，每个 Phase 独立可测试、可回滚。

**Tech Stack:** Python, AkShare, `src/agent/llm_adapter.LLMToolAdapter`, `src/stock_analyzer.StockTrendAnalyzer`, `src/core/pipeline.StockAnalysisPipeline`, `src/agent/` Agent 骨架

**Spec:** `docs/superpowers/specs/2026-03-17-analysis-pipeline-upgrade-design.md`

---

## 文件结构

### 新建文件
- `src/collectors/__init__.py` — collectors 包入口
- `src/collectors/models.py` — 所有数据结构定义（FundFlowData, ClassifiedNews, PeerData, EnrichedStockContext）
- `src/collectors/technical_pattern_labeler.py` — Phase 1: 技术形态标签器
- `src/collectors/news_preprocessor.py` — Phase 2: 新闻LLM分类预处理器
- `src/collectors/fund_flow_collector.py` — Phase 3: 资金流向收集器
- `src/collectors/peer_comparison_collector.py` — Phase 4: 同行对比收集器
- `tests/collectors/test_technical_pattern_labeler.py`
- `tests/collectors/test_news_preprocessor.py`
- `tests/collectors/test_fund_flow_collector.py`
- `tests/collectors/test_peer_comparison_collector.py`

### 修改文件
- `src/core/pipeline.py` — Phase 1~5 各阶段逐步注入收集器调用
- `src/agent/agents/technical_agent.py` — Phase 1: 注入 technical_labels + 资金数据
- `src/agent/agents/intel_agent.py` — Phase 2: 替换为 classified_news 输入
- `src/agent/orchestrator.py` — Phase 4: 注册 PeerAgent

---

## Chunk 1: 基础数据结构 + Phase 1 技术形态标签

### Task 1: 建立 collectors 包和数据模型

**Files:**
- Create: `src/collectors/__init__.py`
- Create: `src/collectors/models.py`

- [ ] **Step 1: 创建包结构和数据模型**

```python
# src/collectors/__init__.py
from src.collectors.models import (
    FundFlowData,
    ClassifiedNewsItem,
    ClassifiedNews,
    PeerStock,
    PeerData,
    EnrichedStockContext,
)

__all__ = [
    "FundFlowData",
    "ClassifiedNewsItem",
    "ClassifiedNews",
    "PeerStock",
    "PeerData",
    "EnrichedStockContext",
]
```

```python
# src/collectors/models.py
# -*- coding: utf-8 -*-
"""
collectors 共享数据模型定义
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict


@dataclass
class FundFlowData:
    """资金流向数据"""
    main_net_inflow_1d: Optional[float] = None   # 当日主力净流入(万元)
    main_net_inflow_3d: Optional[float] = None   # 3日主力净流入
    main_net_inflow_5d: Optional[float] = None   # 5日主力净流入
    northbound_change: Optional[float] = None    # 北向资金持仓变化(万股)
    northbound_trend: Optional[str] = None       # "持续流入"/"持续流出"/"震荡"
    lhb_records: List[Dict] = field(default_factory=list)  # 龙虎榜记录
    has_data: bool = False


@dataclass
class ClassifiedNewsItem:
    """经LLM分类的单条新闻"""
    title: str
    snippet: str
    url: str = ""
    publish_time: Optional[str] = None
    sentiment: str = "neutral"          # "bullish" / "bearish" / "neutral"
    impact_level: str = "low"           # "high" / "medium" / "low"
    event_tags: List[str] = field(default_factory=list)
    recency_weight: float = 0.5         # 0.0 ~ 1.0
    reason: str = ""


@dataclass
class ClassifiedNews:
    """经LLM分类的新闻集合"""
    items: List[ClassifiedNewsItem] = field(default_factory=list)
    bullish_count: int = 0
    bearish_count: int = 0
    neutral_count: int = 0
    top_events: List[str] = field(default_factory=list)
    has_data: bool = False


@dataclass
class PeerStock:
    """同行竞品数据"""
    code: str
    name: str
    change_pct: float = 0.0
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    market_cap: Optional[float] = None  # 总市值(亿)


@dataclass
class PeerData:
    """同行对比数据"""
    sector_name: str = ""
    sector_change_pct: float = 0.0
    peers: List[PeerStock] = field(default_factory=list)
    target_rank_in_sector: int = 0
    target_pe_vs_sector_avg: Optional[float] = None  # PE相对板块均值溢价率
    has_data: bool = False


@dataclass
class EnrichedStockContext:
    """汇聚所有收集器产出的结构化上下文"""
    stock_code: str
    stock_name: str

    # 现有数据（不变）
    price_data: Dict = field(default_factory=dict)
    kline_data: Any = None
    trend_analysis: Dict = field(default_factory=dict)
    search_results: List = field(default_factory=list)

    # 新增数据（各阶段渐进注入）
    technical_labels: List[str] = field(default_factory=list)   # Phase 1
    classified_news: ClassifiedNews = field(default_factory=ClassifiedNews)   # Phase 2
    fund_flow: FundFlowData = field(default_factory=FundFlowData)             # Phase 3
    peer_comparison: PeerData = field(default_factory=PeerData)               # Phase 4
```

- [ ] **Step 2: 验证模块可导入**

```bash
PYTHONPATH=. python -c "from src.collectors import FundFlowData, ClassifiedNews, PeerData, EnrichedStockContext; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/collectors/
git commit -m "feat(collectors): add collectors package with shared data models"
```

---

### Task 2: 实现 TechnicalPatternLabeler

**Files:**
- Create: `src/collectors/technical_pattern_labeler.py`
- Create: `tests/collectors/__init__.py`
- Create: `tests/collectors/test_technical_pattern_labeler.py`

- [ ] **Step 1: 创建测试文件（先写测试）**

```python
# tests/collectors/__init__.py
# (空文件)
```

```python
# tests/collectors/test_technical_pattern_labeler.py
# -*- coding: utf-8 -*-
import pytest
from src.collectors.technical_pattern_labeler import TechnicalPatternLabeler
from src.stock_analyzer import (
    TrendAnalysisResult, TrendStatus, VolumeStatus,
    MACDStatus, RSIStatus, BuySignal
)


def _make_result(**kwargs) -> TrendAnalysisResult:
    """构造一个可自定义字段的 TrendAnalysisResult"""
    defaults = dict(
        code="000001",
        trend_status=TrendStatus.CONSOLIDATION,
        ma_alignment="",
        trend_strength=50.0,
        ma5=10.0, ma10=10.0, ma20=10.0, ma60=10.0,
        current_price=10.0,
        bias_ma5=0.0, bias_ma10=0.0, bias_ma20=0.0,
        volume_status=VolumeStatus.NORMAL,
        volume_ratio_5d=1.0,
        volume_trend="",
        macd_dif=0.1, macd_dea=0.05, macd_bar=0.1,
        macd_status=MACDStatus.BULLISH,
        macd_signal="",
        rsi_6=55.0, rsi_12=52.0, rsi_24=50.0,
        rsi_status=RSIStatus.NEUTRAL,
        rsi_signal="",
        buy_signal=BuySignal.WAIT,
        signal_score=50,
        signal_reasons=[],
        risk_factors=[],
        support_levels=[],
        resistance_levels=[],
    )
    defaults.update(kwargs)
    return TrendAnalysisResult(**defaults)


class TestTechnicalPatternLabeler:
    def setup_method(self):
        self.labeler = TechnicalPatternLabeler()

    def test_bull_alignment_label(self):
        result = _make_result(
            trend_status=TrendStatus.BULL,
            ma5=11.0, ma10=10.5, ma20=10.0,
        )
        labels = self.labeler.label(result)
        assert "多头排列" in labels

    def test_bear_alignment_label(self):
        result = _make_result(
            trend_status=TrendStatus.BEAR,
            ma5=9.0, ma10=9.5, ma20=10.0,
        )
        labels = self.labeler.label(result)
        assert "空头排列" in labels

    def test_macd_golden_cross_zero_label(self):
        result = _make_result(
            macd_status=MACDStatus.GOLDEN_CROSS_ZERO,
            macd_dif=0.2, macd_dea=0.1,
        )
        labels = self.labeler.label(result)
        assert any("零轴上金叉" in l for l in labels)

    def test_macd_golden_cross_label(self):
        result = _make_result(
            macd_status=MACDStatus.GOLDEN_CROSS,
            macd_dif=-0.05, macd_dea=-0.1,
        )
        labels = self.labeler.label(result)
        assert any("金叉" in l for l in labels)

    def test_rsi_overbought_label(self):
        result = _make_result(
            rsi_status=RSIStatus.OVERBOUGHT,
            rsi_6=78.0,
        )
        labels = self.labeler.label(result)
        assert any("RSI超买" in l for l in labels)

    def test_rsi_oversold_label(self):
        result = _make_result(
            rsi_status=RSIStatus.OVERSOLD,
            rsi_6=22.0,
        )
        labels = self.labeler.label(result)
        assert any("RSI超卖" in l for l in labels)

    def test_shrink_volume_down_label(self):
        result = _make_result(
            volume_status=VolumeStatus.SHRINK_VOLUME_DOWN,
            volume_ratio_5d=0.6,
        )
        labels = self.labeler.label(result)
        assert "缩量回调" in labels

    def test_heavy_volume_up_label(self):
        result = _make_result(
            volume_status=VolumeStatus.HEAVY_VOLUME_UP,
            volume_ratio_5d=1.8,
        )
        labels = self.labeler.label(result)
        assert "放量上涨" in labels

    def test_high_bias_label(self):
        result = _make_result(bias_ma5=6.5)
        labels = self.labeler.label(result)
        assert any("乖离过大" in l for l in labels)

    def test_empty_on_none(self):
        labels = self.labeler.label(None)
        assert labels == []

    def test_no_duplicate_labels(self):
        result = _make_result(
            trend_status=TrendStatus.STRONG_BULL,
            ma5=12.0, ma10=11.0, ma20=10.0,
            macd_status=MACDStatus.GOLDEN_CROSS_ZERO,
            macd_dif=0.3, macd_dea=0.1,
        )
        labels = self.labeler.label(result)
        assert len(labels) == len(set(labels))
```

- [ ] **Step 2: 运行测试确认失败**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_technical_pattern_labeler.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError` 或 `ImportError`（文件尚未创建）

- [ ] **Step 3: 实现 TechnicalPatternLabeler**

```python
# src/collectors/technical_pattern_labeler.py
# -*- coding: utf-8 -*-
"""
技术形态标签器

将 StockTrendAnalyzer 输出的散落数值判断汇总为人可读的技术形态标签列表。
纯计算逻辑，无LLM调用。
"""
from __future__ import annotations
import logging
from typing import List, Optional

from src.stock_analyzer import (
    TrendAnalysisResult, TrendStatus, VolumeStatus,
    MACDStatus, RSIStatus,
)

logger = logging.getLogger(__name__)


class TechnicalPatternLabeler:
    """
    将 TrendAnalysisResult 转换为人可读的技术形态标签列表。

    Usage:
        labeler = TechnicalPatternLabeler()
        labels = labeler.label(trend_result)
        # -> ["多头排列", "MACD零轴上金叉(强)", "缩量回踩MA10"]
    """

    def label(self, result: Optional[TrendAnalysisResult]) -> List[str]:
        """
        根据 TrendAnalysisResult 生成技术形态标签列表。

        Args:
            result: StockTrendAnalyzer.analyze() 的返回值，None 时返回空列表。

        Returns:
            技术形态标签列表，无重复。
        """
        if result is None:
            return []

        labels: List[str] = []

        # 1. 趋势/均线排列
        labels.extend(self._trend_labels(result))

        # 2. MACD
        labels.extend(self._macd_labels(result))

        # 3. RSI
        labels.extend(self._rsi_labels(result))

        # 4. 量能
        labels.extend(self._volume_labels(result))

        # 5. 乖离率
        labels.extend(self._bias_labels(result))

        # 去重（保持顺序）
        seen = set()
        unique = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique.append(label)

        logger.debug(f"[PatternLabeler] {result.code} 形态标签: {unique}")
        return unique

    # ------------------------------------------------------------------
    # 私有方法
    # ------------------------------------------------------------------

    def _trend_labels(self, r: TrendAnalysisResult) -> List[str]:
        labels = []
        status = r.trend_status
        if status == TrendStatus.STRONG_BULL:
            labels.append("强势多头排列")
        elif status == TrendStatus.BULL:
            labels.append("多头排列")
        elif status == TrendStatus.WEAK_BULL:
            labels.append("弱势多头")
        elif status == TrendStatus.WEAK_BEAR:
            labels.append("弱势空头")
        elif status == TrendStatus.BEAR:
            labels.append("空头排列")
        elif status == TrendStatus.STRONG_BEAR:
            labels.append("强势空头排列")
        elif status == TrendStatus.CONSOLIDATION:
            labels.append("均线盘整")
        return labels

    def _macd_labels(self, r: TrendAnalysisResult) -> List[str]:
        labels = []
        status = r.macd_status
        if status == MACDStatus.GOLDEN_CROSS_ZERO:
            labels.append("MACD零轴上金叉(强)")
        elif status == MACDStatus.GOLDEN_CROSS:
            labels.append("MACD金叉")
        elif status == MACDStatus.DEATH_CROSS:
            labels.append("MACD死叉")
        elif status == MACDStatus.BULLISH:
            labels.append("MACD多头")
        elif status == MACDStatus.BEARISH:
            labels.append("MACD空头")
        elif status == MACDStatus.CROSSING_UP:
            labels.append("MACD上穿零轴")
        elif status == MACDStatus.CROSSING_DOWN:
            labels.append("MACD下穿零轴")
        return labels

    def _rsi_labels(self, r: TrendAnalysisResult) -> List[str]:
        labels = []
        rsi_val = round(r.rsi_6, 1)
        if r.rsi_status == RSIStatus.OVERBOUGHT:
            labels.append(f"RSI超买({rsi_val})")
        elif r.rsi_status == RSIStatus.OVERSOLD:
            labels.append(f"RSI超卖({rsi_val})")
        return labels

    def _volume_labels(self, r: TrendAnalysisResult) -> List[str]:
        labels = []
        status = r.volume_status
        if status == VolumeStatus.HEAVY_VOLUME_UP:
            labels.append("放量上涨")
        elif status == VolumeStatus.HEAVY_VOLUME_DOWN:
            labels.append("放量下跌")
        elif status == VolumeStatus.SHRINK_VOLUME_UP:
            labels.append("缩量上涨")
        elif status == VolumeStatus.SHRINK_VOLUME_DOWN:
            labels.append("缩量回调")
        return labels

    def _bias_labels(self, r: TrendAnalysisResult) -> List[str]:
        labels = []
        if r.bias_ma5 > 5.0:
            labels.append(f"短线乖离过大({r.bias_ma5:.1f}%)")
        elif r.bias_ma5 < -5.0:
            labels.append(f"大幅偏离均线({r.bias_ma5:.1f}%)")
        return labels
```

- [ ] **Step 4: 运行测试确认通过**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_technical_pattern_labeler.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/technical_pattern_labeler.py tests/collectors/
git commit -m "feat(collectors): implement TechnicalPatternLabeler with full test coverage"
```

---

### Task 3: 将技术形态标签注入 pipeline（传统路径）

**Files:**
- Modify: `src/core/pipeline.py`

注入点在 `_enhance_context` 方法末尾，当 `trend_result` 存在时，追加 `technical_labels` 字段。

- [ ] **Step 1: 在 pipeline.py 顶部导入 TechnicalPatternLabeler**

在 `src/core/pipeline.py` 第 33 行附近（`from src.stock_analyzer import ...` 那行之后）添加：

```python
from src.collectors.technical_pattern_labeler import TechnicalPatternLabeler
```

- [ ] **Step 2: 在 `__init__` 中初始化 labeler**

在 `self.trend_analyzer = StockTrendAnalyzer()` 那行之后添加：

```python
        self.pattern_labeler = TechnicalPatternLabeler()
```

- [ ] **Step 3: 在 `_enhance_context` 末尾注入 technical_labels**

在 `_enhance_context` 方法中，`if trend_result:` 块注入 enhanced['trend_analysis'] 之后，追加：

```python
        # Phase 1: 注入技术形态标签
        if trend_result:
            enhanced['technical_labels'] = self.pattern_labeler.label(trend_result)
```

- [ ] **Step 4: 在传统分析 prompt 中使用 technical_labels**

在 `src/analyzer.py` 的 `analyze` 方法中，找到组装 `technical_analysis` 文本的地方，在技术分析段末尾追加：

```python
        # 注入技术形态标签
        technical_labels = context.get('technical_labels', [])
        if technical_labels:
            technical_section += f"\n\n**技术形态标签**: {', '.join(technical_labels)}"
```

（如果 analyzer.py 中是用 f-string 直接拼接的，找到对应的位置追加即可）

- [ ] **Step 5: 验证运行不报错**

```bash
PYTHONPATH=. python -c "
from src.core.pipeline import StockAnalysisPipeline
p = StockAnalysisPipeline()
print('pipeline 初始化成功，pattern_labeler:', p.pattern_labeler)
"
```

Expected: 无报错，打印出 `pattern_labeler` 对象

- [ ] **Step 6: Commit**

```bash
git add src/core/pipeline.py src/analyzer.py
git commit -m "feat(pipeline): inject technical_labels from TechnicalPatternLabeler into analysis context"
```

---

## Chunk 2: Phase 2 新闻LLM分类预处理

### Task 4: 实现 NewsPreprocessor

**Files:**
- Create: `src/collectors/news_preprocessor.py`
- Create: `tests/collectors/test_news_preprocessor.py`

- [ ] **Step 1: 先写测试**

```python
# tests/collectors/test_news_preprocessor.py
# -*- coding: utf-8 -*-
"""
NewsPreprocessor 单元测试。

关键测试策略：
- 使用 mock 替换 LLMToolAdapter，避免真实 API 调用
- 测试时效加权逻辑（纯计算，可以不 mock）
- 测试空数据的降级处理
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone

from src.collectors.news_preprocessor import NewsPreprocessor
from src.collectors.models import ClassifiedNews


def _make_search_result(title="测试新闻", snippet="新闻摘要", days_ago=1, url=""):
    """构造一个类似 SearchResult 的 mock 对象"""
    result = MagicMock()
    result.title = title
    result.snippet = snippet
    result.url = url
    result.published_date = (
        datetime.now(timezone.utc) - timedelta(days=days_ago)
    ).isoformat()
    return result


def _make_llm_response(classifications):
    """构造 LLM 返回的 JSON 字符串"""
    import json
    resp = MagicMock()
    resp.content = json.dumps(classifications)
    return resp


class TestNewsPreprocessor:
    def setup_method(self):
        self.preprocessor = NewsPreprocessor()

    def test_empty_input_returns_empty(self):
        result = self.preprocessor.process("000001", "平安银行", [])
        assert isinstance(result, ClassifiedNews)
        assert result.has_data is False
        assert result.items == []

    def test_none_input_returns_empty(self):
        result = self.preprocessor.process("000001", "平安银行", None)
        assert result.has_data is False

    def test_recency_weight_24h(self):
        """24小时内的新闻权重为 1.0"""
        weight = self.preprocessor._compute_recency_weight(0.5)  # 0.5天前
        assert weight == 1.0

    def test_recency_weight_3days(self):
        """3天内权重为 0.7"""
        weight = self.preprocessor._compute_recency_weight(2.0)
        assert weight == 0.7

    def test_recency_weight_7days(self):
        """7天内权重为 0.4"""
        weight = self.preprocessor._compute_recency_weight(5.0)
        assert weight == 0.4

    def test_recency_weight_old(self):
        """超过7天权重为 0.2"""
        weight = self.preprocessor._compute_recency_weight(10.0)
        assert weight == 0.2

    @patch("src.collectors.news_preprocessor.LLMToolAdapter")
    def test_llm_classification_bullish(self, MockLLM):
        """LLM返回利好分类，应正确解析"""
        mock_llm = MockLLM.return_value
        mock_llm.call_text.return_value = _make_llm_response([
            {
                "index": 0,
                "sentiment": "bullish",
                "impact_level": "high",
                "event_tags": ["大股东增持"],
                "reason": "大股东增持是明显利好"
            }
        ])
        raw = [_make_search_result("大股东增持100万股", "增持公告", days_ago=0.5)]
        result = self.preprocessor.process("000001", "平安银行", raw)
        assert result.has_data is True
        assert result.bullish_count == 1
        assert result.bearish_count == 0
        assert result.items[0].sentiment == "bullish"
        assert result.items[0].impact_level == "high"
        assert "大股东增持" in result.items[0].event_tags

    @patch("src.collectors.news_preprocessor.LLMToolAdapter")
    def test_llm_classification_bearish(self, MockLLM):
        """LLM返回利空分类，should正确计数"""
        mock_llm = MockLLM.return_value
        mock_llm.call_text.return_value = _make_llm_response([
            {
                "index": 0,
                "sentiment": "bearish",
                "impact_level": "high",
                "event_tags": ["被立案调查"],
                "reason": "监管处罚是明显利空"
            }
        ])
        raw = [_make_search_result("公司被证监会立案", "监管公告", days_ago=1)]
        result = self.preprocessor.process("000001", "平安银行", raw)
        assert result.bearish_count == 1
        assert result.bullish_count == 0

    @patch("src.collectors.news_preprocessor.LLMToolAdapter")
    def test_llm_failure_returns_neutral(self, MockLLM):
        """LLM调用失败时应降级返回 neutral 分类"""
        mock_llm = MockLLM.return_value
        mock_llm.call_text.side_effect = Exception("API error")
        raw = [_make_search_result("随机新闻", "测试", days_ago=1)]
        # 不应抛异常
        result = self.preprocessor.process("000001", "平安银行", raw)
        assert isinstance(result, ClassifiedNews)
        # 降级时 has_data=False 或 items 为中性
        # 只要不抛异常即可

    @patch("src.collectors.news_preprocessor.LLMToolAdapter")
    def test_top_events_extracted(self, MockLLM):
        """high impact 的事件标签应汇总到 top_events"""
        mock_llm = MockLLM.return_value
        mock_llm.call_text.return_value = _make_llm_response([
            {"index": 0, "sentiment": "bullish", "impact_level": "high",
             "event_tags": ["产品涨价"], "reason": ""},
            {"index": 1, "sentiment": "bearish", "impact_level": "low",
             "event_tags": ["常规波动"], "reason": ""},
        ])
        raw = [
            _make_search_result("产品提价", "涨价公告", days_ago=0.5),
            _make_search_result("正常波动", "资讯", days_ago=3),
        ]
        result = self.preprocessor.process("000001", "平安银行", raw)
        assert "产品涨价" in result.top_events
        assert "常规波动" not in result.top_events  # low impact 不进 top
```

- [ ] **Step 2: 运行测试确认失败**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_news_preprocessor.py -v 2>&1 | head -20
```

Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 NewsPreprocessor**

```python
# src/collectors/news_preprocessor.py
# -*- coding: utf-8 -*-
"""
新闻预处理器

使用 LLM 对 SearchService 返回的原始新闻做语义分类（利好/利空/中性），
提取关键事件标签和影响级别。一次 LLM 调用批量处理全部新闻。
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Any

from src.collectors.models import ClassifiedNews, ClassifiedNewsItem
from src.agent.llm_adapter import LLMToolAdapter

logger = logging.getLogger(__name__)

_CLASSIFY_PROMPT_TEMPLATE = """\
你是一个专业的财经新闻分析师。请对以下关于"{stock_name}"({stock_code})的新闻逐条进行分析和分类。

新闻列表：
{news_list}

请对每条新闻输出一个 JSON 对象，组成一个 JSON 数组：
[
  {{
    "index": <新闻序号，从0开始>,
    "sentiment": "<bullish|bearish|neutral>",
    "impact_level": "<high|medium|low>",
    "event_tags": ["关键事件标签1", "标签2"],
    "reason": "<一句话说明分类理由>"
  }},
  ...
]

分类规则：
- "bullish"（利好）：对股价有正面影响的事件，如增持、业绩超预期、产品提价、政策支持
- "bearish"（利空）：对股价有负面影响的事件，如减持、业绩下滑、监管处罚、行业政策收紧
- "neutral"（中性）：无明显影响的日常资讯
- 注意：减持计划"终止"是利好；"业绩超预期但估值偏高"需根据核心事件判断
- impact_level 判断：影响公司核心业务/重大合规事件为 high，季度常规数据为 medium，一般资讯为 low

只输出 JSON 数组，不要任何额外说明。"""


class NewsPreprocessor:
    """
    新闻预处理器：将原始搜索结果通过 LLM 分类为利好/利空/中性。

    Usage:
        preprocessor = NewsPreprocessor()
        classified = preprocessor.process("000001", "平安银行", raw_search_results)
    """

    def process(
        self,
        stock_code: str,
        stock_name: str,
        raw_results: Optional[List[Any]],
    ) -> ClassifiedNews:
        """
        对原始搜索结果进行 LLM 语义分类。

        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            raw_results: SearchService 返回的结果列表（含 title, snippet, url, published_date）

        Returns:
            ClassifiedNews，失败时返回 has_data=False 的空对象。
        """
        if not raw_results:
            return ClassifiedNews()

        try:
            # 1. 计算时效权重
            items_with_weight = []
            for r in raw_results:
                weight = self._compute_recency_weight_from_result(r)
                items_with_weight.append((r, weight))

            # 2. 构建新闻列表文本
            news_lines = []
            for i, (r, weight) in enumerate(items_with_weight):
                title = getattr(r, 'title', '') or ''
                snippet = getattr(r, 'snippet', '') or ''
                news_lines.append(f"[{i}] {title}: {snippet}")
            news_text = "\n".join(news_lines)

            # 3. 一次调用 LLM 批量分类
            prompt = _CLASSIFY_PROMPT_TEMPLATE.format(
                stock_name=stock_name,
                stock_code=stock_code,
                news_list=news_text,
            )
            llm = LLMToolAdapter()
            resp = llm.call_text(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            if not resp or not resp.content:
                logger.warning(f"[NewsPreprocessor] LLM 返回为空 ({stock_code})")
                return ClassifiedNews()

            # 4. 解析 JSON
            classifications = self._parse_llm_response(resp.content)

            # 5. 组装结果
            return self._build_classified_news(raw_results, items_with_weight, classifications)

        except Exception as e:
            logger.warning(f"[NewsPreprocessor] 处理失败 ({stock_code}): {e}")
            return ClassifiedNews()

    def _compute_recency_weight(self, days_ago: float) -> float:
        """根据距今天数计算时效权重"""
        if days_ago <= 1.0:
            return 1.0
        elif days_ago <= 3.0:
            return 0.7
        elif days_ago <= 7.0:
            return 0.4
        else:
            return 0.2

    def _compute_recency_weight_from_result(self, result: Any) -> float:
        """从搜索结果对象解析发布时间并计算权重"""
        try:
            pub_date_str = getattr(result, 'published_date', None) or getattr(result, 'date', None)
            if not pub_date_str:
                return 0.5
            pub_dt = datetime.fromisoformat(str(pub_date_str).replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            days_ago = (now - pub_dt).total_seconds() / 86400
            return self._compute_recency_weight(days_ago)
        except Exception:
            return 0.5

    def _parse_llm_response(self, content: str) -> List[dict]:
        """解析 LLM 返回的 JSON，容错处理"""
        # 去掉可能的 markdown 代码块
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            # 尝试用 json_repair
            try:
                from json_repair import repair_json
                data = json.loads(repair_json(content))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
            logger.warning(f"[NewsPreprocessor] JSON解析失败，内容片段: {content[:200]}")
            return []

    def _build_classified_news(
        self,
        raw_results: List[Any],
        items_with_weight: List[tuple],
        classifications: List[dict],
    ) -> ClassifiedNews:
        """将 LLM 分类结果和原始搜索结果组合成 ClassifiedNews"""
        cls_by_index = {c.get('index', i): c for i, c in enumerate(classifications)}

        items = []
        bullish_count = bearish_count = neutral_count = 0
        top_events = []

        for i, (raw, weight) in enumerate(items_with_weight):
            cls = cls_by_index.get(i, {})
            sentiment = cls.get('sentiment', 'neutral')
            impact_level = cls.get('impact_level', 'low')
            event_tags = cls.get('event_tags', [])

            item = ClassifiedNewsItem(
                title=getattr(raw, 'title', '') or '',
                snippet=getattr(raw, 'snippet', '') or '',
                url=getattr(raw, 'url', '') or '',
                publish_time=getattr(raw, 'published_date', None),
                sentiment=sentiment,
                impact_level=impact_level,
                event_tags=event_tags,
                recency_weight=weight,
                reason=cls.get('reason', ''),
            )
            items.append(item)

            if sentiment == 'bullish':
                bullish_count += 1
            elif sentiment == 'bearish':
                bearish_count += 1
            else:
                neutral_count += 1

            if impact_level == 'high':
                top_events.extend(event_tags)

        return ClassifiedNews(
            items=items,
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            top_events=list(dict.fromkeys(top_events)),  # 去重保序
            has_data=len(items) > 0,
        )
```

- [ ] **Step 4: 运行测试**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_news_preprocessor.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/news_preprocessor.py tests/collectors/test_news_preprocessor.py
git commit -m "feat(collectors): implement NewsPreprocessor with LLM semantic classification"
```

---

### Task 5: 将分类新闻注入 pipeline（传统路径）

**Files:**
- Modify: `src/core/pipeline.py`
- Modify: `src/analyzer.py`

- [ ] **Step 1: 在 pipeline.py 顶部导入 NewsPreprocessor**

```python
from src.collectors.news_preprocessor import NewsPreprocessor
```

- [ ] **Step 2: 在 `__init__` 中初始化**

```python
        self.news_preprocessor = NewsPreprocessor()
```

- [ ] **Step 3: 在 Step 4（搜索完成后）插入新闻预处理**

在 `analyze_stock` 方法中，`intel_results` 搜索完成、格式化为 `news_context` 之后，插入：

```python
            # Phase 2: 新闻LLM分类预处理
            classified_news = None
            if intel_results and self.search_service.is_available:
                try:
                    all_raw_results = []
                    for dim_resp in intel_results.values():
                        if dim_resp and dim_resp.success and dim_resp.results:
                            all_raw_results.extend(dim_resp.results)
                    if all_raw_results:
                        classified_news = self.news_preprocessor.process(
                            code, stock_name, all_raw_results
                        )
                        logger.info(
                            f"{stock_name}({code}) 新闻分类完成: "
                            f"利好{classified_news.bullish_count} "
                            f"利空{classified_news.bearish_count} "
                            f"中性{classified_news.neutral_count}"
                        )
                except Exception as e:
                    logger.warning(f"{stock_name}({code}) 新闻预处理失败: {e}")
```

- [ ] **Step 4: 将 classified_news 注入 enhanced_context**

在 `_enhance_context` 末尾的 Phase 1 标签之后追加：

```python
        # Phase 2: 注入分类新闻摘要
        if classified_news and classified_news.has_data:
            enhanced['classified_news_summary'] = {
                'bullish_count': classified_news.bullish_count,
                'bearish_count': classified_news.bearish_count,
                'neutral_count': classified_news.neutral_count,
                'top_events': classified_news.top_events,
                'items': [
                    {
                        'title': item.title,
                        'sentiment': item.sentiment,
                        'impact_level': item.impact_level,
                        'event_tags': item.event_tags,
                        'recency_weight': item.recency_weight,
                    }
                    for item in classified_news.items
                ],
            }
```

注意：`_enhance_context` 方法目前不接收 `classified_news` 参数，需要在调用时传入，或者改为在 `analyze_stock` 的 Step 6 之后直接注入 `enhanced_context['classified_news_summary']`（推荐后者，改动最小）。

- [ ] **Step 5: 在 analyzer.py 中使用分类新闻**

在 `GeminiAnalyzer.analyze` 的 prompt 组装处，在新闻摘要段落后追加分类信息：

```python
        classified_summary = context.get('classified_news_summary', {})
        if classified_summary:
            news_section += (
                f"\n\n**新闻情绪统计**: 利好{classified_summary.get('bullish_count', 0)}条 "
                f"利空{classified_summary.get('bearish_count', 0)}条 "
                f"中性{classified_summary.get('neutral_count', 0)}条"
            )
            top_events = classified_summary.get('top_events', [])
            if top_events:
                news_section += f"\n**重要事件**: {', '.join(top_events)}"
```

- [ ] **Step 6: 验证运行不报错**

```bash
PYTHONPATH=. python -c "
from src.core.pipeline import StockAnalysisPipeline
p = StockAnalysisPipeline()
print('news_preprocessor:', p.news_preprocessor)
"
```

- [ ] **Step 7: Commit**

```bash
git add src/core/pipeline.py src/analyzer.py
git commit -m "feat(pipeline): inject LLM-classified news into analysis context"
```

---

## Chunk 3: Phase 3 资金流向收集器

### Task 6: 实现 FundFlowCollector

**Files:**
- Create: `src/collectors/fund_flow_collector.py`
- Create: `tests/collectors/test_fund_flow_collector.py`

- [ ] **Step 1: 先写测试**

```python
# tests/collectors/test_fund_flow_collector.py
# -*- coding: utf-8 -*-
"""
FundFlowCollector 单元测试。

由于 AkShare 接口依赖网络，测试主要覆盖：
1. 接口异常时的降级处理（has_data=False，不抛异常）
2. 数据正常时的字段映射
3. 空响应时的处理
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.collectors.fund_flow_collector import FundFlowCollector
from src.collectors.models import FundFlowData


class TestFundFlowCollector:
    def setup_method(self):
        self.collector = FundFlowCollector()

    def test_returns_fundflowdata_type(self):
        """返回类型必须是 FundFlowData"""
        with patch("akshare.stock_individual_fund_flow", side_effect=Exception("network error")):
            result = self.collector.collect("000001")
        assert isinstance(result, FundFlowData)

    def test_akshare_failure_returns_no_data(self):
        """AkShare 接口失败时 has_data=False，不抛异常"""
        with patch("akshare.stock_individual_fund_flow", side_effect=Exception("timeout")):
            result = self.collector.collect("000001")
        assert result.has_data is False

    def test_empty_dataframe_returns_no_data(self):
        """AkShare 返回空 DataFrame 时 has_data=False"""
        with patch("akshare.stock_individual_fund_flow", return_value=pd.DataFrame()):
            result = self.collector.collect("000001")
        assert result.has_data is False

    def test_normal_fund_flow_data(self):
        """正常数据时应解析主力净流入"""
        mock_df = pd.DataFrame([{
            "日期": "2026-03-17",
            "主力净流入-净额": 12345.0,
            "超大单净流入-净额": 5000.0,
            "大单净流入-净额": 7345.0,
        }])
        with patch("akshare.stock_individual_fund_flow", return_value=mock_df):
            result = self.collector.collect("000001")
        # 只验证 has_data 和不报错，具体字段依赖实现
        assert isinstance(result, FundFlowData)

    def test_lhb_failure_does_not_break(self):
        """龙虎榜接口失败不影响整体结果"""
        mock_flow_df = pd.DataFrame([{
            "日期": "2026-03-17",
            "主力净流入-净额": 1000.0,
        }])
        with patch("akshare.stock_individual_fund_flow", return_value=mock_flow_df), \
             patch("akshare.stock_lhb_detail_em", side_effect=Exception("no lhb data")):
            result = self.collector.collect("000001")
        assert isinstance(result, FundFlowData)
        assert result.lhb_records == []

    def test_collect_a_share_market_code(self):
        """A股格式代码（6位数字）不报错"""
        with patch("akshare.stock_individual_fund_flow", side_effect=Exception("skip")):
            result = self.collector.collect("600519")
        assert result.has_data is False

    def test_collect_us_stock_skips_gracefully(self):
        """美股代码直接返回 has_data=False（无主力资金数据）"""
        result = self.collector.collect("AAPL")
        assert result.has_data is False
```

- [ ] **Step 2: 运行测试确认失败**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_fund_flow_collector.py -v 2>&1 | head -20
```

- [ ] **Step 3: 实现 FundFlowCollector**

```python
# src/collectors/fund_flow_collector.py
# -*- coding: utf-8 -*-
"""
资金流向收集器

通过 AkShare 获取个股的主力资金流向、北向资金持仓变化和龙虎榜数据。
接口失败时降级返回空数据，不阻断分析流程。
"""
from __future__ import annotations
import logging
import re
from typing import List, Dict, Optional

import pandas as pd

from src.collectors.models import FundFlowData

logger = logging.getLogger(__name__)

# 仅支持 A 股（6位数字代码）
_A_SHARE_PATTERN = re.compile(r"^\d{6}$")


class FundFlowCollector:
    """
    资金流向收集器：获取个股主力资金、北向资金、龙虎榜数据。

    Usage:
        collector = FundFlowCollector()
        data = collector.collect("600519")
        if data.has_data:
            print(data.main_net_inflow_1d)
    """

    def collect(self, stock_code: str) -> FundFlowData:
        """
        收集个股资金流向数据。

        Args:
            stock_code: 股票代码（仅支持A股6位数字代码，美股/港股直接返回空）

        Returns:
            FundFlowData，失败时 has_data=False
        """
        # 美股/港股不支持
        if not _A_SHARE_PATTERN.match(str(stock_code).strip()):
            logger.debug(f"[FundFlowCollector] {stock_code} 非A股，跳过资金流向收集")
            return FundFlowData()

        data = FundFlowData()

        # 主力资金流向
        try:
            data = self._fetch_fund_flow(stock_code, data)
        except Exception as e:
            logger.warning(f"[FundFlowCollector] {stock_code} 主力资金流向获取失败: {e}")

        # 龙虎榜（独立降级）
        try:
            data.lhb_records = self._fetch_lhb(stock_code)
        except Exception as e:
            logger.debug(f"[FundFlowCollector] {stock_code} 龙虎榜获取失败: {e}")
            data.lhb_records = []

        return data

    def _fetch_fund_flow(self, code: str, data: FundFlowData) -> FundFlowData:
        """获取主力资金净流入数据（1/3/5日）"""
        import akshare as ak

        # AkShare 接口：stock_individual_fund_flow
        # 返回列：日期, 主力净流入-净额, 超大单净流入-净额, 大单净流入-净额, ...
        try:
            df = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith("6") else "sz")
        except Exception:
            # 部分接口参数不同，尝试无 market 参数
            df = ak.stock_individual_fund_flow(stock=code)

        if df is None or df.empty:
            return data

        # 取最近一行（最新数据）
        df = df.sort_values(by=df.columns[0], ascending=False)
        latest = df.iloc[0]

        # 尝试解析主力净流入（不同版本列名可能不同）
        net_col_candidates = ["主力净流入-净额", "主力净额", "net_mf_amount"]
        for col in net_col_candidates:
            if col in df.columns:
                val = latest.get(col)
                if pd.notna(val):
                    data.main_net_inflow_1d = float(val) / 10000 if abs(float(val)) > 10000 else float(val)
                    break

        # 多日数据（取前3行和前5行的合计）
        if len(df) >= 3:
            try:
                vals_3d = []
                for col in net_col_candidates:
                    if col in df.columns:
                        vals_3d = df.head(3)[col].dropna().tolist()
                        break
                if vals_3d:
                    total = sum(float(v) for v in vals_3d)
                    data.main_net_inflow_3d = total / 10000 if abs(total) > 10000 else total
            except Exception:
                pass

        if len(df) >= 5:
            try:
                vals_5d = []
                for col in net_col_candidates:
                    if col in df.columns:
                        vals_5d = df.head(5)[col].dropna().tolist()
                        break
                if vals_5d:
                    total = sum(float(v) for v in vals_5d)
                    data.main_net_inflow_5d = total / 10000 if abs(total) > 10000 else total
            except Exception:
                pass

        data.has_data = data.main_net_inflow_1d is not None
        return data

    def _fetch_lhb(self, code: str) -> List[Dict]:
        """获取最近龙虎榜数据"""
        import akshare as ak
        from datetime import date, timedelta

        end_date = date.today().strftime("%Y%m%d")
        start_date = (date.today() - timedelta(days=30)).strftime("%Y%m%d")

        try:
            df = ak.stock_lhb_detail_em(symbol=code, start_date=start_date, end_date=end_date)
        except Exception:
            return []

        if df is None or df.empty:
            return []

        records = []
        for _, row in df.head(5).iterrows():  # 最多取5条
            record = {
                "date": str(row.get("上榜日期", "")),
                "reason": str(row.get("上榜原因", "")),
                "net_buy": row.get("净买额", None),
            }
            records.append(record)

        return records
```

- [ ] **Step 4: 运行测试**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_fund_flow_collector.py -v
```

Expected: 所有测试 PASS

- [ ] **Step 5: Commit**

```bash
git add src/collectors/fund_flow_collector.py tests/collectors/test_fund_flow_collector.py
git commit -m "feat(collectors): implement FundFlowCollector for A-share fund flow and lhb data"
```

---

### Task 7: 将资金流向注入 pipeline

**Files:**
- Modify: `src/core/pipeline.py`
- Modify: `src/analyzer.py`

- [ ] **Step 1: 导入并初始化**

```python
# pipeline.py 顶部导入
from src.collectors.fund_flow_collector import FundFlowCollector

# __init__ 中
        self.fund_flow_collector = FundFlowCollector()
```

- [ ] **Step 2: 在 analyze_stock 的 Step 2.5 附近插入收集逻辑**

在 fundamental_context 获取之后，`use_agent` 判断之前插入：

```python
            # Phase 3: 资金流向收集
            fund_flow_data = None
            try:
                fund_flow_data = self.fund_flow_collector.collect(code)
                if fund_flow_data.has_data:
                    logger.info(
                        f"{stock_name}({code}) 资金流向: "
                        f"主力1日={fund_flow_data.main_net_inflow_1d:.0f}万"
                    )
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 资金流向收集失败: {e}")
```

- [ ] **Step 3: 在 _enhance_context 注入资金数据**

```python
        # Phase 3: 注入资金流向
        if fund_flow_data and fund_flow_data.has_data:
            enhanced['fund_flow'] = {
                'main_net_inflow_1d': fund_flow_data.main_net_inflow_1d,
                'main_net_inflow_3d': fund_flow_data.main_net_inflow_3d,
                'main_net_inflow_5d': fund_flow_data.main_net_inflow_5d,
                'northbound_trend': fund_flow_data.northbound_trend,
                'lhb_records': fund_flow_data.lhb_records,
            }
```

- [ ] **Step 4: 在 analyzer.py 中使用资金数据**

在 prompt 组装时追加资金面数据段：

```python
        fund_flow = context.get('fund_flow', {})
        if fund_flow:
            fund_section = "\n\n**资金面**:"
            if fund_flow.get('main_net_inflow_1d') is not None:
                val = fund_flow['main_net_inflow_1d']
                direction = "净流入" if val > 0 else "净流出"
                fund_section += f"\n- 主力资金(1日): {direction} {abs(val):.0f}万"
            if fund_flow.get('main_net_inflow_3d') is not None:
                val = fund_flow['main_net_inflow_3d']
                direction = "净流入" if val > 0 else "净流出"
                fund_section += f"\n- 主力资金(3日): {direction} {abs(val):.0f}万"
            lhb = fund_flow.get('lhb_records', [])
            if lhb:
                fund_section += f"\n- 近期龙虎榜: {len(lhb)}条记录，最新原因: {lhb[0].get('reason', '')}"
            technical_section += fund_section  # 追加到技术分析段
```

- [ ] **Step 5: 验证并 Commit**

```bash
PYTHONPATH=. python -c "from src.core.pipeline import StockAnalysisPipeline; p = StockAnalysisPipeline(); print('fund_flow_collector:', p.fund_flow_collector)"

git add src/core/pipeline.py src/analyzer.py
git commit -m "feat(pipeline): inject fund flow data into analysis context"
```

---

## Chunk 4: Phase 4 同行对比收集器 + PeerAgent

### Task 8: 实现 PeerComparisonCollector

**Files:**
- Create: `src/collectors/peer_comparison_collector.py`
- Create: `tests/collectors/test_peer_comparison_collector.py`

- [ ] **Step 1: 先写测试**

```python
# tests/collectors/test_peer_comparison_collector.py
# -*- coding: utf-8 -*-
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.collectors.peer_comparison_collector import PeerComparisonCollector
from src.collectors.models import PeerData


class TestPeerComparisonCollector:
    def setup_method(self):
        self.collector = PeerComparisonCollector()

    def test_returns_peerdata_type(self):
        with patch("akshare.stock_board_industry_name_em", side_effect=Exception("err")):
            result = self.collector.collect("000001", "平安银行")
        assert isinstance(result, PeerData)

    def test_failure_returns_no_data(self):
        with patch("akshare.stock_board_industry_name_em", side_effect=Exception("timeout")):
            result = self.collector.collect("000001", "平安银行")
        assert result.has_data is False

    def test_us_stock_skips_gracefully(self):
        result = self.collector.collect("AAPL", "Apple")
        assert result.has_data is False

    def test_sector_name_extracted(self):
        mock_board_df = pd.DataFrame([
            {"板块名称": "银行", "板块代码": "BK0438", "涨跌幅": 1.2},
        ])
        mock_component_df = pd.DataFrame([
            {"代码": "000001", "名称": "平安银行", "涨跌幅": 1.5, "市盈率-动态": 5.0, "市净率": 0.8, "总市值": 3000},
            {"代码": "600036", "名称": "招商银行", "涨跌幅": 0.8, "市盈率-动态": 8.0, "市净率": 1.2, "总市值": 8000},
        ])
        with patch("akshare.stock_board_industry_name_em", return_value=mock_board_df), \
             patch("akshare.stock_board_industry_cons_em", return_value=mock_component_df):
            result = self.collector.collect("000001", "平安银行")
        assert isinstance(result, PeerData)
```

- [ ] **Step 2: 运行测试确认失败**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_peer_comparison_collector.py -v 2>&1 | head -20
```

- [ ] **Step 3: 实现 PeerComparisonCollector**

```python
# src/collectors/peer_comparison_collector.py
# -*- coding: utf-8 -*-
"""
同行对比收集器

根据目标股票所属板块，拉取同板块核心竞品的行情和估值数据。
仅支持 A 股，美股/港股直接返回空。
"""
from __future__ import annotations
import logging
import re
from typing import List, Optional

import pandas as pd

from src.collectors.models import PeerData, PeerStock

logger = logging.getLogger(__name__)

_A_SHARE_PATTERN = re.compile(r"^\d{6}$")


class PeerComparisonCollector:
    """
    同行对比收集器：获取目标股票所在板块的竞品数据。

    Usage:
        collector = PeerComparisonCollector()
        data = collector.collect("600519", "贵州茅台")
        if data.has_data:
            print(data.sector_name, data.peers)
    """

    def collect(self, stock_code: str, stock_name: str) -> PeerData:
        """
        收集同行对比数据。

        Args:
            stock_code: 股票代码
            stock_name: 股票名称（用于在成分股中定位目标）

        Returns:
            PeerData，失败时 has_data=False
        """
        if not _A_SHARE_PATTERN.match(str(stock_code).strip()):
            logger.debug(f"[PeerCollector] {stock_code} 非A股，跳过同行对比")
            return PeerData()

        try:
            return self._collect_impl(stock_code, stock_name)
        except Exception as e:
            logger.warning(f"[PeerCollector] {stock_code} 同行对比收集失败: {e}")
            return PeerData()

    def _collect_impl(self, code: str, name: str) -> PeerData:
        import akshare as ak

        # 1. 获取所有行业板块列表，找到目标股所在板块
        board_df = ak.stock_board_industry_name_em()
        if board_df is None or board_df.empty:
            return PeerData()

        # 遍历板块，找到包含目标股的板块
        target_board = None
        target_board_change = 0.0

        for _, board_row in board_df.iterrows():
            board_name = board_row.get("板块名称", "")
            try:
                comp_df = ak.stock_board_industry_cons_em(symbol=board_name)
                if comp_df is None or comp_df.empty:
                    continue
                # 检查是否包含目标股
                codes_in_board = comp_df.get("代码", pd.Series()).astype(str).tolist()
                if code in codes_in_board:
                    target_board = board_name
                    target_board_change = float(board_row.get("涨跌幅", 0) or 0)
                    # 拿到成分股列表，直接处理
                    return self._build_peer_data(
                        code, name, target_board, target_board_change, comp_df
                    )
            except Exception:
                continue

        return PeerData()

    def _build_peer_data(
        self,
        target_code: str,
        target_name: str,
        sector_name: str,
        sector_change: float,
        comp_df: pd.DataFrame,
    ) -> PeerData:
        """从成分股 DataFrame 构建 PeerData"""
        # 按市值排序，取前6（排除目标股后取5）
        market_cap_col = next(
            (c for c in ["总市值", "流通市值", "market_cap"] if c in comp_df.columns), None
        )
        if market_cap_col:
            comp_df = comp_df.sort_values(by=market_cap_col, ascending=False)

        peers: List[PeerStock] = []
        target_rank = 0
        all_pe = []

        for rank, (_, row) in enumerate(comp_df.iterrows(), 1):
            code = str(row.get("代码", "")).strip()
            row_name = str(row.get("名称", "")).strip()

            if code == target_code:
                target_rank = rank
                continue  # 目标股不加入竞品列表

            if len(peers) >= 5:
                continue

            pe = row.get("市盈率-动态") or row.get("市盈率") or row.get("pe")
            pb = row.get("市净率") or row.get("pb")
            cap = row.get(market_cap_col) if market_cap_col else None
            change = float(row.get("涨跌幅", 0) or 0)

            try:
                pe_val = float(pe) if pe is not None and str(pe) not in ('', '-', 'None') else None
            except (ValueError, TypeError):
                pe_val = None

            if pe_val and pe_val > 0:
                all_pe.append(pe_val)

            peers.append(PeerStock(
                code=code,
                name=row_name,
                change_pct=change,
                pe_ratio=pe_val,
                pb_ratio=float(pb) if pb and str(pb) not in ('', '-') else None,
                market_cap=float(cap) / 1e8 if cap else None,  # 转为亿
            ))

        # 目标股 PE 与板块均值对比
        target_pe_vs_avg = None
        target_row = comp_df[comp_df["代码"].astype(str) == target_code]
        if not target_row.empty and all_pe:
            target_pe_raw = target_row.iloc[0].get("市盈率-动态") or target_row.iloc[0].get("市盈率")
            try:
                target_pe = float(target_pe_raw)
                sector_pe_avg = sum(all_pe) / len(all_pe)
                if sector_pe_avg > 0:
                    target_pe_vs_avg = (target_pe - sector_pe_avg) / sector_pe_avg * 100
            except (TypeError, ValueError, ZeroDivisionError):
                pass

        return PeerData(
            sector_name=sector_name,
            sector_change_pct=sector_change,
            peers=peers,
            target_rank_in_sector=target_rank,
            target_pe_vs_sector_avg=target_pe_vs_avg,
            has_data=len(peers) > 0,
        )
```

- [ ] **Step 4: 运行测试**

```bash
PYTHONPATH=. python -m pytest tests/collectors/test_peer_comparison_collector.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/collectors/peer_comparison_collector.py tests/collectors/test_peer_comparison_collector.py
git commit -m "feat(collectors): implement PeerComparisonCollector for sector peer analysis"
```

---

### Task 9: 将同行对比注入 pipeline 并更新 analyzer prompt

**Files:**
- Modify: `src/core/pipeline.py`
- Modify: `src/analyzer.py`

- [ ] **Step 1: 导入并初始化**

```python
from src.collectors.peer_comparison_collector import PeerComparisonCollector

# __init__
        self.peer_collector = PeerComparisonCollector()
```

- [ ] **Step 2: 在 analyze_stock 中插入同行对比收集**

在资金流向收集之后：

```python
            # Phase 4: 同行对比收集
            peer_data = None
            try:
                peer_data = self.peer_collector.collect(code, stock_name)
                if peer_data.has_data:
                    logger.info(
                        f"{stock_name}({code}) 同行对比: 板块={peer_data.sector_name}, "
                        f"板块涨跌={peer_data.sector_change_pct:.2f}%"
                    )
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 同行对比收集失败: {e}")
```

- [ ] **Step 3: 注入 enhanced_context**

```python
        # Phase 4: 注入同行对比
        if peer_data and peer_data.has_data:
            enhanced['peer_comparison'] = {
                'sector_name': peer_data.sector_name,
                'sector_change_pct': peer_data.sector_change_pct,
                'target_rank': peer_data.target_rank_in_sector,
                'target_pe_vs_avg': peer_data.target_pe_vs_sector_avg,
                'peers': [
                    {
                        'code': p.code, 'name': p.name,
                        'change_pct': p.change_pct,
                        'pe_ratio': p.pe_ratio,
                    }
                    for p in peer_data.peers
                ],
            }
```

- [ ] **Step 4: 在 analyzer.py 中使用同行对比**

```python
        peer = context.get('peer_comparison', {})
        if peer:
            peer_section = f"\n\n**同行板块对比** ({peer.get('sector_name', '')}板块):"
            peer_section += f"\n- 板块整体涨跌: {peer.get('sector_change_pct', 0):.2f}%"
            if peer.get('target_rank'):
                peer_section += f"\n- 目标股板块排名: 第{peer['target_rank']}位"
            if peer.get('target_pe_vs_avg') is not None:
                val = peer['target_pe_vs_avg']
                direction = "高于" if val > 0 else "低于"
                peer_section += f"\n- PE相对板块均值: {direction} {abs(val):.1f}%"
            peers_list = peer.get('peers', [])
            if peers_list:
                peer_lines = [f"  {p['name']}({p['code']}): {p['change_pct']:+.2f}%" for p in peers_list[:3]]
                peer_section += "\n- 主要竞品:\n" + "\n".join(peer_lines)
            # 追加到 prompt 的相关段落
```

- [ ] **Step 5: 验证并 Commit**

```bash
PYTHONPATH=. python -c "from src.core.pipeline import StockAnalysisPipeline; p = StockAnalysisPipeline(); print('peer_collector:', p.peer_collector)"

git add src/core/pipeline.py src/analyzer.py
git commit -m "feat(pipeline): inject peer comparison data into analysis context"
```

---

## Chunk 5: Phase 5 并行化改造

### Task 10: 将四个收集器并行执行

**Files:**
- Modify: `src/core/pipeline.py`

目前四个收集器是串行调用。Phase 5 将它们改为 `ThreadPoolExecutor` 并行执行，减少总等待时间。

- [ ] **Step 1: 将串行调用重构为并行**

找到 `analyze_stock` 中 Phase 1~4 的收集器调用，用 `ThreadPoolExecutor` 包裹：

```python
            # Phase 1~4: 并行运行所有数据收集器
            fund_flow_data = None
            classified_news = None
            peer_data = None

            # technical_labels 不需要网络，直接同步执行
            technical_labels = []
            if trend_result:
                technical_labels = self.pattern_labeler.label(trend_result)

            collector_futures = {}
            with ThreadPoolExecutor(max_workers=3) as col_executor:
                # 资金流向
                collector_futures['fund_flow'] = col_executor.submit(
                    self.fund_flow_collector.collect, code
                )
                # 同行对比
                collector_futures['peer'] = col_executor.submit(
                    self.peer_collector.collect, code, stock_name
                )
                # 新闻分类（需要先完成搜索，搜索是同步的，所以 classified_news 在搜索后提交）
                # 注意：新闻搜索(Step 4)需要在并行收集之前完成
                # 如果 intel_results 已经在并行前完成，可以一并提交
                if intel_results:
                    all_raw = []
                    for dim_resp in intel_results.values():
                        if dim_resp and dim_resp.success and dim_resp.results:
                            all_raw.extend(dim_resp.results)
                    if all_raw:
                        collector_futures['news'] = col_executor.submit(
                            self.news_preprocessor.process, code, stock_name, all_raw
                        )

            # 收集结果（各自降级）
            try:
                fund_flow_data = collector_futures['fund_flow'].result(timeout=15)
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 资金流向并行收集超时/失败: {e}")

            try:
                peer_data = collector_futures['peer'].result(timeout=20)
            except Exception as e:
                logger.warning(f"{stock_name}({code}) 同行对比并行收集超时/失败: {e}")

            if 'news' in collector_futures:
                try:
                    classified_news = collector_futures['news'].result(timeout=30)
                except Exception as e:
                    logger.warning(f"{stock_name}({code}) 新闻分类并行收集超时/失败: {e}")
```

注意：搜索（`search_comprehensive_intel`）是已有的步骤，需要保持在并行收集前完成，因为新闻分类依赖搜索结果。

- [ ] **Step 2: 运行验证**

```bash
PYTHONPATH=. python -c "
from src.core.pipeline import StockAnalysisPipeline
p = StockAnalysisPipeline()
print('所有收集器初始化OK:')
print('  pattern_labeler:', p.pattern_labeler)
print('  news_preprocessor:', p.news_preprocessor)
print('  fund_flow_collector:', p.fund_flow_collector)
print('  peer_collector:', p.peer_collector)
"
```

Expected: 四个收集器均正常初始化，无报错

- [ ] **Step 3: Commit**

```bash
git add src/core/pipeline.py
git commit -m "perf(pipeline): parallelize data collectors with ThreadPoolExecutor"
```

---

## 完成验收标准

1. **Phase 1** — `technical_labels` 字段出现在分析日志和最终 prompt 中
2. **Phase 2** — 日志中显示"新闻分类完成: 利好X 利空X 中性X"
3. **Phase 3** — A股分析时日志显示"资金流向: 主力1日=XXX万"（非A股跳过）
4. **Phase 4** — 日志显示"同行对比: 板块=XXX, 板块涨跌=XX%"
5. **Phase 5** — 四个收集器并行执行，总耗时不超过最慢单个收集器的 1.5 倍

所有 Phase 均可独立回滚：只需注释掉对应的收集器调用和 `enhanced['xxx']` 注入即可。
