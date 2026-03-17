import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { marketApi, type MarketReviewResponse } from '../../api/market';

const fmt = (v: number) => v.toFixed(2);
const fmtPct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
const colorOf = (v: number) =>
  v > 0 ? 'text-[#ff4d4d]' : v < 0 ? 'text-[#00d46a]' : 'text-muted-text';

export const MarketTopBar: React.FC = () => {
  const [data, setData] = useState<MarketReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    let pollCount = 0;
    let timer: ReturnType<typeof setInterval>;

    const load = () => {
      marketApi
        .getReview('cn')
        .then((res) => {
          if (!cancelled) {
            setData(res);
            setLoading(false);
            clearInterval(timer);
          }
        })
        .catch(() => {
          if (!cancelled) setLoading(false);
        });
    };

    load();

    // 若后台正在生成，每 5s 轮询一次，最多 60s
    timer = setInterval(() => {
      if (pollCount > 12) { clearInterval(timer); return; }
      pollCount++;
      load();
    }, 5000);

    return () => { cancelled = true; clearInterval(timer); };
  }, []);

  if (loading) {
    return (
      <div className="w-full bg-elevated border-b border-surface-dim px-4 py-2 flex items-center gap-4 overflow-x-auto">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-4 w-24 bg-white/5 rounded animate-pulse flex-shrink-0" />
        ))}
      </div>
    );
  }

  if (!data || data.indices.length === 0) return null;

  const mainIndices = data.indices.slice(0, 3);
  const summary = data.review_text
    ? data.review_text.replace(/#{1,6}\s*/g, '').slice(0, 60)
    : '';

  return (
    <div className="w-full bg-elevated border-b border-surface-dim px-4 py-2 flex items-center gap-4 overflow-x-auto text-xs">
      {mainIndices.map((idx) => (
        <div key={idx.code} className="flex items-center gap-1.5 flex-shrink-0">
          <span className="text-muted-text">{idx.name}</span>
          <span className="font-mono text-foreground">{fmt(idx.current)}</span>
          <span className={`font-mono ${colorOf(idx.change_pct)}`}>{fmtPct(idx.change_pct)}</span>
        </div>
      ))}

      {data.total_amount > 0 && (
        <div className="flex items-center gap-1 flex-shrink-0 text-muted-text">
          <span>成交额</span>
          <span className="text-foreground font-mono">{data.total_amount.toFixed(0)}亿</span>
        </div>
      )}

      <div className="w-px h-3 bg-white/10 flex-shrink-0" />

      {summary && (
        <Link
          to="/market"
          className="text-muted-text hover:text-foreground transition-colors truncate max-w-xs flex-shrink min-w-0"
          title="查看完整大盘复盘"
        >
          {summary}…
        </Link>
      )}

      <Link
        to="/market"
        className="ml-auto flex-shrink-0 text-cyan hover:text-cyan/80 transition-colors"
        title="查看大盘分析"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </Link>
    </div>
  );
};
