const STYLES = {
  critical: "bg-critical/10 text-critical border-critical/30",
  warning: "bg-warn/10 text-warn border-warn/30",
  informational: "bg-info/10 text-info border-info/30",
};

const LABELS = {
  critical: "Critical",
  warning: "Warning",
  informational: "Informational",
};

export default function SeverityBadge({ severity }) {
  const cls = STYLES[severity] || STYLES.informational;
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-xs font-mono uppercase tracking-wide ${cls}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {LABELS[severity] || severity}
    </span>
  );
}
