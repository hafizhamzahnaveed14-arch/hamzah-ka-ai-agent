"use client";

import type { TradeIdea } from "@/lib/api";

type Entry = {
  id: string;
  at: string;
  idea: TradeIdea;
};

type Props = {
  entries: Entry[];
};

export function Journal({ entries }: Props) {
  return (
    <div className="rounded-xl border border-line bg-bg-panel/80 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide">Signal Journal</h2>
        <span className="text-xs text-muted">Session (local)</span>
      </div>
      {entries.length === 0 ? (
        <p className="text-sm text-muted">No signals yet. Evaluate a setup to log one.</p>
      ) : (
        <ul className="max-h-64 space-y-2 overflow-auto">
          {entries.map((e) => (
            <li
              key={e.id}
              className="rounded-lg border border-line bg-bg px-3 py-2 font-mono text-xs"
            >
              <div className="flex justify-between gap-2 text-muted">
                <span>{e.at}</span>
                <span>{e.idea.symbol}</span>
              </div>
              <div className="mt-1 flex justify-between">
                <span
                  className={
                    e.idea.action === "LONG"
                      ? "text-long"
                      : e.idea.action === "SHORT"
                        ? "text-short"
                        : "text-muted"
                  }
                >
                  {e.idea.action === "NO_TRADE" ? "NO TRADE" : e.idea.action}
                </span>
                <span>
                  {e.idea.action === "NO_TRADE"
                    ? "—"
                    : `${Math.round(e.idea.confidence * 100)}%`}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
