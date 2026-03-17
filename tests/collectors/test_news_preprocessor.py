# tests/collectors/test_news_preprocessor.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

from src.collectors.news_preprocessor import NewsPreprocessor
from src.collectors.models import ClassifiedNews


def _make_search_result(title="Test", snippet="Snippet", days_ago=1):
    result = MagicMock()
    result.title = title
    result.snippet = snippet
    result.url = "http://test.com"
    result.published_date = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    return result


class TestNewsPreprocessor:
    def setup_method(self):
        self.preprocessor = NewsPreprocessor()

    def test_empty_input_returns_empty(self):
        result = self.preprocessor.process("000001", "Test", [])
        assert isinstance(result, ClassifiedNews)
        assert result.has_data is False

    def test_recency_weight_24h(self):
        w = self.preprocessor._compute_recency_weight(0.5)
        assert w == 1.0

    def test_recency_weight_3days(self):
        w = self.preprocessor._compute_recency_weight(2.0)
        assert w == 0.7

    @patch("src.collectors.news_preprocessor.LLMToolAdapter")
    def test_llm_classification(self, MockLLM):
        import json
        mock_llm = MockLLM.return_value
        mock_content = json.dumps([
            {"index": 0, "sentiment": "bullish", "impact_level": "high",
             "event_tags": ["事件A"], "reason": "原因A"}
        ])
        mock_llm.call_text.return_value = MagicMock(content=mock_content)

        raw = [_make_search_result("Title", "Snippet", 0.5)]
        result = self.preprocessor.process("000001", "Test", raw)

        assert result.has_data is True
        assert result.bullish_count == 1
        assert result.items[0].sentiment == "bullish"
