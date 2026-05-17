import client from "./client";
import type { SimulationStatus } from "./types";

export async function getSimulationStatus(): Promise<SimulationStatus> {
  const { data } = await client.get<SimulationStatus>("/simulation/status");
  return data;
}
