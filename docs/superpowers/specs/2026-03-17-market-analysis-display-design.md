# 大盘分析缓存 + 前端展示 + 年度走势 设计文档

**日期**: 2026-03-17
**状态**: 已批准

---

## 背景

用户需求：
1. 前端价格走势增加年度（1年）时间周期
2. 大盘分析结果做当日缓存，避免重复调用 LLM
3. 前端新增大盘分析展示（首页顶部横条 + 独立大盘页）

---

## 模块一：年度走势（前端）

### 变更文件
- `apps/dsa-web/src/components/report/ReportPriceHistory.tsx`
- `apps/dsa-web/src/api/stocks.ts`（调整 days 参数默认值）
- `api/v1/endpoints/stocks.py`（允许 days 最大值扩大到 365）

### 实现细节
- 新增 `'1y'` 周期，标签"年度"
- 前端请求历史数据时，有 1y 周期则传 `days=365`，否则沿用 180
- X 轴按月份显示（间隔约 30 条数据取一个刻度，格式 `MM月`）
- 统计数据：年初开盘、当前收盘、年内最高、年内最低、YTD 涨跌幅

---

## 模块二：大盘分析缓存（后端）

### 存储方案
复用 `AnalysisHistory` 表，无需新建表：
- `code = 'MARKET_CN'`（A股）
- `report_type = 'market_review'`
- `analysis_summary` 存 AI 复盘全文
- `raw_result` 存序列化的 MarketOverview JSON（indices、涨跌统计、板块榜等）

### 缓存逻辑
- 复用 `AnalysisRepository.get_post_close_cache(code, report_type)` 查当日缓存
- 命中缓存直接返回，跳过 LLM 调用
- `force_update=True` 时强制重跑

### 新增服务
`src/services/market_service.py`（新文件）：
- `get_or_create_market_review(region='cn', force_update=False) -> dict`
  - 查缓存 → 命中则返回
  - 未命中则调 `MarketAnalyzer` 生成复盘 → 保存到 `AnalysisHistory` → 返回

### 新增 API 端点
`api/v1/endpoints/market.py`（新文件）：
- `GET /api/v1/market/review?region=cn` → 返回当日大盘概览 + AI 复盘（自动触发生成）
- `POST /api/v1/market/review/refresh?region=cn` → 强制重跑

注册路由到 `api/app.py`。

### 响应结构
```json
{
  "date": "2026-03-17",
  "region": "cn",
  "cached": true,
  "indices": [
    {"code": "000001", "name": "上证指数", "current": 3287.5, "change": 26.1, "change_pct": 0.8}
  ],
  "up_count": 2341,
  "down_count": 1523,
  "flat_count": 136,
  "limit_up_count": 45,
  "limit_down_count": 3,
  "total_amount": 8234.5,
  "top_sectors": [{"name": "半导体", "change_pct": 3.2}],
  "bottom_sectors": [{"name": "地产", "change_pct": -1.5}],
  "review_text": "今日A股市场整体震荡上行……",
  "generated_at": "2026-03-17T16:30:00"
}
```

---

## 模块三：前端展示

### 3a. 首页顶部横条 `MarketTopBar.tsx`（新组件）
- 位置：`apps/dsa-web/src/components/market/MarketTopBar.tsx`
- 页面加载时请求 `GET /api/v1/market/review`
- 展示内容：上证 / 深证 / 创业板 涨跌幅 + 成交额 + AI 复盘一句话（截取前60字）
- 无缓存时显示骨架 loading，后台生成完成后自动刷新（轮询 3s，最多 60s）
- 集成到 `HomePage.tsx` 顶部

### 3b. 独立大盘分析页 `MarketPage.tsx`（新页面）
- 位置：`apps/dsa-web/src/pages/MarketPage.tsx`
- 路由：`/market`
- 导航菜单新增"大盘"入口
- 展示内容：
  - 主要指数卡片（带涨跌色）
  - 涨跌家数统计（涨停/跌停/上涨/下跌/平盘）
  - 板块涨幅榜 Top5 / 跌幅榜 Top5
  - AI 复盘全文（Markdown 渲染）
- 右上角"刷新复盘"按钮 → POST /refresh → 完成后重新 GET

### 3c. 前端 API 客户端
- 位置：`apps/dsa-web/src/api/market.ts`（新文件）
- `marketApi.getReview(region)` → GET
- `marketApi.refreshReview(region)` → POST

---

## 不在本次范围内
- 美股大盘（US region）展示（后端已支持，前端暂不实现）
- 大盘历史走势图（仅展示当日数据）
- 推送通知

---

## 测试要点
- 缓存命中：同一天第二次请求不重复调用 LLM
- force_update：POST /refresh 触发重新生成并更新缓存
- 年度走势：365天数据正确加载，X 轴月份标签正确
- 加载状态：首次生成时前端显示 loading 而非报错
