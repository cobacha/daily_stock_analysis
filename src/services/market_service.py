# -*- coding: utf-8 -*-
"""
大盘复盘服务 — 负责缓存查询与保存
"""
import json
import logging
import uuid
from typing import Optional, Dict, Any

from src.storage import DatabaseManager
from src.repositories.analysis_repo import AnalysisRepository

logger = logging.getLogger(__name__)

# 大盘复盘在 AnalysisHistory 中的特殊标识
MARKET_CACHE_CODE: Dict[str, str] = {
    "cn": "MARKET_CN",
    "us": "MARKET_US",
}
MARKET_REVIEW_TYPE = "market_review"


class MarketService:
    """大盘复盘缓存服务"""

    def __init__(self, db_manager=None):
        self.repo = AnalysisRepository(db_manager or DatabaseManager.get_instance())

    def get_cached_review(self, region: str = "cn"):
        """查询当日大盘复盘缓存，命中返回 AnalysisHistory 记录，否则返回 None"""
        code = MARKET_CACHE_CODE.get(region, MARKET_CACHE_CODE["cn"])
        return self.repo.get_post_close_cache(code, MARKET_REVIEW_TYPE)

    def save_review(
        self,
        region: str,
        overview_dict: Dict[str, Any],
        review_text: str,
    ) -> None:
        """将大盘复盘结果保存到 AnalysisHistory"""
        code = MARKET_CACHE_CODE.get(region, MARKET_CACHE_CODE["cn"])
        query_id = str(uuid.uuid4())

        # 构造一个轻量 result 对象供 save() 使用
        class _FakeResult:
            pass

        result = _FakeResult()
        result.code = code
        result.name = "大盘复盘"
        result.sentiment_score = 50
        result.trend_prediction = ""
        result.operation_advice = ""
        result.analysis_summary = review_text
        result.decision_type = "hold"
        result.confidence_level = "中"
        result.success = True

        self.repo.save(
            result=result,
            query_id=query_id,
            report_type=MARKET_REVIEW_TYPE,
            news_content=None,
            context_snapshot=overview_dict,
        )
        logger.info(f"[大盘] 复盘缓存已保存 region={region} code={code}")
