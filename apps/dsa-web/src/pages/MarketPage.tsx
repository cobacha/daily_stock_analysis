import React, { useState, useEffect, useCallback } from 'react';
import { marketApi, type MarketReviewResponse } from '../api/market';
import { Card } from '../components/common';
import { MarketReviewMarkdown } from '../components/market/MarketReviewMarkdown';

type Region = 'cn' | 'us';
const REGION_LABELS: Record<Region, string> = { cn: 'A股', us: '美股' };

const fmt = (v: number) => v.toFixed(2);
const fmtPct = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
const colorOf = (v: number) =>
  v > 0 ? 'text-[#ff4d4d]' : v < 0 ? 'text-[#00d46a]' : 'text-muted-text';
const bgOf = (v: number) =>
  v > 0 ? 'bg-[#ff4d4d]/10' : v < 0 ? 'bg-[#00d46a]/10' : 'bg-white/5';

const MarketPage: React.FC = () => {
  const [region, setRegion] = useState<Region>('cn');
  const [data, setData] = useState<MarketReviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((r: Region) => {
    setLoading(true);
    setError(null);
    setData(null);
    marketApi
      .getReview(r)
      .then(setData)
      .catch(() => setError('大盘数据获取失败，请稍后重试'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(region); }, [load, region]);

  const handleRefresh = () => {
    setRefreshing(true);
    setError(null);
    marketApi
      .refreshReview(region)
      .then(setData)
      .catch(() => setError('复盘刷新失败，请稍后重试'))
      .finally(() => setRefreshing(false));
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="sticky top-0 z-10 bg-base border-b border-white/5 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-white">大盘分析</h1>
          {/* A股/美股 切换 */}
          <div className="flex items-center gap-0.5 bg-elevated rounded-lg p-0.5">
            {(['cn', 'us'] as Region[]).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRegion(r)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  region === r ? 'bg-cyan/15 text-cyan' : 'text-muted-text hover:text-white'
                }`}
              >
                {REGION_LABELS[r]}
              </button>
            ))}
          </div>
          {data && (
            <p className="text-xs text-muted-text">
              {data.date}
              {data.cached && <span className="ml-2 text-cyan/60">已缓存</span>}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={handleRefresh}
          disabled={loading || refreshing}
          className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
        >
          {refreshing ? (
            <span className="w-3 h-3 border border-white/20 border-t-white rounded-full animate-spin" />
          ) : (
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          刷新复盘
        </button>
      </div>

      <div className="flex-1 px-4 py-4 space-y-4 max-w-3xl mx-auto w-full">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <div className="w-6 h-6 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
            <span className="ml-3 text-sm text-muted-text">正在获取大盘数据…</span>
          </div>
        )}

        {error && !loading && (
          <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
            {error}
          </div>
        )}

        {!loading && data && (
          <>
            <Card variant="bordered" padding="md">
              <h2 className="text-sm font-semibold text-white mb-3">主要指数</h2>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {data.indices.map((idx) => (
                  <div key={idx.code} className={`rounded-lg p-3 ${bgOf(idx.change_pct)}`}>
                    <p className="text-xs text-muted-text mb-1">{idx.name}</p>
                    <p className="text-lg font-mono font-semibold text-white">{fmt(idx.current)}</p>
                    <p className={`text-sm font-mono ${colorOf(idx.change_pct)}`}>
                      {fmtPct(idx.change_pct)}
                      <span className="text-xs ml-1">({fmt(idx.change)})</span>
                    </p>
                  </div>
                ))}
              </div>
            </Card>

            {data.up_count > 0 && (
              <Card variant="bordered" padding="md">
                <h2 className="text-sm font-semibold text-white mb-3">涨跌统计</h2>
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-3 text-center">
                  {[
                    { label: '上涨', value: data.up_count, color: 'text-[#ff4d4d]' },
                    { label: '下跌', value: data.down_count, color: 'text-[#00d46a]' },
                    { label: '平盘', value: data.flat_count, color: 'text-muted-text' },
                    { label: '涨停', value: data.limit_up_count, color: 'text-[#ff4d4d]' },
                    { label: '跌停', value: data.limit_down_count, color: 'text-[#00d46a]' },
                  ].map((item) => (
                    <div key={item.label}>
                      <p className="text-xs text-muted-text mb-1">{item.label}</p>
                      <p className={`text-xl font-mono font-bold ${item.color}`}>{item.value}</p>
                    </div>
                  ))}
                </div>
                {data.total_amount > 0 && (
                  <p className="mt-3 text-xs text-muted-text text-right">
                    两市成交额 <span className="text-white font-mono">{data.total_amount.toFixed(0)} 亿</span>
                  </p>
                )}
              </Card>
            )}

            {(data.top_sectors.length > 0 || data.bottom_sectors.length > 0) && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {data.top_sectors.length > 0 && (
                  <Card variant="bordered" padding="md">
                    <h2 className="text-sm font-semibold text-[#ff4d4d] mb-3">涨幅榜 Top5</h2>
                    <div className="space-y-2">
                      {data.top_sectors.map((s, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-white">{s.name}</span>
                          <span className="font-mono text-[#ff4d4d]">+{s.change_pct?.toFixed(2)}%</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
                {data.bottom_sectors.length > 0 && (
                  <Card variant="bordered" padding="md">
                    <h2 className="text-sm font-semibold text-[#00d46a] mb-3">跌幅榜 Top5</h2>
                    <div className="space-y-2">
                      {data.bottom_sectors.map((s, i) => (
                        <div key={i} className="flex items-center justify-between text-xs">
                          <span className="text-white">{s.name}</span>
                          <span className="font-mono text-[#00d46a]">{s.change_pct?.toFixed(2)}%</span>
                        </div>
                      ))}
                    </div>
                  </Card>
                )}
              </div>
            )}

            {data.review_text && (
              <Card variant="bordered" padding="md">
                <div className="flex items-center gap-2 mb-4">
                  <span className="flex items-center gap-1.5 rounded-md bg-cyan/10 px-2 py-0.5 text-xs font-medium text-cyan">
                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    AI 复盘
                  </span>
                  {data.generated_at && (
                    <span className="text-xs text-muted-text">
                      {new Date(data.generated_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })} 生成
                    </span>
                  )}
                </div>
                <MarketReviewMarkdown content={data.review_text} />
              </Card>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default MarketPage;
