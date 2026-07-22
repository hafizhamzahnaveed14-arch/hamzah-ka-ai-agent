"use client";

import type { JournalEntry } from "@/lib/api";

type Props = {
  entries: JournalEntry[];
  loading?: boolean;
  error?: string | null;
  source?: string;
};

function formatAt(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function Journal({ entries, loading, error, source = "neon" }: Props) {
  return (
    <div className="rounded-xl border border-line bg-bg-panel/80 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide">Signal Journal</h2>
        <span className="text-xs text-muted">
          {source === "neon" ? "Neon (cloud)" : source}
        </span>
      </div>
      {loading ? (
        <p className="text-sm text-muted">Loading journal…</p>
      ) : error ? (
        <p className="text-sm text-warn">{error}</p>
      ) : entries.length === 0 ? (
        <p className="text-sm text-muted">
          No signals in Neon yet. Scanner writes here every cycle.
        </p>
      ) : (
        <ul className="max-h-64 space-y-2 overflow-auto">
          {entries.map((e) => (
            <li
              key={e.id}
              className="rounded-lg border border-line bg-bg px-3 py-2 font-mono text-xs"
            >
              <div className="flex justify-between gap-2 text-muted">
                <span>{formatAt(e.created_at)}</span>
                <span>{e.symbol}</span>
              </div>
              <div className="mt-1 flex justify-between">
                <span
                  className={
                    e.action === "LONG"
                      ? "text-long"
                      : e.action === "SHORT"
                        ? "text-short"
                        : "text-muted"
                  }
                >
                  {e.action === "NO_TRADE" ? "NO TRADE" : e.action}
                </span>
                <span>
                  {e.action === "NO_TRADE"
                    ? "—"
                    : `${Math.round(e.confidence * 100)}%`}
                </span>
              </div>
              {e.no_trade_reason ? (
                <p className="mt-1 text-[10px] text-muted line-clamp-2">
                  {e.no_trade_reason}
                </p>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
