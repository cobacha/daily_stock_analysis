# tests/collectors/test_peer_comparison_collector.py
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

    def test_us_stock_skips_gracefully(self):
        result = self.collector.collect("AAPL", "Apple")
        assert result.has_data is False

    def test_failure_returns_no_data(self):
        with patch("akshare.stock_board_industry_name_em", side_effect=Exception("timeout")):
            result = self.collector.collect("000001", "平安银行")
        assert result.has_data is False
