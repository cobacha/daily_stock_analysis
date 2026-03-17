// apps/dsa-web/src/api/market.ts
import apiClient from './index';

export type MarketIndexData = {
  code: string;
  name: string;
  current: number;
  change: number;
  change_pct: number;
  open: number;
  high: number;
  low: number;
  volume: number;
  amount: number;
  amplitude: number;
};

export type SectorData = {
  name: string;
  change_pct: number;
  [key: string]: unknown;
};

export type MarketReviewResponse = {
  region: string;
  cached: boolean;
  date: string;
  indices: MarketIndexData[];
  up_count: number;
  down_count: number;
  flat_count: number;
  limit_up_count: number;
  limit_down_count: number;
  total_amount: number;
  top_sectors: SectorData[];
  bottom_sectors: SectorData[];
  review_text: string;
  generated_at: string | null;
};

export const marketApi = {
  async getReview(region = 'cn'): Promise<MarketReviewResponse> {
    const resp = await apiClient.get('/api/v1/market/review', {
      params: { region },
      timeout: 120000, // 首次生成可能需要较长时间
    });
    return resp.data as MarketReviewResponse;
  },

  async refreshReview(region = 'cn'): Promise<MarketReviewResponse> {
    const resp = await apiClient.post('/api/v1/market/review/refresh', null, {
      params: { region },
      timeout: 120000,
    });
    return resp.data as MarketReviewResponse;
  },
};
