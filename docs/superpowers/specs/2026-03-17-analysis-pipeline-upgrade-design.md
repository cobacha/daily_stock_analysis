# 分析流程深度升级设计文档

> **日期:** 2026-03-17
> **状态:** Draft
> **目标:** 从数据质量、策略深度、Agent架构三个维度全面升级股票分析流程

---

## 1. 背景与现状

### 1.1 当前架构

系统已拥有成熟的基础分析管线：

| 层级 | 现状 | 成熟度 |
|------|------|--------|
| 数据抓取 | AkShare/EFinance/YFinance 多源适配 | 中等，部分接口已失效 |
| 搜索服务 | Bocha/Tavily/Brave 多引擎+故障转移 | 较高 |
| 量化指标 | K线趋势(MA/MACD/RSI)、筹码分布、买卖点位计算 | 基础 |
| LLM分析 | GeminiAnalyzer 单Agent，结构化JSON输出 | 中等 |
| Agent架构 | Orchestrator/TechnicalAgent/IntelAgent/DecisionAgent 骨架存在 | 早期 |

### 1.2 核心痛点

1. **资金指标缺失**：北向资金接口已废弃（代码注释掉），无主力资金流向、龙虎榜深度解读
2. **新闻催化剂整合粗糙**：搜索结果平铺注入prompt，缺乏语义分类（利好/利空）、时效性加权、信源过滤
3. **无同行对比**：仅分析个股自身，无法体现板块相对强弱
4. **技术形态散落**：MACD/均线等指标的诊断结论分散在评分逻辑中，未形成人可读的标签
5. **Agent架构未打通**：pipeline.py 仍走老路径，未利用已有的 Agent 骨架

---

## 2. 架构决策

### 2.1 混合型架构

- **第一阶段 — 并行数据收集（纯代码，无LLM消耗）**：多个独立的数据收集器并行抓取量化数据、资金流向、同行数据
- **新闻预处理例外**：新闻分类使用 LLM 语义理解（非关键词匹配），以保证复杂语境的准确性
- **第二阶段 — 增强版Agent分析（LLM深度推理）**：将所有结构化数据注入已有的 Agent 骨架，由 DecisionAgent 做最终汇总

### 2.2 渐进式替换策略

保持 `pipeline.py` 入口不变，在内部逐步接入新的数据收集器和 Agent 增强。每个收集器独立开发/测试/上线，不影响现有功能。

---

## 3. 整体数据流

```
用户请求
   ↓
Pipeline (入口不变)
   ↓
┌──────────── 第一阶段：并行数据收集 ────────────┐
│                                                  │
│  ┌──────────────┐  ┌──────────────┐              │
│  │ FundFlow     │  │ NewsPreproc  │              │
│  │ Collector    │  │ essor (LLM)  │              │
│  │              │  │              │              │
│  │ · 北向资金    │  │ · 搜索聚合    │              │
│  │ · 主力净流入  │  │ · LLM语义分类 │              │
│  │ · 龙虎榜     │  │ · 时效加权    │              │
│  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                      │
│  ┌──────┴───────┐  ┌──────┴───────┐              │
│  │ PeerCompare  │  │ Technical   │              │
│  │ Collector    │  │ PatternLabel│              │
│  │              │  │ er          │              │
│  │ · 板块识别    │  │ · MACD形态   │              │
│  │ · 竞品拉取    │  │ · 均线排列   │              │
│  │ · 相对估值    │  │ · 量价背离   │              │
│  └──────┬───────┘  └──────┬───────┘              │
│         └────────┬────────┘                      │
│                  ↓                               │
│       EnrichedStockContext                       │
└──────────────────────────────────────────────────┘
                   ↓
┌──────────── 第二阶段：增强版Agent分析 ───────────┐
│                                                  │
│  TechnicalAgent ← 技术形态标签 + 资金数据        │
│  IntelAgent     ← 预处理后的分类新闻 + 催化剂    │
│  PeerAgent(新)  ← 同行对比数据                   │
│       ↓                                          │
│  DecisionAgent  ← 汇总所有Agent意见              │
└──────────────────────────────────────────────────┘
```

---

## 4. 数据收集器详细设计

### 4.1 `FundFlowCollector` — 资金流向收集器

**职责**：收集个股的资金面数据，包括主力资金流向、北向资金持仓变动和龙虎榜明细。

**数据源**：AkShare

| 数据项 | AkShare 接口 | 说明 |
|--------|-------------|------|
| 主力净流入 | `stock_individual_fund_flow` | 1日/3日/5日主力净流入额 |
| 北向资金 | `stock_hsgt_hist_em` 或替代接口 | 北向持仓变化趋势 |
| 龙虎榜 | `stock_lhb_detail_em` | 近期龙虎榜买卖席位、机构占比 |

**输出数据结构**：

```python
@dataclass
class FundFlowData:
    main_net_inflow_1d: Optional[float]   # 当日主力净流入(万元)
    main_net_inflow_3d: Optional[float]   # 3日主力净流入
    main_net_inflow_5d: Optional[float]   # 5日主力净流入
    northbound_change: Optional[float]    # 北向资金持仓变化(万股)
    northbound_trend: Optional[str]       # "持续流入"/"持续流出"/"震荡"
    lhb_records: List[Dict]              # 龙虎榜记录 [{date, reason, buy_seats, sell_seats, net_buy}]
    has_data: bool = False               # 是否成功获取到数据
```

**降级策略**：接口失败时 `has_data=False`，不阻断流程。

**文件位置**：`src/collectors/fund_flow_collector.py`

---

### 4.2 `NewsPreprocessor` — 新闻预处理器（LLM语义分类）

**职责**：将搜索服务返回的原始新闻结果进行语义理解、情感分类和结构化处理。

**处理流程**：

1. 接收 `SearchService` 返回的原始搜索结果
2. 按发布时间计算 `recency_weight`（24h内=1.0, 3天内=0.7, 7天内=0.4, 更早=0.2）
3. 去重（基于标题相似度 > 0.85 的合并）
4. **批量发送给 LLM** 进行语义分类（一次调用处理所有新闻）
5. 返回分类后的结构化新闻列表

**LLM分类Prompt设计**：

```
你是一个专业的财经新闻分析师。请对以下关于"{stock_name}"的新闻逐条进行分析和分类。

新闻列表：
{numbered_news_list}

请对每条新闻输出JSON：
{
  "index": 新闻序号,
  "sentiment": "bullish" | "bearish" | "neutral",
  "impact_level": "high" | "medium" | "low",
  "event_tags": ["关键事件标签1", "标签2"],
  "reason": "一句话说明分类理由"
}

注意：
- "减持计划终止"是利好，不是利空
- "业绩超预期但估值偏高"需综合判断
- 优先关注对股价有实质影响的事件
```

**输出数据结构**：

```python
@dataclass
class ClassifiedNewsItem:
    title: str
    snippet: str
    url: str
    publish_time: Optional[str]
    sentiment: str                # "bullish" / "bearish" / "neutral"
    impact_level: str             # "high" / "medium" / "low"
    event_tags: List[str]         # ["大股东增持", "产品涨价"]
    recency_weight: float         # 0.0 ~ 1.0
    reason: str                   # LLM给出的分类理由

@dataclass
class ClassifiedNews:
    items: List[ClassifiedNewsItem]
    bullish_count: int
    bearish_count: int
    neutral_count: int
    top_events: List[str]         # 高影响力事件标签汇总
    has_data: bool = False
```

**成本控制**：
- 一次 LLM 调用批量处理所有新闻（通常3~8条），不逐条调用
- 使用低温度 (temperature=0.1) 确保分类稳定
- 优先使用轻量模型 (如 gemini-2.0-flash)

**文件位置**：`src/collectors/news_preprocessor.py`

---

### 4.3 `PeerComparisonCollector` — 同行对比收集器

**职责**：根据目标股票所属板块，拉取同板块核心竞品的行情和估值数据，进行横向对比。

**处理流程**：

1. 识别目标股票所属行业板块（利用现有 `data_provider` 中的板块数据）
2. 拉取该板块成分股列表，选取市值前5的核心股
3. 获取每只竞品的基础数据（涨跌幅、PE、PB、市值）
4. 计算目标股在板块中的排名

**数据源**：AkShare 板块成分股接口 + 个股基本面接口

**输出数据结构**：

```python
@dataclass
class PeerStock:
    code: str
    name: str
    change_pct: float           # 涨跌幅
    pe_ratio: Optional[float]   # 市盈率
    pb_ratio: Optional[float]   # 市净率
    market_cap: Optional[float] # 总市值(亿)

@dataclass
class PeerData:
    sector_name: str                # 所属板块名称
    sector_change_pct: float        # 板块整体涨跌幅
    peers: List[PeerStock]          # 竞品列表(前5)
    target_rank_in_sector: int      # 目标股在板块中的涨跌幅排名
    target_pe_vs_sector_avg: Optional[float]  # PE相对板块均值的溢价率
    has_data: bool = False
```

**文件位置**：`src/collectors/peer_comparison_collector.py`

---

### 4.4 `TechnicalPatternLabeler` — 技术形态标签器

**职责**：将 `StockTrendAnalyzer` 输出的散落数值判断汇总为人可读的技术形态标签列表。

**处理逻辑**（纯计算，无LLM）：

| 判断条件 | 输出标签 |
|----------|---------|
| MA5 > MA10 > MA20 | "多头排列" |
| MA5 < MA10 < MA20 | "空头排列" |
| MACD DIF上穿DEA且在零轴上方 | "MACD零轴上金叉(强)" |
| MACD DIF上穿DEA且在零轴下方 | "MACD零轴下金叉(弱)" |
| RSI > 70 | "RSI超买({value})" |
| RSI < 30 | "RSI超卖({value})" |
| 当日成交量 < MA5成交量 * 0.7 且涨跌幅 < -1% | "缩量回调" |
| 当日成交量 > MA5成交量 * 1.5 且涨跌幅 > 2% | "放量突破" |
| 价格站上MA20且MA20拐头向上 | "站上20日均线" |
| 乖离率 > 5% | "短线乖离过大" |
| 收盘价创20日新高 | "创20日新高" |

**输出**：`List[str]`，如 `["多头排列", "MACD零轴上金叉(强)", "缩量回踩MA10"]`

**文件位置**：`src/collectors/technical_pattern_labeler.py`

---

## 5. `EnrichedStockContext` 数据包

```python
@dataclass
class EnrichedStockContext:
    """汇聚所有收集器产出的结构化上下文，传递给Agent层"""
    stock_code: str
    stock_name: str

    # 现有数据（不变）
    price_data: Dict              # 行情数据
    kline_data: Any               # K线 DataFrame
    trend_analysis: Dict          # 现有 StockTrendAnalyzer 结果
    search_results: List          # 原始搜索结果（保留兼容）

    # 新增数据
    fund_flow: FundFlowData               # 资金流向
    classified_news: ClassifiedNews       # LLM分类新闻
    peer_comparison: PeerData             # 同行对比
    technical_labels: List[str]           # 技术形态标签
```

**文件位置**：`src/collectors/models.py`

---

## 6. Agent层增强

### 6.1 现有Agent改动

**TechnicalAgent 增强**：
- Prompt增加 `fund_flow` 数据段："资金面：主力1日净流入{X}万，北向{trend}，近期龙虎榜{summary}"
- Prompt增加 `technical_labels` 段："技术形态：{labels}"
- 评判时有"资金面佐证"，不再仅基于K线

**IntelAgent 增强**：
- 将原来平铺的搜索结果替换为 `classified_news`
- Prompt按利好/利空/中性分区展示，每条注明影响级别和事件标签
- 要求输出时给出"催化剂强度评估"

### 6.2 新增Agent

**PeerAgent**：
- 输入：`PeerData`
- 职责：分析目标股相对板块的强弱（强于/弱于/同步板块）、估值是否合理（PE相对溢价）
- 输出Opinion字段：`peer_strength`(强/弱/同步)、`valuation_assessment`(偏高/合理/偏低)、`key_insight`(一句话总结)

### 6.3 DecisionAgent 权重调整

| Agent | 旧权重 | 新权重 |
|-------|--------|--------|
| TechnicalAgent | 40% | 30% |
| IntelAgent | 30% | 20% |
| RiskAgent | 30% | 15% |
| PeerAgent (新) | — | 15% |
| 资金面(融入Technical) | — | 20% |

---

## 7. Pipeline 集成方案

### 7.1 并行执行

在 `pipeline.py` 的 `_analyze_single_stock` 中，使用 `ThreadPoolExecutor` 并行运行四个收集器：

```python
with ThreadPoolExecutor(max_workers=4) as executor:
    fund_future = executor.submit(fund_flow_collector.collect, stock_code)
    news_future = executor.submit(news_preprocessor.process, stock_code, raw_search_results)
    peer_future = executor.submit(peer_collector.collect, stock_code)
    label_future = executor.submit(pattern_labeler.label, trend_analysis)

enriched_ctx = EnrichedStockContext(
    ...,
    fund_flow=fund_future.result(),
    classified_news=news_future.result(),
    peer_comparison=peer_future.result(),
    technical_labels=label_future.result(),
)
```

### 7.2 向后兼容

- `EnrichedStockContext` 中所有新增字段默认为空值
- 当收集器返回 `has_data=False` 时，对应的 Prompt 段落自动省略
- 现有的分析功能不受影响，新模块作为增量注入

---

## 8. 降级与容错原则

1. **每个收集器独立容错**：一个收集器失败不影响其他收集器和整体流程
2. **数据缺失时省略**：Agent prompt 中动态跳过无数据的段落
3. **超时控制**：每个收集器设置独立超时（默认10s），超时返回空数据
4. **日志追踪**：每个收集器记录执行耗时和数据获取状态

---

## 9. 渐进式上线计划

| 阶段 | 内容 | 影响面 | 预计复杂度 |
|------|------|--------|-----------|
| Phase 1 | `TechnicalPatternLabeler` + 注入现有prompt | 最小，纯计算逻辑 | 低 |
| Phase 2 | `NewsPreprocessor` (LLM分类) + 替换IntelAgent输入 | 中等，新增LLM调用 | 中 |
| Phase 3 | `FundFlowCollector` + 增强TechnicalAgent prompt | 中等，新数据源适配 | 中 |
| Phase 4 | `PeerComparisonCollector` + 新增PeerAgent | 较大，新Agent接入 | 中高 |
| Phase 5 | Pipeline并行化改造，四个收集器用ThreadPool并行 | 性能优化 | 低 |

每个阶段独立可测试、可上线、可回滚。
