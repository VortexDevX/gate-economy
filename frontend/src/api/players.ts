import client from "./client";
import type { PaginatedLedger } from "./types";

export interface LedgerParams {
  page?: number;
  size?: number;
}

export async function getMyLedger(
  params: LedgerParams = {},
): Promise<PaginatedLedger> {
  const { data } = await client.get<PaginatedLedger>("/players/me/ledger", {
    params,
  });
  return data;
}
