import client from "./client";
import type { NewsListResponse } from "./types";

export interface NewsListParams {
  limit?: number;
  offset?: number;
  category?: string;
  min_importance?: number;
}

export async function listNews(
  params: NewsListParams = {},
): Promise<NewsListResponse> {
  const { data } = await client.get<NewsListResponse>("/news", { params });
  return data;
}
