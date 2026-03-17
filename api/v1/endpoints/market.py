# -*- coding: utf-8 -*-
"""大盘复盘 API 端点"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from src.services.market_service import MarketService

logger = logging.getLogger(__name__)
router = APIRouter()


def _run_market_review(region: str) -> dict:
    """
    实际执行大盘复盘生成（同步）。
    导入放在函数内，避免启动时加载重量级依赖。
    """
    from src.core.market_review import run_market_review
    from src.notification import NotificationService

    notifier = NotificationService()
    result = run_market_review(notifier, region=region, send_notification=False)
    # run_market_review 返回 {"overview": MarketOverview, "review_text": str} 或 None
    if result is None:
        raise HTTPException(status_code=503, detail="大盘数据获取失败，请稍后重试")

    overview = result.get("overview")
    review_text: str = result.get("review_text", "")

    # 序列化 overview
    overview_dict = _overview_to_dict(overview, review_text)

    # 保存缓存
    svc = MarketService()
    svc.save_review(region=region, overview_dict=overview_dict, review_text=review_text)

    overview_dict["cached"] = False
    return overview_dict


def _overview_to_dict(overview, review_text: str) -> dict:
    """将 MarketOverview 转为可序列化字典"""
    if overview is None:
        return {"date": "", "region": "", "indices": [], "up_count": 0, "down_count": 0,
                "flat_count": 0, "limit_up_count": 0, "limit_down_count": 0,
                "total_amount": 0.0, "top_sectors": [], "bottom_sectors": [],
                "review_text": review_text, "generated_at": None}
    return {
        "date": overview.date,
        "indices": [idx.to_dict() for idx in overview.indices],
        "up_count": overview.up_count,
        "down_count": overview.down_count,
        "flat_count": overview.flat_count,
        "limit_up_count": overview.limit_up_count,
        "limit_down_count": overview.limit_down_count,
        "total_amount": overview.total_amount,
        "top_sectors": overview.top_sectors,
        "bottom_sectors": overview.bottom_sectors,
        "review_text": review_text,
        "generated_at": None,
    }


def _record_to_response(record, region: str) -> dict:
    """将 AnalysisHistory 缓存记录转为响应字典"""
    # context_snapshot 里存的 overview_dict
    ctx: dict = {}
    if hasattr(record, "context_snapshot") and record.context_snapshot:
        try:
            ctx = json.loads(record.context_snapshot) if isinstance(record.context_snapshot, str) else record.context_snapshot
        except Exception:
            pass

    return {
        "region": region,
        "cached": True,
        "date": ctx.get("date", ""),
        "indices": ctx.get("indices", []),
        "up_count": ctx.get("up_count", 0),
        "down_count": ctx.get("down_count", 0),
        "flat_count": ctx.get("flat_count", 0),
        "limit_up_count": ctx.get("limit_up_count", 0),
        "limit_down_count": ctx.get("limit_down_count", 0),
        "total_amount": ctx.get("total_amount", 0.0),
        "top_sectors": ctx.get("top_sectors", []),
        "bottom_sectors": ctx.get("bottom_sectors", []),
        "review_text": record.analysis_summary or ctx.get("review_text", ""),
        "generated_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/review")
def get_market_review(region: str = Query("cn", pattern="^(cn|us)$")):
    """
    获取当日大盘复盘。
    - 有缓存：直接返回
    - 无缓存：触发生成（同步，首次较慢）
    """
    svc = MarketService()
    cached = svc.get_cached_review(region=region)
    if cached:
        return _record_to_response(cached, region)

    # 无缓存，同步生成
    return _run_market_review(region)


@router.post("/review/refresh")
def refresh_market_review(region: str = Query("cn", pattern="^(cn|us)$")):
    """强制重新生成大盘复盘（忽略当日缓存）"""
    return _run_market_review(region)
