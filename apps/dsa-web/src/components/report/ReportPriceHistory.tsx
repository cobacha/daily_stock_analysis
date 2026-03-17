import React, { useState, useEffect, useMemo } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { stocksApi, type KLineData } from '../../api/stocks';
import { Card } from '../common';

interface ReportPriceHistoryProps {
  stockCode: string;
}

interface ChartPoint {
  date: string;
  close: number;
  label: string;
}

type PeriodKey = 'today' | '5d' | '10d' | 'month' | 'quarter' | '1y';

interface PeriodConfig {
  key: PeriodKey;
  label: string;
  statLabels: [string, string, string, string];
  filter: (data: KLineData[], now: Date) => KLineData[];
  /** X 轴标签格式 */
  xLabel: (date: string, idx: number, total: number) => string;
}

// 格式化日期 yyyy-mm-dd -> MM/DD
const mmdd = (d: string) => d.slice(5).replace('-', '/');
// 格式化日期 -> MM-DD
const mmdd2 = (d: string) => d.slice(5);

const PERIODS: PeriodConfig[] = [
  {
    key: 'today',
    label: '今日',
    statLabels: ['开盘价', '收盘价', '最高价', '最低价'],
    filter: (data, now) => {
      const todayStr = now.toISOString().slice(0, 10);
      const today = data.filter((d) => d.date === todayStr);
      // 若今日无数据（休市），取最近一个交易日
      return today.length > 0 ? today : data.slice(-1);
    },
    xLabel: (date) => date.slice(5),
  },
  {
    key: '5d',
    label: '5日',
    statLabels: ['区间开盘', '最新收盘', '期间最高', '期间最低'],
    filter: (data) => data.slice(-5),
    xLabel: (date, idx, total) => (idx === 0 || idx === total - 1 ? mmdd(date) : ''),
  },
  {
    key: '10d',
    label: '10日',
    statLabels: ['区间开盘', '最新收盘', '期间最高', '期间最低'],
    filter: (data) => data.slice(-10),
    xLabel: (date, idx, total) =>
      idx === 0 || idx === Math.floor(total / 2) || idx === total - 1 ? mmdd(date) : '',
  },
  {
    key: 'month',
    label: '本月',
    statLabels: ['月初开盘', '最新收盘', '月内最高', '月内最低'],
    filter: (data, now) => {
      const prefix = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
      return data.filter((d) => d.date.startsWith(prefix));
    },
    xLabel: (date, idx, total) => {
      const step = Math.max(1, Math.floor(total / 4));
      return idx % step === 0 || idx === total - 1 ? mmdd2(date) : '';
    },
  },
  {
    key: 'quarter',
    label: '季度',
    statLabels: ['季初开盘', '最新收盘', '季内最高', '季内最低'],
    filter: (data, now) => {
      // 获取本季度第一天
      const quarter = Math.floor(now.getMonth() / 3);
      const quarterStartMonth = quarter * 3 + 1;
      const quarterStart = `${now.getFullYear()}-${String(quarterStartMonth).padStart(2, '0')}`;
      return data.filter((d) => d.date >= quarterStart);
    },
    xLabel: (date, idx, total) => {
      const step = Math.max(1, Math.floor(total / 4));
      return idx % step === 0 || idx === total - 1 ? mmdd2(date) : '';
    },
  },
  {
    key: '1y',
    label: '年度',
    statLabels: ['年初开盘', '最新收盘', '年内最高', '年内最低'],
    filter: (data, now) => {
      const yearStart = `${now.getFullYear()}-01`;
      return data.filter((d) => d.date >= yearStart);
    },
    xLabel: (date, idx, total) => {
      // 每隔约30条（约1个月）显示一个月份标签
      const step = Math.max(1, Math.floor(total / 12));
      return idx % step === 0 || idx === total - 1
        ? `${date.slice(5, 7)}月`
        : '';
    },
  },
];

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-elevated border border-white/10 [[data-theme=light]_&]:border-black/8 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-muted-text mb-0.5">{label}</p>
      <p className="text-white font-mono font-semibold">{payload[0].value.toFixed(2)}</p>
    </div>
  );
};

export const ReportPriceHistory: React.FC<ReportPriceHistoryProps> = ({ stockCode }) => {
  const [allKlines, setAllKlines] = useState<KLineData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePeriod, setActivePeriod] = useState<PeriodKey>('quarter');

  // 拉取半年数据（覆盖所有周期），切换周期只做客户端过滤
  useEffect(() => {
    if (!stockCode) return;
    let cancelled = false;
    setIsLoading(true);
    setError(null);

    const days = activePeriod === '1y' ? 365 : 180;
    stocksApi
      .getHistory(stockCode, days)
      .then((res) => {
        if (cancelled) return;
        setAllKlines(res.data);
      })
      .catch((err) => {
        if (cancelled) return;
        console.error('获取价格历史失败:', err);
        setError('价格数据获取失败');
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => { cancelled = true; };
  }, [stockCode, activePeriod]);

  const period = PERIODS.find((p) => p.key === activePeriod)!;

  const { chartData, statStart, statEnd, statHigh, statLow, changePct, isPositive } =
    useMemo(() => {
      const now = new Date();
      const klines = period.filter(allKlines, now);

      if (klines.length === 0) {
        return { chartData: [], statStart: null, statEnd: null, statHigh: null, statLow: null, changePct: null, isPositive: true };
      }

      const first = klines[0];
      const last = klines[klines.length - 1];
      const statHigh = Math.max(...klines.map((k) => k.high));
      const statLow = Math.min(...klines.map((k) => k.low));
      // 今日模式用当日开盘价，其他周期用第一天开盘价作为基准
      const basePrice = first.open;
      const changePct = ((last.close - basePrice) / basePrice) * 100;

      const chartData: ChartPoint[] = klines.map((k, i) => ({
        date: k.date,
        close: k.close,
        label: period.xLabel(k.date, i, klines.length),
      }));

      return {
        chartData,
        statStart: basePrice,
        statEnd: last.close,
        statHigh,
        statLow,
        changePct,
        isPositive: changePct >= 0,
      };
    }, [allKlines, period]);

  const colorUp = '#ff4d4d';
  const colorDown = '#00d46a';
  const lineColor = isPositive ? colorUp : colorDown;
  const gradId = `ph-grad-${stockCode.replace(/[^a-zA-Z0-9]/g, '')}-${activePeriod}`;

  const fmt = (v: number | null) => (v === null ? '--' : v.toFixed(2));
  const fmtPct = (v: number | null) => {
    if (v === null) return '--';
    return `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`;
  };

  return (
    <Card variant="bordered" padding="md" className="text-left">
      {/* 标题栏 */}
      <div className="mb-3 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-baseline gap-2">
          <span className="label-uppercase">PRICE</span>
          <h3 className="text-base font-semibold text-white">价格走势</h3>
        </div>

        {/* 周期选择器 */}
        <div className="flex items-center gap-1 bg-elevated rounded-lg p-0.5">
          {PERIODS.map((p) => (
            <button
              key={p.key}
              type="button"
              onClick={() => setActivePeriod(p.key)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                activePeriod === p.key
                  ? 'bg-cyan/15 text-cyan'
                  : 'text-muted-text hover:text-white'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* 涨跌幅 badge */}
      {!isLoading && !error && changePct !== null && (
        <div className="mb-2 flex items-center gap-2">
          <span
            className={`text-sm font-mono font-bold ${isPositive ? 'text-[#ff4d4d]' : 'text-[#00d46a]'}`}
          >
            {fmtPct(changePct)}
          </span>
          <span className="text-xs text-muted-text">
            {period.label === '今日' ? '当日涨跌' : `${period.label}涨跌`}
          </span>
        </div>
      )}

      {/* 内容区 */}
      {isLoading ? (
        <div className="flex items-center justify-center h-28">
          <div className="w-6 h-6 border-2 border-cyan/20 border-t-cyan rounded-full animate-spin" />
        </div>
      ) : error ? (
        <div className="flex items-center justify-center h-28 text-xs text-muted-text">{error}</div>
      ) : chartData.length === 0 ? (
        <div className="flex items-center justify-center h-28 text-xs text-muted-text">
          暂无 {period.label} 行情数据
        </div>
      ) : (
        <>
          {/* 图表 */}
          <div className="h-28 mb-4 -mx-1">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={lineColor} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={lineColor} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fill: '#6b7280', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  width={52}
                  tickFormatter={(v: number) => v.toFixed(0)}
                />
                <Tooltip content={<CustomTooltip />} />
                {statStart !== null && (
                  <ReferenceLine
                    y={statStart}
                    stroke="rgba(255,255,255,0.15)"
                    strokeDasharray="4 3"
                  />
                )}
                <Area
                  type="monotone"
                  dataKey="close"
                  stroke={lineColor}
                  strokeWidth={1.5}
                  fill={`url(#${gradId})`}
                  dot={chartData.length === 1 ? { r: 4, fill: lineColor, strokeWidth: 0 } : false}
                  activeDot={{ r: 3, fill: lineColor, strokeWidth: 0 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* 关键数据 */}
          <div className="grid grid-cols-4 gap-2">
            {[
              { label: period.statLabels[0], value: fmt(statStart), color: 'text-white' },
              { label: period.statLabels[1], value: fmt(statEnd), color: isPositive ? 'text-[#ff4d4d]' : 'text-[#00d46a]' },
              { label: period.statLabels[2], value: fmt(statHigh), color: 'text-[#ff4d4d]' },
              { label: period.statLabels[3], value: fmt(statLow), color: 'text-[#00d46a]' },
            ].map((item) => (
              <div key={item.label} className="text-center">
                <p className="text-[10px] text-muted-text mb-0.5">{item.label}</p>
                <p className={`text-sm font-mono font-medium ${item.color}`}>{item.value}</p>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  );
};
