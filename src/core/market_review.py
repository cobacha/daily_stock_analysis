# -*- coding: utf-8 -*-
"""
===================================
股票智能分析系统 - 大盘复盘模块（支持 A 股 / 美股）
===================================

职责：
1. 根据 MARKET_REVIEW_REGION 配置选择市场区域（cn / us / both）
2. 执行大盘复盘分析并生成复盘报告
3. 保存和发送复盘报告
"""

import logging
from datetime import datetime
from typing import Optional

from src.config import get_config
from src.notification import NotificationService
from src.market_analyzer import MarketAnalyzer
from src.search_service import SearchService
from src.analyzer import GeminiAnalyzer


logger = logging.getLogger(__name__)


def run_market_review(
    notifier: NotificationService,
    analyzer: Optional[GeminiAnalyzer] = None,
    search_service: Optional[SearchService] = None,
    send_notification: bool = True,
    merge_notification: bool = False,
    override_region: Optional[str] = None,
    region: Optional[str] = None,
) -> Optional[dict]:
    """
    执行大盘复盘分析

    Args:
        notifier: 通知服务
        analyzer: AI分析器（可选）
        search_service: 搜索服务（可选）
        send_notification: 是否发送通知
        merge_notification: 是否合并推送（跳过本次推送，由 main 层合并个股+大盘后统一发送，Issue #190）
        override_region: 覆盖 config 的 market_review_region（Issue #373 交易日过滤后有效子集）
        region: 市场区域（cn / us / both），优先级高于 override_region 和 config

    Returns:
        dict with keys:
            - "overview": MarketOverview 对象（both 模式下为 A 股 overview，可能为 None）
            - "review_text": 复盘报告文本字符串
    """
    logger.info("开始执行大盘复盘分析...")
    config = get_config()
    # region 参数优先级：region > override_region > config
    effective_region = (
        region
        if region is not None
        else (
            override_region
            if override_region is not None
            else (getattr(config, 'market_review_region', 'cn') or 'cn')
        )
    )
    if effective_region not in ('cn', 'us', 'both'):
        effective_region = 'cn'

    market_overview = None

    try:
        if effective_region == 'both':
            # 顺序执行 A 股 + 美股，合并报告
            cn_analyzer = MarketAnalyzer(
                search_service=search_service, analyzer=analyzer, region='cn'
            )
            us_analyzer = MarketAnalyzer(
                search_service=search_service, analyzer=analyzer, region='us'
            )
            logger.info("生成 A 股大盘复盘报告...")
            market_overview = cn_analyzer.get_market_overview()
            cn_report = cn_analyzer.run_daily_review()
            logger.info("生成美股大盘复盘报告...")
            us_report = us_analyzer.run_daily_review()
            review_report = ''
            if cn_report:
                review_report = f"# A股大盘复盘\n\n{cn_report}"
            if us_report:
                if review_report:
                    review_report += "\n\n---\n\n> 以下为美股大盘复盘\n\n"
                review_report += f"# 美股大盘复盘\n\n{us_report}"
            if not review_report:
                review_report = None
        else:
            market_analyzer = MarketAnalyzer(
                search_service=search_service,
                analyzer=analyzer,
                region=effective_region,
            )
            market_overview = market_analyzer.get_market_overview()
            review_report = market_analyzer.run_daily_review()

        if review_report:
            # 保存报告到文件
            date_str = datetime.now().strftime('%Y%m%d')
            report_filename = f"market_review_{date_str}.md"
            filepath = notifier.save_report_to_file(
                f"# 🎯 大盘复盘\n\n{review_report}",
                report_filename
            )
            logger.info(f"大盘复盘报告已保存: {filepath}")

            # 写入 DB 缓存，使 CLI 和 API 路径共享同一份当日缓存
            try:
                from src.services.market_service import MarketService
                _overview_dict = {}
                if market_overview is not None:
                    _overview_dict = {
                        "date": getattr(market_overview, "date", ""),
                        "indices": [idx.to_dict() for idx in getattr(market_overview, "indices", [])],
                        "up_count": getattr(market_overview, "up_count", 0),
                        "down_count": getattr(market_overview, "down_count", 0),
                        "flat_count": getattr(market_overview, "flat_count", 0),
                        "limit_up_count": getattr(market_overview, "limit_up_count", 0),
                        "limit_down_count": getattr(market_overview, "limit_down_count", 0),
                        "total_amount": getattr(market_overview, "total_amount", 0.0),
                        "top_sectors": getattr(market_overview, "top_sectors", []),
                        "bottom_sectors": getattr(market_overview, "bottom_sectors", []),
                        "review_text": review_report,
                    }
                MarketService().save_review(
                    region=effective_region if effective_region in ('cn', 'us') else 'cn',
                    overview_dict=_overview_dict,
                    review_text=review_report,
                )
                logger.info("[大盘复盘] 已写入 DB 缓存")
            except Exception as _e:
                logger.warning(f"[大盘复盘] 写入 DB 缓存失败（不影响报告生成）: {_e}")
            
            # 推送通知（合并模式下跳过，由 main 层统一发送）
            if merge_notification and send_notification:
                logger.info("合并推送模式：跳过大盘复盘单独推送，将在个股+大盘复盘后统一发送")
            elif send_notification and notifier.is_available():
                # 添加标题
                report_content = f"🎯 大盘复盘\n\n{review_report}"

                success = notifier.send(report_content, email_send_to_all=True)
                if success:
                    logger.info("大盘复盘推送成功")
                else:
                    logger.warning("大盘复盘推送失败")
            elif not send_notification:
                logger.info("已跳过推送通知 (--no-notify)")
            
            return {"overview": market_overview, "review_text": review_report}

    except Exception as e:
        logger.error(f"大盘复盘分析失败: {e}")

    return None
