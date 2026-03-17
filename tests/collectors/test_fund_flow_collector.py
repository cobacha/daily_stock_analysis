# tests/collectors/test_fund_flow_collector.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from src.collectors.fund_flow_collector import FundFlowCollector
from src.collectors.models import FundFlowData

class TestFundFlowCollector:
    def setup_method(self):
        self.collector = FundFlowCollector()

    def test_returns_fundflowdata_type(self):
        with patch("akshare.stock_individual_fund_flow", side_effect=Exception("network error")):
            result = self.collector.collect("000001")
        assert isinstance(result, FundFlowData)

    def test_akshare_failure_returns_no_data(self):
        with patch("akshare.stock_individual_fund_flow", side_effect=Exception("timeout")):
            result = self.collector.collect("000001")
        assert result.has_data is False

    def test_empty_dataframe_returns_no_data(self):
        with patch("akshare.stock_individual_fund_flow", return_value=pd.DataFrame()):
            result = self.collector.collect("000001")
            assert result.has_data is False

    def test_us_stock_skips_gracefully(self):
        result = self.collector.collect("AAPL")
        assert result.has_data is False
