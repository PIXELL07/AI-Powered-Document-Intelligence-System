const CATEGORY_LABELS = {
  financial: "Financial",
  contractual: "Contractual",
  data_quality: "Data Quality",
  other: "Other",
};

function scoreColor(score) {
  if (score >= 60) return "text-critical";
  if (score >= 25) return "text-warn";
  return "text-ok";
}

export default function RiskChart({ riskScore, breakdown }) {
  const entries = Object.entries(breakdown || {}).filter(([, v]) => v > 0);
  const max = Math.max(1, ...entries.map(([, v]) => v));

  return (
    <div>
      <div className="flex items-end gap-3 mb-6">
        <span className={`font-display text-5xl font-semibold ${scoreColor(riskScore)}`}>
          {riskScore != null ? Math.round(riskScore) : "—"}
        </span>
        <span className="text-inkfaint text-sm mb-1">/ 100 overall risk</span>
      </div>
      <div className="space-y-3">
        {entries.length === 0 && (
          <p className="text-sm text-inkfaint">No risk-contributing categories detected.</p>
        )}
        {entries.map(([key, value]) => (
          <div key={key}>
            <div className="flex justify-between text-xs font-mono text-inkfaint mb-1">
              <span className="uppercase tracking-wide">{CATEGORY_LABELS[key] || key}</span>
              <span>{value.toFixed(1)}</span>
            </div>
            <div className="h-2 bg-hairline/60 rounded-full overflow-hidden">
              <div
                className="h-full bg-ledger rounded-full"
                style={{ width: `${Math.max(4, (value / max) * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
