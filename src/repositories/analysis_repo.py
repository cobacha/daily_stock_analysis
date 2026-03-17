# -*- coding: utf-8 -*-
"""
===================================
分析历史数据访问层
===================================

职责：
1. 封装分析历史数据的数据库操作
2. 提供 CRUD 接口
"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any

from src.storage import DatabaseManager, AnalysisHistory

logger = logging.getLogger(__name__)


class AnalysisRepository:
    """
    分析历史数据访问层
    
    封装 AnalysisHistory 表的数据库操作
    """
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        初始化数据访问层
        
        Args:
            db_manager: 数据库管理器（可选，默认使用单例）
        """
        self.db = db_manager or DatabaseManager.get_instance()
    
    def get_by_query_id(self, query_id: str) -> Optional[AnalysisHistory]:
        """
        根据 query_id 获取分析记录
        
        Args:
            query_id: 查询 ID
            
        Returns:
            AnalysisHistory 对象，不存在返回 None
        """
        try:
            records = self.db.get_analysis_history(query_id=query_id, limit=1)
            return records[0] if records else None
        except Exception as e:
            logger.error(f"查询分析记录失败: {e}")
            return None
    
    def get_list(
        self,
        code: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[AnalysisHistory]:
        """
        获取分析记录列表
        
        Args:
            code: 股票代码筛选
            days: 时间范围（天）
            limit: 返回数量限制
            
        Returns:
            AnalysisHistory 对象列表
        """
        try:
            return self.db.get_analysis_history(
                code=code,
                days=days,
                limit=limit
            )
        except Exception as e:
            logger.error(f"获取分析列表失败: {e}")
            return []
    
    def save(
        self,
        result: Any,
        query_id: str,
        report_type: str,
        news_content: Optional[str] = None,
        context_snapshot: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        保存分析结果
        
        Args:
            result: 分析结果对象
            query_id: 查询 ID
            report_type: 报告类型
            news_content: 新闻内容
            context_snapshot: 上下文快照
            
        Returns:
            保存的记录数
        """
        try:
            return self.db.save_analysis_history(
                result=result,
                query_id=query_id,
                report_type=report_type,
                news_content=news_content,
                context_snapshot=context_snapshot
            )
        except Exception as e:
            logger.error(f"保存分析结果失败: {e}")
            return 0
    
    def get_post_close_cache(
        self,
        code: str,
        report_type: str,
        close_hour: int = 18,
    ) -> Optional[AnalysisHistory]:
        """
        当日缓存查询：当天已分析过的股票直接复用结果，避免重复调用 LLM。

        逻辑：
        - 查找今天（自然日）已有的同股票、同报告类型分析记录
        - 找到则命中缓存，调用方可直接复用
        - --update 模式（force_update=True）由调用方控制跳过，本方法不感知

        Args:
            code: 标准化后的股票代码
            report_type: 归一化的报告类型（simple/full/brief）
            close_hour: 保留参数（历史兼容），当前不再使用

        Returns:
            命中的 AnalysisHistory 记录，未命中返回 None
        """
        try:
            records = self.db.get_analysis_history(
                code=code,
                report_type=report_type,
                today_only=True,
                limit=1,
            )
            if records:
                record = records[0]
                logger.info(
                    f"[当日缓存] 命中 {code} 今日缓存记录 id={record.id}, "
                    f"created_at={record.created_at}"
                )
                return record
        except Exception as e:
            logger.error(f"查询当日缓存失败: {e}")
        return None

    def build_analysis_result_from_cache(
        self, record: AnalysisHistory
    ) -> Optional[Any]:
        """
        从缓存的 AnalysisHistory 记录重建 AnalysisResult 对象（供 pipeline 路径使用）。

        raw_result 字段存储了完整的 to_dict() 序列化结果，解析后可还原大部分字段。

        Returns:
            AnalysisResult 对象，失败返回 None
        """
        try:
            import json
            from src.analyzer import AnalysisResult

            raw: Dict[str, Any] = {}
            if record.raw_result:
                try:
                    raw = json.loads(record.raw_result)
                except Exception:
                    pass

            return AnalysisResult(
                code=record.code,
                name=record.name or "",
                sentiment_score=record.sentiment_score or 50,
                trend_prediction=record.trend_prediction or "",
                operation_advice=record.operation_advice or "",
                analysis_summary=record.analysis_summary or "",
                decision_type=raw.get("decision_type", "hold"),
                confidence_level=raw.get("confidence_level", "中"),
                dashboard=raw.get("dashboard"),
                trend_analysis=raw.get("trend_analysis", ""),
                short_term_outlook=raw.get("short_term_outlook", ""),
                medium_term_outlook=raw.get("medium_term_outlook", ""),
                technical_analysis=raw.get("technical_analysis", ""),
                ma_analysis=raw.get("ma_analysis", ""),
                volume_analysis=raw.get("volume_analysis", ""),
                pattern_analysis=raw.get("pattern_analysis", ""),
                fundamental_analysis=raw.get("fundamental_analysis", ""),
                sector_position=raw.get("sector_position", ""),
                company_highlights=raw.get("company_highlights", ""),
                news_summary=raw.get("news_summary", ""),
                market_sentiment=raw.get("market_sentiment", ""),
                hot_topics=raw.get("hot_topics", ""),
                key_points=raw.get("key_points", ""),
                risk_warning=raw.get("risk_warning", ""),
                buy_reason=raw.get("buy_reason", ""),
                current_price=raw.get("current_price"),
                change_pct=raw.get("change_pct"),
                model_used=raw.get("model_used"),
                data_sources=raw.get("data_sources", ""),
                success=True,
            )
        except Exception as e:
            logger.error(f"从缓存重建 AnalysisResult 失败: {e}")
            return None

    def count_by_code(self, code: str, days: int = 30) -> int:
        """
        统计指定股票的分析记录数
        
        Args:
            code: 股票代码
            days: 时间范围（天）
            
        Returns:
            记录数量
        """
        try:
            records = self.db.get_analysis_history(code=code, days=days, limit=1000)
            return len(records)
        except Exception as e:
            logger.error(f"统计分析记录失败: {e}")
            return 0
