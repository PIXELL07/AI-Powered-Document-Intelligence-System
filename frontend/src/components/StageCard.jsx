import { useState } from "react";

function StageMark({ status }) {
  if (status === "complete") {
    return (
      <div className="w-8 h-8 rounded-full border-2 border-ok flex items-center justify-center bg-ok/10 stamp-tick">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M2 7L5.5 10.5L12 3" stroke="currentColor" strokeWidth="2" className="text-ok" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
    );
  }
  if (status === "active") {
    return (
      <div className="w-8 h-8 rounded-full border-2 border-ledger flex items-center justify-center">
        <div className="w-3.5 h-3.5 rounded-full border-2 border-ledger border-t-transparent animate-spin" />
      </div>
    );
  }
  if (status === "failed") {
    return (
      <div className="w-8 h-8 rounded-full border-2 border-critical flex items-center justify-center bg-critical/10">
        <span className="text-critical text-sm font-bold">!</span>
      </div>
    );
  }
  return <div className="w-8 h-8 rounded-full border-2 border-hairline" />;
}

export default function StageCard({ stageNumber, stageName, status, output, renderOutput }) {
  const [open, setOpen] = useState(status === "active");
  const isDone = status === "complete";

  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <StageMark status={status} />
        <div className="flex-1 w-px bg-hairline mt-1" />
      </div>
      <div className="flex-1 pb-6">
        <button
          onClick={() => isDone && setOpen((o) => !o)}
          className={`w-full text-left flex items-center justify-between ${isDone ? "cursor-pointer" : "cursor-default"}`}
        >
          <div>
            <span className="font-mono text-xs text-inkfaint mr-2">
              {String(stageNumber).padStart(2, "0")}
            </span>
            <span className="font-display text-lg text-ink">{stageName}</span>
          </div>
          {isDone && (
            <span className="font-mono text-xs text-inkfaint">{open ? "hide" : "show"}</span>
          )}
        </button>
        {status === "active" && (
          <p className="mt-1 text-sm text-inkfaint">Processing…</p>
        )}
        {status === "failed" && (
          <p className="mt-1 text-sm text-critical">Stage failed. See document status for details.</p>
        )}
        {isDone && open && (
          <div className="mt-3 border border-hairline rounded-md bg-surface p-4">
            {renderOutput ? renderOutput(output) : (
              <pre className="text-xs font-mono text-inkfaint whitespace-pre-wrap break-words">
                {JSON.stringify(output, null, 2)}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
