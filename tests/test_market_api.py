# tests/test_market_api.py
# -*- coding: utf-8 -*-
import sys
from unittest.mock import MagicMock, patch

for _mod in ("litellm", "google.generativeai", "google.genai", "anthropic"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest
from fastapi.testclient import TestClient


def _make_client():
    from api.app import create_app
    app = create_app()
    return TestClient(app, raise_server_exceptions=False)


class TestMarketApi:
    def test_get_review_returns_200_with_cached_data(self):
        """缓存命中时 GET /api/v1/market/review 返回 200"""
        import json
        from datetime import datetime
        client = _make_client()
        cached = MagicMock()
        cached.analysis_summary = "今日复盘"
        ctx = {"date": "2026-03-17", "indices": [], "up_count": 2000, "down_count": 1500,
               "flat_count": 100, "limit_up_count": 30, "limit_down_count": 2,
               "total_amount": 8000.0, "top_sectors": [], "bottom_sectors": [], "review_text": "今日复盘"}
        cached.context_snapshot = json.dumps(ctx)
        cached.created_at = datetime(2026, 3, 17, 16, 30)

        with patch("api.v1.endpoints.market.MarketService") as mock_svc_cls:
            mock_svc = MagicMock()
            mock_svc_cls.return_value = mock_svc
            mock_svc.get_cached_review.return_value = cached

            resp = client.get("/api/v1/market/review?region=cn")
            assert resp.status_code == 200
            data = resp.json()
            assert data["cached"] is True
            assert data["review_text"] == "今日复盘"

    def test_post_refresh_calls_run_market_review(self):
        """POST /refresh 调用 _run_market_review"""
        client = _make_client()
        fake_result = {
            "date": "2026-03-17", "indices": [], "up_count": 0, "down_count": 0,
            "flat_count": 0, "limit_up_count": 0, "limit_down_count": 0,
            "total_amount": 0.0, "top_sectors": [], "bottom_sectors": [],
            "review_text": "新复盘", "generated_at": None, "cached": False
        }
        with patch("api.v1.endpoints.market._run_market_review", return_value=fake_result) as mock_run:
            resp = client.post("/api/v1/market/review/refresh?region=cn")
            assert resp.status_code == 200
            mock_run.assert_called_once_with("cn")

    def test_get_review_no_cache_triggers_generation(self):
        """无缓存时触发 _run_market_review"""
        client = _make_client()
        fake_result = {
            "date": "2026-03-17", "indices": [], "up_count": 0, "down_count": 0,
            "flat_count": 0, "limit_up_count": 0, "limit_down_count": 0,
            "total_amount": 0.0, "top_sectors": [], "bottom_sectors": [],
            "review_text": "", "generated_at": None, "cached": False
        }
        with patch("api.v1.endpoints.market.MarketService") as mock_svc_cls, \
             patch("api.v1.endpoints.market._run_market_review", return_value=fake_result) as mock_run:
            mock_svc = MagicMock()
            mock_svc_cls.return_value = mock_svc
            mock_svc.get_cached_review.return_value = None

            resp = client.get("/api/v1/market/review")
            assert resp.status_code == 200
            mock_run.assert_called_once()
