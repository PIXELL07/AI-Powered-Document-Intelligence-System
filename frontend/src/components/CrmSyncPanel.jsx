import { useState } from "react";
import { api } from "../api";

const STATUS_STYLE = {
  synced: "text-ok bg-ok/10 border-ok/30",
  pending: "text-inkfaint bg-hairline/40 border-hairline",
  failed: "text-critical bg-critical/10 border-critical/30",
};

export default function CrmSyncPanel({ documentId, syncStatus, onRetried }) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await api.retryCrmSync(documentId);
      onRetried && onRetried();
    } finally {
      setRetrying(false);
    }
  };

  if (!syncStatus) {
    return (
      <div className="border border-hairline rounded-md p-4 bg-surface text-sm text-inkfaint">
        CRM sync has not started for this document yet.
      </div>
    );
  }

  const style = STATUS_STYLE[syncStatus.status] || STATUS_STYLE.pending;

  return (
    <div className="border border-hairline rounded-md p-4 bg-surface flex items-center justify-between">
      <div>
        <span className={`inline-block px-2 py-0.5 rounded border text-xs font-mono uppercase tracking-wide ${style}`}>
          {syncStatus.status}
        </span>
        <p className="text-xs text-inkfaint mt-2">
          Provider: <span className="font-mono">{syncStatus.provider}</span>
          {syncStatus.external_record_id && (
            <> · Record: <span className="font-mono">{syncStatus.external_record_id.slice(0, 12)}</span></>
          )}
        </p>
        {syncStatus.status === "failed" && syncStatus.last_error && (
          <p className="text-xs text-critical mt-1">{syncStatus.last_error}</p>
        )}
      </div>
      {syncStatus.status === "failed" && (
        <button
          onClick={handleRetry}
          disabled={retrying}
          className="text-xs font-mono uppercase tracking-wide px-3 py-1.5 rounded border border-ledger text-ledger hover:bg-ledger hover:text-white transition disabled:opacity-50"
        >
          {retrying ? "Retrying…" : "Retry sync"}
        </button>
      )}
    </div>
  );
}
