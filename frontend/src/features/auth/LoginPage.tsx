import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../stores/auth";
import { AxiosError } from "axios";
import type { ApiError } from "../../api/types";

export default function LoginPage() {
  const navigate = useNavigate();
  const login = useAuthStore((s) => s.login);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof AxiosError && err.response?.data) {
        setError((err.response.data as ApiError).detail || "Login failed");
      } else {
        setError("Login failed — check your connection");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-grid">
        <section className="auth-lore hidden md:flex flex-col justify-between">
          <div>
            <span className="nm-panel-title">Closed-loop market sim</span>
            <h1 className="nm-page-title font-bold mt-4">
              Dungeon Gate Economy
            </h1>
            <p className="nm-page-subtitle mt-3 max-w-md">
              Trade gate shares, queue tick intents, and watch guild treasuries
              rise or crack under dungeon pressure.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-3 text-xs">
            <div className="nm-card p-3">
              <div className="nm-panel-title">Ticks</div>
              <div className="font-mono mt-1">Deterministic</div>
            </div>
            <div className="nm-card p-3">
              <div className="nm-panel-title">Assets</div>
              <div className="font-mono mt-1">Gate Shares</div>
            </div>
            <div className="nm-card p-3">
              <div className="nm-panel-title">Risk</div>
              <div className="font-mono mt-1">Collapse</div>
            </div>
          </div>
        </section>

        <div className="auth-card">
          <h1 className="text-2xl font-bold text-center mb-2">
            Enter the Exchange
          </h1>
          <p className="text-gray-400 text-center text-sm mb-6">
            Sign in to command your gates and guild positions.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div
                className="text-sm rounded px-3 py-2 border"
                style={{
                  background: "rgba(241, 104, 88, 0.14)",
                  borderColor: "rgba(241, 104, 88, 0.48)",
                  color: "var(--nm-bad)",
                }}
              >
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm text-gray-300 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm
                           focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm text-gray-300 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm
                           focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-50
                         text-white font-medium py-2 px-4 rounded transition-colors"
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>

          <p className="text-center text-sm text-gray-400 mt-6">
            No account?{" "}
            <Link to="/register" className="text-brand-400 hover:text-brand-300">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
