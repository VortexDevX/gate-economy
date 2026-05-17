import client from "./client";
import type {
  MarketPriceResponse,
  OrderBookResponse,
  TradeListResponse,
} from "./types";

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
