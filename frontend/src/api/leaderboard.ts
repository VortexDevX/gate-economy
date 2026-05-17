import client from "./client";
import type {
  LeaderboardResponse,
  MyRankResponse,
  SeasonResponse,
  SeasonResultResponse,
} from "./types";

export interface LeaderboardParams {
  page?: number;
  page_size?: number;
}

export async function getLeaderboard(
  params: LeaderboardParams = {},
): Promise<LeaderboardResponse> {
  const { data } = await client.get<LeaderboardResponse>("/leaderboard", {
    params,
  });
  return data;
}

export async function getMyRank(): Promise<MyRankResponse> {
  const { data } = await client.get<MyRankResponse>("/leaderboard/me");
  return data;
}

export interface SeasonsParams {
  page?: number;
  page_size?: number;
}

export async function listSeasons(
  params: SeasonsParams = {},
): Promise<SeasonResponse[]> {
  const { data } = await client.get<SeasonResponse[]>("/seasons", { params });
  return data;
}

export async function getCurrentSeason(): Promise<SeasonResponse> {
  const { data } = await client.get<SeasonResponse>("/seasons/current");
  return data;
}

export interface SeasonResultsParams {
  page?: number;
  page_size?: number;
}

export async function getSeasonResults(
  seasonId: number,
  params: SeasonResultsParams = {},
): Promise<SeasonResultResponse[]> {
  const { data } = await client.get<SeasonResultResponse[]>(
    `/seasons/${seasonId}/results`,
    { params },
  );
  return data;
}
