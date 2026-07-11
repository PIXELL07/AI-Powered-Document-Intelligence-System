import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const from = location.state?.from?.pathname || "/";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      const msg = err.message.includes(":") ? err.message.split(":").slice(1).join(":").trim() : err.message;
      setError(msg || "Could not log in. Check your email and password.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="font-display text-3xl font-semibold text-ledger">Ledgerline</span>
          <p className="text-inkfaint text-sm mt-2">Sign in to your projects</p>
        </div>

        <form onSubmit={handleSubmit} className="border border-hairline rounded-md p-6 bg-surface space-y-4">
          {error && (
            <div className="text-sm text-critical bg-critical/5 border border-critical/30 rounded p-2.5">
              {error}
            </div>
          )}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wide text-inkfaint mb-1">Email</label>
            <input
              type="email"
              required
              autoFocus
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-hairline rounded px-3 py-2 bg-paper focus:outline-none focus:ring-2 focus:ring-ledger/40"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="block text-xs font-mono uppercase tracking-wide text-inkfaint mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-hairline rounded px-3 py-2 bg-paper focus:outline-none focus:ring-2 focus:ring-ledger/40"
              placeholder="••••••••"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full font-mono text-xs uppercase tracking-wide px-4 py-2.5 rounded bg-ledger text-white hover:bg-ledgerlight transition disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <p className="text-center text-sm text-inkfaint mt-5">
          Don't have an account?{" "}
          <Link to="/signup" className="text-ledger hover:underline">Create one</Link>
        </p>
      </div>
    </div>
  );
}
