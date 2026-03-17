# src/collectors/news_preprocessor.py
# -*- coding: utf-8 -*-
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional, Any

from src.collectors.models import ClassifiedNews, ClassifiedNewsItem
from src.agent.llm_adapter import LLMToolAdapter

_CLASSIFY_PROMPT_TEMPLATE = """\
你是一个专业的财经新闻分析师。请对以下关于"{stock_name}"({stock_code})的新闻逐条进行分析和分类。

新闻列表：
{news_list}

请输出JSON数组：
[
  {{"index": 0, "sentiment": "...", "impact_level": "...", "event_tags": [], "reason": "..."}},
  ...
]
分类：bullish(利好), bearish(利空), neutral(中性)。
只输出JSON。"""

class NewsPreprocessor:
    def process(self, stock_code: str, stock_name: str, raw_results: Optional[List[Any]]) -> ClassifiedNews:
        if not raw_results:
            return ClassifiedNews()

        try:
            # 1. 构建新闻列表
            news_lines = [f"[{i}] {getattr(r, 'title', '')}: {getattr(r, 'snippet', '')}"
                          for i, r in enumerate(raw_results)]
            prompt = _CLASSIFY_PROMPT_TEMPLATE.format(stock_name=stock_name, stock_code=stock_code,
                                                     news_list="\n".join(news_lines))

            # 2. LLM调用
            llm = LLMToolAdapter()
            resp = llm.call_text([{"role": "user", "content": prompt}], temperature=0.1)
            if not resp or not resp.content:
                return ClassifiedNews()

            # 3. 解析JSON
            data = json.loads(resp.content)
            if not isinstance(data, list):
                return ClassifiedNews()

            # 4. 构建结果
            items = []
            bullish = bearish = neutral = 0
            for i, r in enumerate(raw_results):
                cls = next((c for c in data if c.get('index') == i), {})
                sentiment = cls.get('sentiment', 'neutral')

                if sentiment == 'bullish': bullish += 1
                elif sentiment == 'bearish': bearish += 1
                else: neutral += 1

                weight = self._compute_recency_weight_from_result(r)
                items.append(ClassifiedNewsItem(
                    title=getattr(r, 'title', ''),
                    snippet=getattr(r, 'snippet', ''),
                    url=getattr(r, 'url', ''),
                    publish_time=getattr(r, 'published_date', None),
                    sentiment=sentiment,
                    impact_level=cls.get('impact_level', 'low'),
                    event_tags=cls.get('event_tags', []),
                    recency_weight=weight,
                    reason=cls.get('reason', '')
                ))

            return ClassifiedNews(items=items, bullish_count=bullish, bearish_count=bearish,
                                  neutral_count=neutral, has_data=len(items) > 0)
        except Exception as e:
            logging.warning(f"[NewsPreprocessor] 处理失败: {e}")
            return ClassifiedNews()

    def _compute_recency_weight(self, days_ago: float) -> float:
        if days_ago <= 1.0: return 1.0
        elif days_ago <= 3.0: return 0.7
        elif days_ago <= 7.0: return 0.4
        return 0.2

    def _compute_recency_weight_from_result(self, result: Any) -> float:
        try:
            pub = getattr(result, 'published_date', None)
            if not pub: return 0.5
            pub_dt = datetime.fromisoformat(str(pub).replace('Z', '+00:00'))
            if pub_dt.tzinfo is None: pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            days = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 86400
            return self._compute_recency_weight(days)
        except: return 0.5
