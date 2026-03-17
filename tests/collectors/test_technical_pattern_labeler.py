# tests/collectors/test_technical_pattern_labeler.py
# -*- coding: utf-8 -*-
import pytest
from src.collectors.technical_pattern_labeler import TechnicalPatternLabeler
from src.stock_analyzer import (
    TrendAnalysisResult, TrendStatus, VolumeStatus,
    MACDStatus, RSIStatus, BuySignal
)


def _make_result(**kwargs) -> TrendAnalysisResult:
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
        result = _make_result(trend_status=TrendStatus.BULL, ma5=11.0, ma10=10.5, ma20=10.0)
        labels = self.labeler.label(result)
        assert "多头排列" in labels

    def test_bear_alignment_label(self):
        result = _make_result(trend_status=TrendStatus.BEAR, ma5=9.0, ma10=9.5, ma20=10.0)
        labels = self.labeler.label(result)
        assert "空头排列" in labels

    def test_macd_golden_cross_zero_label(self):
        result = _make_result(macd_status=MACDStatus.GOLDEN_CROSS_ZERO, macd_dif=0.2, macd_dea=0.1)
        labels = self.labeler.label(result)
        assert any("零轴上金叉" in l for l in labels)

    def test_macd_golden_cross_label(self):
        result = _make_result(macd_status=MACDStatus.GOLDEN_CROSS, macd_dif=-0.05, macd_dea=-0.1)
        labels = self.labeler.label(result)
        assert any("金叉" in l for l in labels)

    def test_rsi_overbought_label(self):
        result = _make_result(rsi_status=RSIStatus.OVERBOUGHT, rsi_6=78.0)
        labels = self.labeler.label(result)
        assert any("RSI超买" in l for l in labels)

    def test_rsi_oversold_label(self):
        result = _make_result(rsi_status=RSIStatus.OVERSOLD, rsi_6=22.0)
        labels = self.labeler.label(result)
        assert any("RSI超卖" in l for l in labels)

    def test_shrink_volume_down_label(self):
        result = _make_result(volume_status=VolumeStatus.SHRINK_VOLUME_DOWN, volume_ratio_5d=0.6)
        labels = self.labeler.label(result)
        assert "缩量回调" in labels

    def test_heavy_volume_up_label(self):
        result = _make_result(volume_status=VolumeStatus.HEAVY_VOLUME_UP, volume_ratio_5d=1.8)
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
