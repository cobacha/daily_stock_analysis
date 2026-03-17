# src/collectors/peer_comparison_collector.py
# -*- coding: utf-8 -*-
"""
同行对比收集器
"""
from __future__ import annotations
import logging
import re
from typing import List
import pandas as pd
from src.collectors.models import PeerData, PeerStock

_A_SHARE_PATTERN = re.compile(r"^\d{6}$")

class PeerComparisonCollector:
    def collect(self, stock_code: str, stock_name: str) -> PeerData:
        if not _A_SHARE_PATTERN.match(str(stock_code).strip()):
            return PeerData()

        try:
            return self._collect_impl(stock_code, stock_name)
        except Exception as e:
            logging.warning(f"[PeerCollector] {stock_code} 同行对比收集失败: {e}")
            return PeerData()

    def _collect_impl(self, code: str, name: str) -> PeerData:
        import akshare as ak
        try:
            board_df = ak.stock_board_industry_name_em()
        except Exception:
            return PeerData()

        if board_df is None or board_df.empty:
            return PeerData()

        for _, board_row in board_df.iterrows():
            board_name = board_row.get("板块名称", "")
            try:
                comp_df = ak.stock_board_industry_cons_em(symbol=board_name)
                if comp_df is None or comp_df.empty:
                    continue
                codes = comp_df.get("代码", pd.Series()).astype(str).tolist()
                if code in codes:
                    return self._build_peer_data(code, board_name, board_row.get("涨跌幅", 0.0), comp_df)
            except Exception:
                continue
        return PeerData()

    def _build_peer_data(self, target_code, sector_name, sector_change, comp_df) -> PeerData:
        peers: List[PeerStock] = []
        target_rank = 0

        market_cap_col = next((c for c in ["总市值", "流通市值"] if c in comp_df.columns), None)
        if market_cap_col:
            comp_df = comp_df.sort_values(by=market_cap_col, ascending=False)

        for rank, (_, row) in enumerate(comp_df.iterrows(), 1):
            c = str(row.get("代码", "")).strip()
            if c == target_code:
                target_rank = rank
                continue
            if len(peers) >= 5:
                continue

            peers.append(PeerStock(
                code=c,
                name=str(row.get("名称", "")),
                change_pct=float(row.get("涨跌幅", 0) or 0),
            ))

        return PeerData(
            sector_name=sector_name,
            sector_change_pct=float(sector_change or 0),
            peers=peers,
            target_rank_in_sector=target_rank,
            has_data=len(peers) > 0,
        )
