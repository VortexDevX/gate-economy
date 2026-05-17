import client from "./client";
import type {
  GateListResponse,
  GateDetailResponse,
  GateRankProfileResponse,
} from "./types";

export interface GateListParams {
  status?: string;
  rank?: string;
  offset?: number;
  limit?: number;
}

export async function listGates(
  params: GateListParams = {},
): Promise<GateListResponse> {
  const { data } = await client.get<GateListResponse>("/gates", { params });
  return data;
}

export async function getGate(gateId: string): Promise<GateDetailResponse> {
  const { data } = await client.get<GateDetailResponse>(`/gates/${gateId}`);
  return data;
}

export async function listRankProfiles(): Promise<GateRankProfileResponse[]> {
  const { data } = await client.get<GateRankProfileResponse[]>(
    "/gates/rank-profiles",
  );
  return data;
}
