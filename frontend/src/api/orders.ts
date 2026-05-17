import client from "./client";
import type { OrderListResponse } from "./types";

export interface OrderListParams {
  limit?: number;
  offset?: number;
}

export async function getMyOrders(
  params: OrderListParams = {},
): Promise<OrderListResponse> {
  const { data } = await client.get<OrderListResponse>("/orders/me", {
    params,
  });
  return data;
}
