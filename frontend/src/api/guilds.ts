import client from "./client";
import type { GuildDetailResponse, GuildListResponse } from "./types";

export interface GuildListParams {
  status?: string;
  offset?: number;
  limit?: number;
}

export async function listGuilds(
  params: GuildListParams = {},
): Promise<GuildListResponse> {
  const { data } = await client.get<GuildListResponse>("/guilds", { params });
  return data;
}

export async function getGuild(guildId: string): Promise<GuildDetailResponse> {
  const { data } = await client.get<GuildDetailResponse>(`/guilds/${guildId}`);
  return data;
}
