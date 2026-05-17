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
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h1 className="text-2xl font-bold text-center mb-2">
          Dungeon Gate Economy
        </h1>
        <p className="text-gray-400 text-center text-sm mb-6">
          Sign in to your account
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="text-sm rounded px-3 py-2 border"
              style={{
                background: "linear-gradient(145deg, #ffe6e6, #ffdada)",
                borderColor: "#f3b1b1",
                color: "#9b2c2c",
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
  );
}
