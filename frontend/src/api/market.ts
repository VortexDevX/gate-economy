import client from "./client";
import type {
  MarketHistoryResponse,
  MarketOverviewResponse,
  MarketPriceResponse,
  OrderBookResponse,
  OrderPreviewRequest,
  OrderPreviewResponse,
  TradeListResponse,
} from "./types";

export interface MarketOverviewParams {
  status?: string;
  rank?: string;
  sort_by?: "VOLUME" | "YIELD" | "RISK" | "NEWEST";
  offset?: number;
  limit?: number;
}

export async function getMarketOverview(
  params: MarketOverviewParams = {},
): Promise<MarketOverviewResponse> {
  const { data } = await client.get<MarketOverviewResponse>("/market/overview", {
    params,
  });
  return data;
}

export async function previewOrder(
  body: OrderPreviewRequest,
): Promise<OrderPreviewResponse> {
  const { data } = await client.post<OrderPreviewResponse>(
    "/market/order-preview",
    body,
  );
  return data;
}

export async function getMarketPrice(
  assetType: string,
  assetId: string,
): Promise<MarketPriceResponse> {
  const { data } = await client.get<MarketPriceResponse>(
    `/market/${assetType}/${assetId}`,
  );
  return data;
}

export async function getOrderBook(
  assetType: string,
  assetId: string,
): Promise<OrderBookResponse> {
  const { data } = await client.get<OrderBookResponse>(
    `/market/${assetType}/${assetId}/book`,
  );
  return data;
}

export interface TradeListParams {
  limit?: number;
  offset?: number;
}

export async function getTrades(
  assetType: string,
  assetId: string,
  params: TradeListParams = {},
): Promise<TradeListResponse> {
  const { data } = await client.get<TradeListResponse>(
    `/market/${assetType}/${assetId}/trades`,
    { params },
  );
  return data;
}

export async function getMarketHistory(
  assetType: string,
  assetId: string,
  limit = 60,
): Promise<MarketHistoryResponse> {
  const { data } = await client.get<MarketHistoryResponse>(
    `/market/${assetType}/${assetId}/history`,
    { params: { limit } },
  );
  return data;
}
