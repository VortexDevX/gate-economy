import client from "./client";
import type {
  AdminLedgerEntry,
  ConservationAuditResponse,
  EventTriggerRequest,
  EventTriggerResponse,
  ParameterResponse,
  ParameterUpdateRequest,
  SeasonActionRequest,
  SeasonActionResponse,
  SimulationControlResponse,
  TreasuryResponse,
} from "./types";

export interface AdminLedgerParams {
  entry_type?: string;
  player_id?: string;
  tick_id?: number;
  limit?: number;
  offset?: number;
}

export async function pauseSimulation(): Promise<SimulationControlResponse> {
  const { data } = await client.post<SimulationControlResponse>(
    "/admin/simulation/pause",
  );
  return data;
}

export async function resumeSimulation(): Promise<SimulationControlResponse> {
  const { data } = await client.post<SimulationControlResponse>(
    "/admin/simulation/resume",
  );
  return data;
}

export async function listAdminParameters(): Promise<ParameterResponse[]> {
  const { data } = await client.get<ParameterResponse[]>("/admin/parameters");
  return data;
}

export async function patchAdminParameter(
  key: string,
  body: ParameterUpdateRequest,
): Promise<ParameterResponse> {
  const { data } = await client.patch<ParameterResponse>(
    `/admin/parameters/${encodeURIComponent(key)}`,
    body,
  );
  return data;
}

export async function triggerAdminEvent(
  body: EventTriggerRequest,
): Promise<EventTriggerResponse> {
  const { data } = await client.post<EventTriggerResponse>(
    "/admin/events/trigger",
    body,
  );
  return data;
}

export async function getTreasury(): Promise<TreasuryResponse> {
  const { data } = await client.get<TreasuryResponse>("/admin/treasury");
  return data;
}

export async function getConservationAudit(): Promise<ConservationAuditResponse> {
  const { data } = await client.get<ConservationAuditResponse>(
    "/admin/audit/conservation",
  );
  return data;
}

export async function listAdminLedger(
  params: AdminLedgerParams = {},
): Promise<AdminLedgerEntry[]> {
  const { data } = await client.get<AdminLedgerEntry[]>("/admin/ledger", {
    params,
  });
  return data;
}

export async function manageSeason(
  body: SeasonActionRequest,
): Promise<SeasonActionResponse> {
  const { data } = await client.post<SeasonActionResponse>("/admin/seasons", body);
  return data;
}
