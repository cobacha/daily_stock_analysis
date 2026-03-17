# -*- coding: utf-8 -*-
"""
===================================
分析服务层
===================================

职责：
1. 封装股票分析逻辑
2. 调用 analyzer 和 pipeline 执行分析
3. 保存分析结果到数据库
"""

import json
import logging
import uuid
from typing import Optional, Dict, Any

from src.repositories.analysis_repo import AnalysisRepository

logger = logging.getLogger(__name__)


class AnalysisService:
    """
    分析服务
    
    封装股票分析相关的业务逻辑
    """
    
    def __init__(self):
        """初始化分析服务"""
        self.repo = AnalysisRepository()
    
    def analyze_stock(
        self,
        stock_code: str,
        report_type: str = "detailed",
        force_refresh: bool = False,
        force_update: bool = False,
        query_id: Optional[str] = None,
        send_notification: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        执行股票分析

        Args:
            stock_code: 股票代码
            report_type: 报告类型 (simple/detailed)
            force_refresh: 是否强制刷新数据层缓存
            force_update: 是否强制跳过盘后缓存（--update 模式）
            query_id: 查询 ID（可选）
            send_notification: 是否发送通知（API 触发默认发送）

        Returns:
            分析结果字典，包含:
            - stock_code: 股票代码
            - stock_name: 股票名称
            - report: 分析报告
        """
        try:
            # 导入分析相关模块
            from src.config import get_config
            from src.core.pipeline import StockAnalysisPipeline
            from src.enums import ReportType

            # 生成 query_id
            if query_id is None:
                query_id = uuid.uuid4().hex

            # 确定报告类型（归一化）
            rt = ReportType.from_str(report_type)

            # ── 盘后缓存检查 ──────────────────────────────────────────────
            # 18:00 之后市场已收盘，若当天已有同股票+同报告类型的分析结果，
            # 直接复用，避免重复调用 LLM；第二天自然日变更后缓存自动失效。
            # force_update=True（--update 参数）时跳过缓存强制重新分析。
            if not force_update:
                cached = self.repo.get_post_close_cache(stock_code, rt.value)
                if cached is not None:
                    logger.info(
                        f"[盘后缓存] {stock_code} 命中今日缓存（id={cached.id}），"
                        f"query_id={query_id}，跳过重新分析，不写入新记录"
                    )
                    return self._build_response_from_cached(cached, query_id, rt.value)
            # ─────────────────────────────────────────────────────────────

            # 获取配置
            config = get_config()

            # 创建分析流水线
            # 已在上方完成盘后缓存检查，传入 force_update=True 跳过 pipeline 内的重复检查
            pipeline = StockAnalysisPipeline(
                config=config,
                query_id=query_id,
                query_source="api",
                force_update=True,
            )

            # 执行分析
            result = pipeline.process_single_stock(
                code=stock_code,
                skip_analysis=False,
                single_stock_notify=send_notification,
                report_type=rt
            )

            if result is None:
                logger.warning(f"分析股票 {stock_code} 返回空结果")
                return None

            # 构建响应
            return self._build_analysis_response(result, query_id, report_type=rt.value)

        except Exception as e:
            logger.error(f"分析股票 {stock_code} 失败: {e}", exc_info=True)
            return None
    
    def _build_response_from_cached(
        self,
        record: Any,
        query_id: str,
        report_type: str,
    ) -> Dict[str, Any]:
        """
        从缓存的 AnalysisHistory 记录构建与正常分析路径相同格式的响应。

        Args:
            record: AnalysisHistory 对象（盘后缓存命中的记录）
            query_id: 新的查询 ID（当前 task_id）
            report_type: 归一化报告类型

        Returns:
            与 _build_analysis_response 格式完全一致的字典
        """
        # 解析 raw_result 获取可能存储的额外字段
        raw: Dict[str, Any] = {}
        if record.raw_result:
            try:
                raw = json.loads(record.raw_result)
            except Exception:
                pass

        current_price = raw.get("current_price")
        change_pct = raw.get("change_pct")
        model_used = raw.get("model_used")

        sentiment_label = self._get_sentiment_label(record.sentiment_score or 0)

        def _to_str(v: Any) -> Optional[str]:
            return str(v) if v is not None else None

        report = {
            "meta": {
                "query_id": query_id,
                "stock_code": record.code,
                "stock_name": record.name,
                "report_type": report_type,
                "current_price": current_price,
                "change_pct": change_pct,
                "model_used": model_used,
            },
            "summary": {
                "analysis_summary": record.analysis_summary,
                "operation_advice": record.operation_advice,
                "trend_prediction": record.trend_prediction,
                "sentiment_score": record.sentiment_score,
                "sentiment_label": sentiment_label,
            },
            "strategy": {
                "ideal_buy": _to_str(record.ideal_buy),
                "secondary_buy": _to_str(record.secondary_buy),
                "stop_loss": _to_str(record.stop_loss),
                "take_profit": _to_str(record.take_profit),
            },
            "details": {
                "news_summary": record.news_content,
            },
        }

        return {
            "stock_code": record.code,
            "stock_name": record.name,
            "report": report,
        }

    def _build_analysis_response(
        self, 
        result: Any, 
        query_id: str,
        report_type: str = "detailed",
    ) -> Dict[str, Any]:
        """
        构建分析响应
        
        Args:
            result: AnalysisResult 对象
            query_id: 查询 ID
            report_type: 归一化后的报告类型
            
        Returns:
            格式化的响应字典
        """
        # 获取狙击点位
        sniper_points = {}
        if hasattr(result, 'get_sniper_points'):
            sniper_points = result.get_sniper_points() or {}
        
        # 计算情绪标签
        sentiment_label = self._get_sentiment_label(result.sentiment_score)
        
        # 构建报告结构
        report = {
            "meta": {
                "query_id": query_id,
                "stock_code": result.code,
                "stock_name": result.name,
                "report_type": report_type,
                "current_price": result.current_price,
                "change_pct": result.change_pct,
                "model_used": getattr(result, "model_used", None),
            },
            "summary": {
                "analysis_summary": result.analysis_summary,
                "operation_advice": result.operation_advice,
                "trend_prediction": result.trend_prediction,
                "sentiment_score": result.sentiment_score,
                "sentiment_label": sentiment_label,
            },
            "strategy": {
                "ideal_buy": sniper_points.get("ideal_buy"),
                "secondary_buy": sniper_points.get("secondary_buy"),
                "stop_loss": sniper_points.get("stop_loss"),
                "take_profit": sniper_points.get("take_profit"),
            },
            "details": {
                "news_summary": result.news_summary,
                "technical_analysis": result.technical_analysis,
                "fundamental_analysis": result.fundamental_analysis,
                "risk_warning": result.risk_warning,
            }
        }
        
        return {
            "stock_code": result.code,
            "stock_name": result.name,
            "report": report,
        }
    
    def _get_sentiment_label(self, score: int) -> str:
        """
        根据评分获取情绪标签
        
        Args:
            score: 情绪评分 (0-100)
            
        Returns:
            情绪标签
        """
        if score >= 80:
            return "极度乐观"
        elif score >= 60:
            return "乐观"
        elif score >= 40:
            return "中性"
        elif score >= 20:
            return "悲观"
        else:
            return "极度悲观"
