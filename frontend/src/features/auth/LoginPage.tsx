import { useState, type FormEvent } from "react";
import {
  ArrowRight,
  Coins,
  Compass,
  KeyRound,
  Landmark,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AxiosError } from "axios";
import type { ApiError } from "../../api/types";
import { useAuthStore } from "../../stores/auth";

type LoginLocationState = {
  registered?: boolean;
};

const playSteps = [
  {
    icon: Compass,
    number: "01",
    title: "Scout a gate",
    copy: "Compare its share price, income, and chance of collapse.",
  },
  {
    icon: Coins,
    number: "02",
    title: "Take a position",
    copy: "Buy shares now or place an order at the price you want.",
  },
  {
    icon: TrendingUp,
    number: "03",
    title: "Build your fortune",
    copy: "Collect gate income, react to events, and grow into a guild.",
  },
];

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const login = useAuthStore((s) => s.login);
  const registered = Boolean(
    (location.state as LoginLocationState | null)?.registered,
  );

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
    <main className="auth-game-shell">
      <div className="auth-game-atmosphere" aria-hidden="true">
        <div className="auth-game-atmosphere-glow" />
        <div className="auth-game-atmosphere-runes" />
        <div className="auth-game-atmosphere-grid" />
      </div>

      <header className="auth-game-brand">
        <span className="auth-game-brand-mark" aria-hidden="true">
          <Landmark size={24} strokeWidth={1.7} />
        </span>
        <span className="auth-game-brand-copy">
          <strong>Dungeon Gate</strong>
          <small>The Obsidian Exchange</small>
        </span>
        <span className="auth-game-live-status">
          <span className="auth-game-live-pulse" aria-hidden="true" />
          Market simulation
        </span>
      </header>

      <div className="auth-game-layout">
        <section className="auth-game-intro" aria-labelledby="login-intro-title">
          <div className="auth-game-eyebrow">
            <Sparkles size={15} aria-hidden="true" />
            Your fortune waits beyond the gate
          </div>

          <h1 id="login-intro-title" className="auth-game-title">
            Trade the unknown.
            <span>Outlast the collapse.</span>
          </h1>
          <p className="auth-game-lead">
            Every dungeon gate produces wealth while it survives. Read the
            risk, buy its shares, and escape before the gate breaks.
          </p>

          <ol className="auth-game-loop" aria-label="How to play">
            {playSteps.map(({ icon: Icon, number, title, copy }) => (
              <li className="auth-game-loop-step" key={number}>
                <span className="auth-game-loop-icon" aria-hidden="true">
                  <Icon size={20} strokeWidth={1.8} />
                </span>
                <span className="auth-game-loop-number">{number}</span>
                <span className="auth-game-loop-copy">
                  <strong>{title}</strong>
                  <small>{copy}</small>
                </span>
              </li>
            ))}
          </ol>

          <div className="auth-game-assurance">
            <ShieldCheck size={19} aria-hidden="true" />
            <span>
              <strong>A living, closed-loop economy</strong>
              Every coin, trade, payout, and loss remains inside the game.
            </span>
          </div>
        </section>

        <section className="auth-game-panel" aria-labelledby="login-title">
          <div className="auth-game-panel-sigil" aria-hidden="true">
            <KeyRound size={27} strokeWidth={1.5} />
          </div>
          <div className="auth-game-panel-heading">
            <span className="auth-game-panel-kicker">Trader access</span>
            <h2 id="login-title">Enter the Exchange</h2>
            <p>Resume your portfolio and choose your next move.</p>
          </div>

          {registered && (
            <div className="auth-game-success" role="status">
              <ShieldCheck size={18} aria-hidden="true" />
              <span>
                <strong>Your trader account is ready.</strong>
                Sign in to begin your first gate operation.
              </span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-game-form">
            {error && (
              <div id="login-error" className="auth-game-error" role="alert">
                <span className="auth-game-error-mark" aria-hidden="true">
                  !
                </span>
                <span>{error}</span>
              </div>
            )}

            <div className="auth-game-field">
              <label htmlFor="email">
                <Mail size={15} aria-hidden="true" />
                Email address
              </label>
              <div className="auth-game-input-wrap">
                <Mail size={18} aria-hidden="true" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "login-error" : undefined}
                  placeholder="trader@example.com"
                />
              </div>
            </div>

            <div className="auth-game-field">
              <label htmlFor="password">
                <LockKeyhole size={15} aria-hidden="true" />
                Password
              </label>
              <div className="auth-game-input-wrap">
                <LockKeyhole size={18} aria-hidden="true" />
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "login-error" : undefined}
                  placeholder="Enter your password"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="auth-game-primary-action"
              aria-busy={loading}
            >
              <span>{loading ? "Opening the gate…" : "Enter the Exchange"}</span>
              <ArrowRight size={19} aria-hidden="true" />
            </button>
          </form>

          <div className="auth-game-divider">
            <span>New to the Exchange?</span>
          </div>
          <Link to="/register" className="auth-game-secondary-action">
            Create a trader account
            <ArrowRight size={17} aria-hidden="true" />
          </Link>

          <p className="auth-game-panel-footnote">
            Learn the market at your own pace. Your first objective will guide
            you from scouting to your first share.
          </p>
        </section>
      </div>
    </main>
  );
}
