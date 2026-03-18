# src/collectors/fund_flow_collector.py
# -*- coding: utf-8 -*-
"""
资金流向收集器
"""
from __future__ import annotations
import logging
import re
from typing import List, Dict
import pandas as pd
from src.collectors.models import FundFlowData

_A_SHARE_PATTERN = re.compile(r"^\d{6}$")

class FundFlowCollector:
    def collect(self, stock_code: str) -> FundFlowData:
        if not _A_SHARE_PATTERN.match(str(stock_code).strip()):
            return FundFlowData()

        data = FundFlowData()
        try:
            data = self._fetch_fund_flow(stock_code, data)
        except Exception as e:
            logging.warning(f"[FundFlowCollector] 主力资金获取失败: {e}")

        try:
            data.lhb_records = self._fetch_lhb(stock_code)
        except Exception as e:
            logging.debug(f"[FundFlowCollector] 龙虎榜获取失败: {e}")
            data.lhb_records = []

        return data

    def _fetch_fund_flow(self, code: str, data: FundFlowData) -> FundFlowData:
        import akshare as ak
        try:
            df = ak.stock_individual_fund_flow(stock=code, market="sh" if code.startswith("6") else "sz")
        except Exception:
            try:
                df = ak.stock_individual_fund_flow(stock=code)
            except:
                return data

        if df is None or df.empty:
            return data

        df = df.sort_values(by=df.columns[0], ascending=False)
        latest = df.iloc[0]

        # 主力净流入
        net_col_candidates = ["主力净流入-净额", "主力净额", "net_mf_amount"]
        for col in net_col_candidates:
            if col in df.columns:
                val = latest.get(col)
                if pd.notna(val):
                    flow_value = float(val)
                    # AkShare 返回单位是"万元"，过滤异常值（单只股票日主力流入不会超过10亿）
                    if abs(flow_value) < 100000:  # 10亿以内视为有效数据
                        data.main_net_inflow_1d = flow_value
                    else:
                        import logging
                        logging.warning(f"[FundFlowCollector] 主力资金数据异常: {flow_value}万元，跳过")
                    break

        data.has_data = data.main_net_inflow_1d is not None
        return data

    def _fetch_lhb(self, code: str) -> List[Dict]:
        import akshare as ak
        from datetime import date, timedelta
        end_date = date.today().strftime("%Y%m%d")
        start_date = (date.today() - timedelta(days=30)).strftime("%Y%m%d")

        try:
            df = ak.stock_lhb_detail_em(symbol=code, start_date=start_date, end_date=end_date)
        except:
            return []

        if df is None or df.empty:
            return []

        records = []
        for _, row in df.head(5).iterrows():
            records.append({
                "date": str(row.get("上榜日期", "")),
                "reason": str(row.get("上榜原因", "")),
            })
        return records
