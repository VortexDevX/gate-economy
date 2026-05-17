import client from "./client";
import type { IntentCreate, IntentListResponse, IntentResponse } from "./types";

export async function submitIntent(
  intent: IntentCreate,
): Promise<IntentResponse> {
  const { data } = await client.post<IntentResponse>("/intents", intent);
  return data;
}

export interface IntentListParams {
  limit?: number;
  offset?: number;
}

export async function getMyIntents(
  params: IntentListParams = {},
): Promise<IntentListResponse> {
  const { data } = await client.get<IntentListResponse>("/intents/me", {
    params,
  });
  return data;
}
