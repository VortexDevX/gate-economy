import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../../api/auth";
import { AxiosError } from "axios";
import type { ApiError } from "../../api/types";

export default function RegisterPage() {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({
        username: username.trim(),
        email: email.trim().toLowerCase(),
        password,
      });
      navigate("/login", { state: { registered: true } });
    } catch (err) {
      if (err instanceof AxiosError && err.response?.data) {
        const data = err.response.data as
          | ApiError
          | { detail: Array<{ msg: string }> };
        if (typeof data.detail === "string") {
          setError(data.detail);
        } else if (Array.isArray(data.detail)) {
          setError(data.detail.map((d) => d.msg).join(". "));
        } else {
          setError("Registration failed");
        }
      } else {
        setError("Registration failed — check your connection");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-gray-900 border border-gray-800 rounded-lg p-6">
        <h1 className="text-2xl font-bold text-center mb-2">Create Account</h1>
        <p className="text-gray-400 text-center text-sm mb-6">
          Join the Dungeon Gate Economy
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div
              className="text-sm rounded px-3 py-2 border"
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
            <label
              htmlFor="username"
              className="block text-sm text-gray-300 mb-1"
            >
              Username
            </label>
            <input
              id="username"
              type="text"
              required
              minLength={3}
              maxLength={50}
              pattern="^[a-zA-Z0-9_-]+$"
              title="Letters, numbers, dashes, and underscores only"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm
                         focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </div>

          <div>
            <label
              htmlFor="reg-email"
              className="block text-sm text-gray-300 mb-1"
            >
              Email
            </label>
            <input
              id="reg-email"
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
              htmlFor="reg-password"
              className="block text-sm text-gray-300 mb-1"
            >
              Password
            </label>
            <input
              id="reg-password"
              type="password"
              required
              minLength={8}
              maxLength={128}
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
            {loading ? "Creating account…" : "Create Account"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-400 mt-6">
          Already have an account?{" "}
          <Link to="/login" className="text-brand-400 hover:text-brand-300">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
