import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getMe } from "../api/auth";
import { getSimulationStatus } from "../api/simulation";
import {
  listGates,
  getGate,
  listRankProfiles,
  type GateListParams,
} from "../api/gates";
import { listNews, type NewsListParams } from "../api/news";
import { listEvents, type EventListParams } from "../api/events";
import {
  getMyLedger,
  getMyPortfolio,
  type LedgerParams,
} from "../api/players";
import { listGuilds, getGuild, type GuildListParams } from "../api/guilds";
import {
  getLeaderboard,
  getMyRank,
  listSeasons,
  getCurrentSeason,
  getSeasonResults,
  type LeaderboardParams,
  type SeasonsParams,
  type SeasonResultsParams,
} from "../api/leaderboard";
import {
  getMarketHistory,
  getMarketOverview,
  getMarketPrice,
  getOrderBook,
  previewOrder,
  getTrades,
  type MarketOverviewParams,
  type TradeListParams,
} from "../api/market";
import { getMyOrders, type OrderListParams } from "../api/orders";
import {
  submitIntent,
  getMyIntents,
  type IntentListParams,
} from "../api/intents";
import {
  getConservationAudit,
  getTreasury,
  listAdminLedger,
  listAdminParameters,
  manageSeason,
  patchAdminParameter,
  pauseSimulation,
  resumeSimulation,
  triggerAdminEvent,
  type AdminLedgerParams,
} from "../api/admin";
import type { IntentCreate, OrderPreviewRequest } from "../api/types";

// --- Player ---

export function useMe(enabled = true) {
  return useQuery({
    queryKey: ["players", "me"],
    queryFn: getMe,
    enabled,
    staleTime: 10_000,
    refetchInterval: enabled ? 10_000 : false,
  });
}

// --- Simulation ---

export function useSimulationStatus() {
  return useQuery({
    queryKey: ["simulation", "status"],
    queryFn: getSimulationStatus,
    refetchInterval: 5_000,
  });
}

// --- Gates ---

export function useGates(params: GateListParams = {}) {
  return useQuery({
    queryKey: ["gates", params],
    queryFn: () => listGates(params),
    refetchInterval: 10_000,
  });
}

export function useGate(gateId: string) {
  return useQuery({
    queryKey: ["gates", gateId],
    queryFn: () => getGate(gateId),
    enabled: !!gateId,
    refetchInterval: 10_000,
  });
}

export function useGateRankProfiles() {
  return useQuery({
    queryKey: ["gates", "rank-profiles"],
    queryFn: listRankProfiles,
    staleTime: Infinity,
  });
}

// --- Guilds ---

export function useGuilds(params: GuildListParams = {}) {
  return useQuery({
    queryKey: ["guilds", params],
    queryFn: () => listGuilds(params),
    refetchInterval: 10_000,
  });
}

export function useGuild(guildId: string) {
  return useQuery({
    queryKey: ["guilds", guildId],
    queryFn: () => getGuild(guildId),
    enabled: !!guildId,
    refetchInterval: 10_000,
  });
}

// --- News ---

export function useNews(params: NewsListParams = {}) {
  return useQuery({
    queryKey: ["news", params],
    queryFn: () => listNews(params),
    refetchInterval: 10_000,
  });
}

// --- Events ---

export function useEvents(params: EventListParams = {}) {
  return useQuery({
    queryKey: ["events", params],
    queryFn: () => listEvents(params),
    refetchInterval: 10_000,
  });
}

// --- Ledger ---

export function useMyLedger(params: LedgerParams = {}) {
  return useQuery({
    queryKey: ["players", "me", "ledger", params],
    queryFn: () => getMyLedger(params),
    refetchInterval: 10_000,
  });
}

export function useMyPortfolio() {
  return useQuery({
    queryKey: ["players", "me", "portfolio"],
    queryFn: getMyPortfolio,
    refetchInterval: 10_000,
  });
}

// --- Market ---

export function useMarketOverview(params: MarketOverviewParams = {}) {
  return useQuery({
    queryKey: ["market", "overview", params],
    queryFn: () => getMarketOverview(params),
    refetchInterval: 10_000,
  });
}

export function useOrderPreview(preview: OrderPreviewRequest | null) {
  return useQuery({
    queryKey: ["market", "order-preview", preview],
    queryFn: () => previewOrder(preview as OrderPreviewRequest),
    enabled: preview !== null,
    staleTime: 1_000,
    retry: false,
  });
}

export function useMarketPrice(assetType: string, assetId: string) {
  return useQuery({
    queryKey: ["market", "price", assetType, assetId],
    queryFn: () => getMarketPrice(assetType, assetId),
    enabled: !!assetType && !!assetId,
    refetchInterval: 5_000,
  });
}

export function useOrderBook(assetType: string, assetId: string) {
  return useQuery({
    queryKey: ["market", "book", assetType, assetId],
    queryFn: () => getOrderBook(assetType, assetId),
    enabled: !!assetType && !!assetId,
    refetchInterval: 5_000,
  });
}

export function useTrades(
  assetType: string,
  assetId: string,
  params: TradeListParams = {},
) {
  return useQuery({
    queryKey: ["market", "trades", assetType, assetId, params],
    queryFn: () => getTrades(assetType, assetId, params),
    enabled: !!assetType && !!assetId,
    refetchInterval: 10_000,
  });
}

// --- Orders ---

export function useMyOrders(params: OrderListParams = {}) {
  return useQuery({
    queryKey: ["orders", "me", params],
    queryFn: () => getMyOrders(params),
    refetchInterval: 5_000,
  });
}

export function useMyIntents(params: IntentListParams = {}) {
  return useQuery({
    queryKey: ["intents", "me", params],
    queryFn: () => getMyIntents(params),
    refetchInterval: 5_000,
  });
}

export function useMarketHistory(
  assetType: string,
  assetId: string,
  limit = 60,
) {
  return useQuery({
    queryKey: ["market", "history", assetType, assetId, limit],
    queryFn: () => getMarketHistory(assetType, assetId, limit),
    enabled: !!assetType && !!assetId,
    refetchInterval: 10_000,
  });
}

// --- Leaderboard ---

export function useLeaderboard(params: LeaderboardParams = {}) {
  return useQuery({
    queryKey: ["leaderboard", params],
    queryFn: () => getLeaderboard(params),
    refetchInterval: 10_000,
  });
}

export function useMyRank() {
  return useQuery({
    queryKey: ["leaderboard", "me"],
    queryFn: getMyRank,
    refetchInterval: 10_000,
  });
}

export function useSeasons(params: SeasonsParams = {}) {
  return useQuery({
    queryKey: ["seasons", params],
    queryFn: () => listSeasons(params),
    refetchInterval: 30_000,
  });
}

export function useCurrentSeason() {
  return useQuery({
    queryKey: ["seasons", "current"],
    queryFn: getCurrentSeason,
    retry: false,
    refetchInterval: 10_000,
  });
}

export function useSeasonResults(
  seasonId: number | null,
  params: SeasonResultsParams = {},
) {
  return useQuery({
    queryKey: ["seasons", seasonId, "results", params],
    queryFn: () => getSeasonResults(seasonId as number, params),
    enabled: seasonId != null,
    refetchInterval: 30_000,
  });
}

// --- Intents ---

export function useSubmitIntent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (intent: IntentCreate) => submitIntent(intent),
    onSuccess: () => {
      // Accepted intents are visible immediately. Economic state remains
      // server-authoritative and refreshes on the actual tick event or polling.
      queryClient.invalidateQueries({ queryKey: ["intents", "me"] });
    },
  });
}

// --- Admin ---

export function useAdminParameters() {
  return useQuery({
    queryKey: ["admin", "parameters"],
    queryFn: listAdminParameters,
    refetchInterval: 15_000,
  });
}

export function useAdminTreasury() {
  return useQuery({
    queryKey: ["admin", "treasury"],
    queryFn: getTreasury,
    refetchInterval: 10_000,
  });
}

export function useConservationAudit() {
  return useQuery({
    queryKey: ["admin", "audit", "conservation"],
    queryFn: getConservationAudit,
    refetchInterval: 30_000,
  });
}

export function useAdminLedger(params: AdminLedgerParams = {}) {
  return useQuery({
    queryKey: ["admin", "ledger", params],
    queryFn: () => listAdminLedger(params),
    refetchInterval: 10_000,
  });
}

export function usePauseSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: pauseSimulation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simulation", "status"] });
    },
  });
}

export function useResumeSimulation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: resumeSimulation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["simulation", "status"] });
    },
  });
}

export function usePatchAdminParameter() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      patchAdminParameter(key, { value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "parameters"] });
      queryClient.invalidateQueries({ queryKey: ["simulation", "status"] });
    },
  });
}

export function useTriggerAdminEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (eventType: string) => triggerAdminEvent({ event_type: eventType }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["events"] });
      queryClient.invalidateQueries({ queryKey: ["news"] });
    },
  });
}

export function useManageSeason() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: manageSeason,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leaderboard"] });
      queryClient.invalidateQueries({ queryKey: ["seasons"] });
    },
  });
}
