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
        # -> ["多头排列", "MACD零轴上金叉(强)", "缩量回调"]
    """

    def label(self, result: Optional[TrendAnalysisResult]) -> List[str]:
        if result is None:
            return []

        labels: List[str] = []
        labels.extend(self._trend_labels(result))
        labels.extend(self._macd_labels(result))
        labels.extend(self._rsi_labels(result))
        labels.extend(self._volume_labels(result))
        labels.extend(self._bias_labels(result))

        # 去重保序
        seen = set()
        unique = []
        for label in labels:
            if label not in seen:
                seen.add(label)
                unique.append(label)

        logger.debug(f"[PatternLabeler] {result.code} 形态标签: {unique}")
        return unique

    def _trend_labels(self, r: TrendAnalysisResult) -> List[str]:
        mapping = {
            TrendStatus.STRONG_BULL: "强势多头排列",
            TrendStatus.BULL: "多头排列",
            TrendStatus.WEAK_BULL: "弱势多头",
            TrendStatus.WEAK_BEAR: "弱势空头",
            TrendStatus.BEAR: "空头排列",
            TrendStatus.STRONG_BEAR: "强势空头排列",
            TrendStatus.CONSOLIDATION: "均线盘整",
        }
        label = mapping.get(r.trend_status)
        return [label] if label else []

    def _macd_labels(self, r: TrendAnalysisResult) -> List[str]:
        mapping = {
            MACDStatus.GOLDEN_CROSS_ZERO: "MACD零轴上金叉(强)",
            MACDStatus.GOLDEN_CROSS: "MACD金叉",
            MACDStatus.DEATH_CROSS: "MACD死叉",
            MACDStatus.BULLISH: "MACD多头",
            MACDStatus.BEARISH: "MACD空头",
            MACDStatus.CROSSING_UP: "MACD上穿零轴",
            MACDStatus.CROSSING_DOWN: "MACD下穿零轴",
        }
        label = mapping.get(r.macd_status)
        return [label] if label else []

    def _rsi_labels(self, r: TrendAnalysisResult) -> List[str]:
        rsi_val = round(r.rsi_6, 1)
        if r.rsi_status == RSIStatus.OVERBOUGHT:
            return [f"RSI超买({rsi_val})"]
        elif r.rsi_status == RSIStatus.OVERSOLD:
            return [f"RSI超卖({rsi_val})"]
        return []

    def _volume_labels(self, r: TrendAnalysisResult) -> List[str]:
        mapping = {
            VolumeStatus.HEAVY_VOLUME_UP: "放量上涨",
            VolumeStatus.HEAVY_VOLUME_DOWN: "放量下跌",
            VolumeStatus.SHRINK_VOLUME_UP: "缩量上涨",
            VolumeStatus.SHRINK_VOLUME_DOWN: "缩量回调",
        }
        label = mapping.get(r.volume_status)
        return [label] if label else []

    def _bias_labels(self, r: TrendAnalysisResult) -> List[str]:
        if r.bias_ma5 > 5.0:
            return [f"短线乖离过大({r.bias_ma5:.1f}%)"]
        elif r.bias_ma5 < -5.0:
            return [f"大幅偏离均线({r.bias_ma5:.1f}%)"]
        return []
