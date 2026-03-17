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
