import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useSubmitIntent } from "../../hooks/queries";

export default function CreateGuildPage() {
  const navigate = useNavigate();
  const submitIntent = useSubmitIntent();

  const [name, setName] = useState("");
  const [publicFloatPct, setPublicFloatPct] = useState("0.20");
  const [dividendPolicy, setDividendPolicy] = useState("MANUAL");
  const [autoDividendPct, setAutoDividendPct] = useState("0.10");
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    const floatVal = Number(publicFloatPct);
    const autoVal = Number(autoDividendPct);

    if (!name.trim()) {
      setErrorMsg("Guild name is required");
      return;
    }
    if (Number.isNaN(floatVal) || floatVal < 0 || floatVal > 0.49) {
      setErrorMsg("public_float_pct must be between 0.00 and 0.49");
      return;
    }
    if (dividendPolicy === "AUTO_FIXED_PCT") {
      if (Number.isNaN(autoVal) || autoVal <= 0 || autoVal > 1) {
        setErrorMsg("auto_dividend_pct must be > 0 and <= 1.0");
        return;
      }
    }

    const payload: Record<string, unknown> = {
      name: name.trim(),
      public_float_pct: floatVal,
      dividend_policy: dividendPolicy,
    };
    if (dividendPolicy === "AUTO_FIXED_PCT") {
      payload.auto_dividend_pct = autoVal;
    }

    try {
      await submitIntent.mutateAsync({
        intent_type: "CREATE_GUILD",
        payload,
      });
      setSuccessMsg(
        "Create guild intent queued. The guild will appear after the next simulation tick processes it.",
      );
      setTimeout(() => navigate("/guilds"), 1200);
    } catch {
      setErrorMsg("Failed to submit create guild intent");
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div><h1 className="nm-page-title font-bold">Create Guild</h1><p className="nm-page-subtitle mt-1">Define the treasury and token policy before launching public shares.</p></div>
      <p className="text-sm text-gray-400">
        This submits a CREATE_GUILD intent and is processed on the next tick.
      </p>

      <form
        onSubmit={handleSubmit}
        className="bg-gray-900 border border-gray-800 rounded-lg p-5 space-y-4"
      >
        <Field label="Guild Name">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                       focus:outline-none focus:border-brand-500"
            placeholder="e.g. Iron Covenant"
          />
        </Field>

        <Field label="Public Float % (0.00 to 0.49)">
          <input
            type="number"
            min="0"
            max="0.49"
            step="0.01"
            value={publicFloatPct}
            onChange={(e) => setPublicFloatPct(e.target.value)}
            className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                       focus:outline-none focus:border-brand-500"
          />
        </Field>

        <Field label="Dividend Policy">
          <select
            value={dividendPolicy}
            onChange={(e) => setDividendPolicy(e.target.value)}
            className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                       focus:outline-none focus:border-brand-500"
          >
            <option value="MANUAL">MANUAL</option>
            <option value="AUTO_FIXED_PCT">AUTO_FIXED_PCT</option>
          </select>
        </Field>

        {dividendPolicy === "AUTO_FIXED_PCT" && (
          <Field label="Auto Dividend % (0.01 to 1.00)">
            <input
              type="number"
              min="0.01"
              max="1"
              step="0.01"
              value={autoDividendPct}
              onChange={(e) => setAutoDividendPct(e.target.value)}
              className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm
                         focus:outline-none focus:border-brand-500"
            />
          </Field>
        )}

        {errorMsg && (
          <div className="text-xs text-red-300 bg-red-900/30 border border-red-800 rounded px-3 py-2">
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div className="text-xs text-green-300 bg-green-900/30 border border-green-800 rounded px-3 py-2">
            {successMsg}
          </div>
        )}

        <button
          type="submit"
          disabled={submitIntent.isPending}
          className="w-full bg-brand-600 hover:bg-brand-500 text-white text-sm font-medium
                     py-2 rounded disabled:opacity-50"
        >
          {submitIntent.isPending ? "Submitting..." : "Submit Create Guild Intent"}
        </button>
      </form>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <div className="text-xs text-gray-400 mb-1">{label}</div>
      {children}
    </label>
  );
}

