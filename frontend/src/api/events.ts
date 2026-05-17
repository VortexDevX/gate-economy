import client from "./client";
import type { EventListResponse } from "./types";

export interface EventListParams {
  limit?: number;
  offset?: number;
  event_type?: string;
}

export async function listEvents(
  params: EventListParams = {},
): Promise<EventListResponse> {
  const { data } = await client.get<EventListResponse>("/events", { params });
  return data;
}
