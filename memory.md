# 记忆

## Bug Fixes

### Cache Bug (2026-03-18)
- **问题**: 前端刷新页面时，即使命中缓存也会重复触发分析。
- **原因**: `AnalysisService.analyze_stock` 在命中缓存后，创建 `StockAnalysisPipeline` 时硬编码了 `force_update=True`，导致 Pipeline 内部的缓存检查被跳过。
- **修复**: 修改 `src/services/analysis_service.py`，将 `force_update` 参数正确传递给 Pipeline。
- **测试**: 更新了 `tests/test_analysis_api_contract.py` 验证参数传递。

## Design Specs

### Analysis Pipeline Upgrade (2026-03-17)
- 设计文档: `docs/superpowers/specs/2026-03-17-analysis-pipeline-upgrade-design.md`
- 实现了:
  - `TechnicalPatternLabeler`: 将技术指标转换为标签
  - `NewsPreprocessor`: LLM新闻分类
  - `FundFlowCollector`: 资金流向数据
  - `PeerComparisonCollector`: 同行对比数据
  - Pipeline 并行化改造
