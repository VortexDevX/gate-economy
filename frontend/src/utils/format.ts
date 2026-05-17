/**
 * Convert micro-units to display currency string.
 * 1 currency = 1,000,000 micro-units.
 */
export function formatCurrency(micro: number): string {
  const units = micro / 1_000_000;
  return units.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Compact format for large values (e.g., 1.5M, 250K).
 */
export function formatCurrencyCompact(micro: number): string {
  const units = micro / 1_000_000;
  if (units >= 1_000_000) return `${(units / 1_000_000).toFixed(1)}M`;
  if (units >= 1_000) return `${(units / 1_000).toFixed(1)}K`;
  return units.toFixed(2);
}

/**
 * Format ISO date string to short localized display.
 */
export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Format stability value as percentage string.
 */
export function formatStability(value: number): string {
  return `${value.toFixed(1)}%`;
}

/**
 * Format a 0-1 ratio as display percentage.
 */
export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * Truncate UUID for display.
 */
export function shortId(uuid: string): string {
  return uuid.slice(0, 8);
}
