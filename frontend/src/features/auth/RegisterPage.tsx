import { useState, type FormEvent } from "react";
import {
  ArrowRight,
  Coins,
  CircleAlert,
  Compass,
  Gem,
  Landmark,
  LockKeyhole,
  Mail,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UserRound,
} from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { AxiosError } from "axios";
import { register } from "../../api/auth";
import type { ApiError } from "../../api/types";

const playSteps = [
  {
    icon: Compass,
    number: "01",
    title: "Find opportunity",
    copy: "Scout active gates and see their price, income, and stability.",
  },
  {
    icon: Coins,
    number: "02",
    title: "Buy gate shares",
    copy: "Own a piece of a gate and receive income while it survives.",
  },
  {
    icon: TrendingUp,
    number: "03",
    title: "Grow your power",
    copy: "Reinvest your gains, trade the market, or build a guild.",
  },
];

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
    <main className="auth-game-shell auth-game-shell-register">
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
        <section
          className="auth-game-intro"
          aria-labelledby="register-intro-title"
        >
          <div className="auth-game-eyebrow">
            <Sparkles size={15} aria-hidden="true" />
            Your first gate operation begins here
          </div>

          <h1 id="register-intro-title" className="auth-game-title">
            Enter with a plan.
            <span>Leave with a fortune.</span>
          </h1>
          <p className="auth-game-lead">
            Gates create wealth, but none last forever. Buy carefully, collect
            income each cycle, and sell before instability becomes collapse.
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
            <Gem size={19} aria-hidden="true" />
            <span>
              <strong>Risk creates opportunity</strong>
              High-yield gates can enrich you quickly—or collapse with your
              investment still inside.
            </span>
          </div>
        </section>

        <section className="auth-game-panel" aria-labelledby="register-title">
          <div className="auth-game-panel-sigil" aria-hidden="true">
            <UserRound size={27} strokeWidth={1.5} />
          </div>
          <div className="auth-game-panel-heading">
            <span className="auth-game-panel-kicker">New market entrant</span>
            <h2 id="register-title">Claim Your Seat</h2>
            <p>Create a trader identity and begin your first objective.</p>
          </div>

          <form onSubmit={handleSubmit} className="auth-game-form">
            {error && (
              <div id="register-error" className="auth-game-error" role="alert">
                <span className="auth-game-error-mark" aria-hidden="true">
                  <CircleAlert size={18} />
                </span>
                <span>{error}</span>
              </div>
            )}

            <div className="auth-game-field">
              <label htmlFor="username">
                <UserRound size={15} aria-hidden="true" />
                Trader name
              </label>
              <div className="auth-game-input-wrap">
                <UserRound size={18} aria-hidden="true" />
                <input
                  id="username"
                  name="username"
                  type="text"
                  autoComplete="username"
                  required
                  minLength={3}
                  maxLength={50}
                  pattern={"^[a-zA-Z0-9_\\-]+$"}
                  title="Letters, numbers, dashes, and underscores only"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={
                    error ? "username-help register-error" : "username-help"
                  }
                  placeholder="Choose your market name"
                />
              </div>
              <small id="username-help" className="auth-game-field-help">
                3–50 characters. Use letters, numbers, dashes, or underscores.
              </small>
            </div>

            <div className="auth-game-field">
              <label htmlFor="reg-email">
                <Mail size={15} aria-hidden="true" />
                Email address
              </label>
              <div className="auth-game-input-wrap">
                <Mail size={18} aria-hidden="true" />
                <input
                  id="reg-email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? "register-error" : undefined}
                  placeholder="trader@example.com"
                />
              </div>
            </div>

            <div className="auth-game-field">
              <label htmlFor="reg-password">
                <LockKeyhole size={15} aria-hidden="true" />
                Password
              </label>
              <div className="auth-game-input-wrap">
                <LockKeyhole size={18} aria-hidden="true" />
                <input
                  id="reg-password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  maxLength={128}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  aria-invalid={Boolean(error)}
                  aria-describedby={
                    error ? "password-help register-error" : "password-help"
                  }
                  placeholder="Create a secure password"
                />
              </div>
              <small id="password-help" className="auth-game-field-help">
                Use at least 8 characters.
              </small>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="auth-game-primary-action"
              aria-busy={loading}
            >
              <span>{loading ? "Creating your trader…" : "Create Trader & Start"}</span>
              <ArrowRight size={19} aria-hidden="true" />
            </button>
          </form>

          <div className="auth-game-divider">
            <span>Already registered?</span>
          </div>
          <Link to="/login" className="auth-game-secondary-action">
            Return to trader sign in
            <ArrowRight size={17} aria-hidden="true" />
          </Link>

          <p className="auth-game-panel-footnote">
            <ShieldCheck size={14} aria-hidden="true" />
            Your opening objective explains the market before you risk a coin.
          </p>
        </section>
      </div>
    </main>
  );
}
