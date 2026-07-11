import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function SignupPage() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }
    setSubmitting(true);
    try {
      await signup(email.trim(), password, name.trim());
      navigate("/", { replace: true });
    } catch (err) {
      const msg = err.message.includes(":") ? err.message.split(":").slice(1).join(":").trim() : err.message;
      setError(msg || "Could not create your account.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <span className="font-display text-3xl font-semibold text-ledger">Ledgerline</span>
          <p className="text-inkfaint text-sm mt-2">Create an account to start processing documents</p>
        </div>

        <form onSubmit={handleSubmit} className="border border-hairline rounded-md p-6 bg-surface space-y-4">
          {error && (
            <div className="text-sm text-critical bg-critical/5 border border-critical/30 rounded p-2.5">
              {error}
            </div>
          )}
          <div>
            <label className="block text-xs font-mono uppercase tracking-wide text-inkfaint mb-1">Name (optional)</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full border border-hairline rounded px-3 py-2 bg-paper focus:outline-none focus:ring-2 focus:ring-ledger/40"
              placeholder="Jane Analyst"
            />
          </div>
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
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-hairline rounded px-3 py-2 bg-paper focus:outline-none focus:ring-2 focus:ring-ledger/40"
              placeholder="At least 8 characters"
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="w-full font-mono text-xs uppercase tracking-wide px-4 py-2.5 rounded bg-ledger text-white hover:bg-ledgerlight transition disabled:opacity-50"
          >
            {submitting ? "Creating account…" : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-inkfaint mt-5">
          Already have an account?{" "}
          <Link to="/login" className="text-ledger hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
