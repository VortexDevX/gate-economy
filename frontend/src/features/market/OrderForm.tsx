import { useState, useEffect, type FormEvent } from "react";
import { useSubmitIntent } from "../../hooks/queries";
import { useAuthStore } from "../../stores/auth";
import { formatCurrency } from "../../utils/format";
import type { MarketPriceResponse } from "../../api/types";

interface Props {
  assetType: string;
  assetId: string;
  marketPrice: MarketPriceResponse | undefined;
  prefilledPrice?: number | null;
  visibleAskQty?: number;
}

export default function OrderForm({
  assetType,
  assetId,
  marketPrice,
  prefilledPrice,
  visibleAskQty = 0,
}: Props) {
  const player = useAuthStore((s) => s.player);
  const submitIntent = useSubmitIntent();

  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [quantity, setQuantity] = useState("1");
  const [priceStr, setPriceStr] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  // Apply prefilled price from order book click
  useEffect(() => {
    if (prefilledPrice != null) {
      setPriceStr((prefilledPrice / 1_000_000).toFixed(6));
    }
  }, [prefilledPrice]);

  // Auto-clear success message
  useEffect(() => {
    if (successMsg) {
      const timer = setTimeout(() => setSuccessMsg(""), 8_000);
      return () => clearTimeout(timer);
    }
  }, [successMsg]);

  const priceMicro = priceStr
    ? Math.round(parseFloat(priceStr) * 1_000_000)
    : 0;
  const qty = parseInt(quantity, 10) || 0;
  const totalMicro = priceMicro * qty;

  // Rough fee estimate (base 0.5%)
  const estFeeMicro = Math.round(totalMicro * 0.005);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    if (qty <= 0) {
      setErrorMsg("Quantity must be at least 1");
      return;
    }
    if (priceMicro <= 0) {
      setErrorMsg("Price must be greater than 0");
      return;
    }
    if (side === "BUY" && player && player.balance_micro < totalMicro + estFeeMicro) {
      setErrorMsg("Insufficient balance for estimated escrow.");
      return;
    }
    if (side === "BUY" && visibleAskQty > 0 && qty > visibleAskQty) {
      setErrorMsg(
        `Requested quantity exceeds visible asks (${visibleAskQty}). Reduce quantity or wait for more liquidity.`,
      );
      return;
    }

    try {
      const intent = await submitIntent.mutateAsync({
        intent_type: "PLACE_ORDER",
        payload: {
          asset_type: assetType,
          asset_id: assetId,
          side,
          quantity: qty,
          price_limit_micro: priceMicro,
        },
      });
      setSuccessMsg(
        `Intent queued (id ${intent.id.slice(0, 8)}). This is not an immediate fill. Check Orders -> Intent Results after the next tick.`,
      );
      setQuantity("1");
      setPriceStr("");
    } catch {
      setErrorMsg("Failed to submit order intent");
    }
  };

  // Suggest price from market data
  const suggestedPrice =
    side === "BUY"
      ? (marketPrice?.best_ask_micro ?? marketPrice?.last_price_micro)
      : (marketPrice?.best_bid_micro ?? marketPrice?.last_price_micro);

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Info note */}
      <div className="text-xs text-gray-500 bg-gray-800/30 rounded px-3 py-2">
        Submitting here queues an intent. The engine validates and executes it on
        the next simulation tick (~5s).
      </div>

      {/* Side toggle */}
      <div className="flex rounded overflow-hidden border border-gray-700">
        <button
          type="button"
          onClick={() => setSide("BUY")}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            side === "BUY"
              ? "bg-green-900/50 text-green-300"
              : "bg-gray-900 text-gray-400 hover:text-gray-200"
          }`}
        >
          BUY
        </button>
        <button
          type="button"
          onClick={() => setSide("SELL")}
          className={`flex-1 py-2 text-sm font-medium transition-colors ${
            side === "SELL"
              ? "bg-red-900/50 text-red-300"
              : "bg-gray-900 text-gray-400 hover:text-gray-200"
          }`}
        >
          SELL
        </button>
      </div>

      {/* Quantity */}
      <div>
        <label className="block text-xs text-gray-400 mb-1">
          Quantity (shares)
        </label>
        <input
          type="number"
          min="1"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-mono
                     focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Price */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs text-gray-400">Price per share (¤)</label>
          {suggestedPrice && (
            <button
              type="button"
              onClick={() =>
                setPriceStr((suggestedPrice / 1_000_000).toFixed(6))
              }
              className="text-xs text-brand-400 hover:text-brand-300"
            >
              Use {side === "BUY" ? "ask" : "bid"}: ¤{" "}
              {formatCurrency(suggestedPrice)}
            </button>
          )}
        </div>
        <input
          type="number"
          step="0.000001"
          min="0.000001"
          value={priceStr}
          onChange={(e) => setPriceStr(e.target.value)}
          placeholder={
            suggestedPrice
              ? (suggestedPrice / 1_000_000).toFixed(6)
              : "0.000000"
          }
          className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-mono
                     focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Estimate */}
      {priceMicro > 0 && qty > 0 && (
        <div className="bg-gray-800/50 rounded p-3 space-y-1 text-xs">
          <div className="flex justify-between">
            <span className="text-gray-400">
              {side === "BUY" ? "Total Cost" : "Proceeds"}
            </span>
            <span className="font-mono">¤ {formatCurrency(totalMicro)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Est. Fee (~0.5%)</span>
            <span className="font-mono text-gray-500">
              ¤ {formatCurrency(estFeeMicro)}
            </span>
          </div>
          {side === "BUY" && (
            <div className="flex justify-between border-t border-gray-700 pt-1">
              <span className="text-gray-400">Est. Escrow</span>
              <span className="font-mono">
                ¤ {formatCurrency(totalMicro + estFeeMicro)}
              </span>
            </div>
          )}
          {player && side === "BUY" && (
            <div className="flex justify-between">
              <span className="text-gray-400">Your Balance</span>
              <span
                className={`font-mono ${
                  player.balance_micro < totalMicro + estFeeMicro
                    ? "text-red-400"
                    : "text-gray-300"
                }`}
              >
                ¤ {formatCurrency(player.balance_micro)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Messages */}
      {side === "BUY" && visibleAskQty > 0 && (
        <div className="text-xs text-gray-400 bg-gray-800/40 border border-gray-700 rounded px-3 py-2">
          Visible ask liquidity: {visibleAskQty} shares
        </div>
      )}
      {errorMsg && (
        <div className="bg-red-900/30 border border-red-800 text-red-300 text-xs rounded px-3 py-2">
          {errorMsg}
        </div>
      )}
      {successMsg && (
        <div className="bg-green-900/30 border border-green-800 text-green-300 text-xs rounded px-3 py-2">
          {successMsg}
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={submitIntent.isPending}
        className={`w-full font-medium py-2 px-4 rounded text-sm transition-colors disabled:opacity-50 ${
          side === "BUY"
            ? "bg-green-700 hover:bg-green-600 text-white"
            : "bg-red-700 hover:bg-red-600 text-white"
        }`}
      >
        {submitIntent.isPending ? "Submitting…" : `Place ${side} Order`}
      </button>
    </form>
  );
}
