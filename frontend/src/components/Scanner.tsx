"use client";

import clsx from "clsx";

export type ScanRow = {
  symbol: string;
  price: number | null;
  bias: string;
  confidence: number | null;
  status: "idle" | "loading" | "error";
};

type Props = {
  rows: ScanRow[];
  selected: string;
  onSelect: (symbol: string) => void;
};

export function Scanner({ rows, selected, onSelect }: Props) {
  return (
    <div className="rounded-xl border border-line bg-bg-panel/80 p-3">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide">Market Scanner</h2>
        <span className="text-xs text-muted">Phase 1 · MEXC</span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
        {rows.map((row) => (
          <button
            key={row.symbol}
            type="button"
            onClick={() => onSelect(row.symbol)}
            className={clsx(
              "rounded-lg border px-3 py-2.5 text-left transition",
              selected === row.symbol
                ? "border-accent/60 bg-bg-elevated"
                : "border-line bg-bg hover:border-accent/30",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-sm font-medium">{row.symbol}</span>
              <span
                className={clsx(
                  "text-[11px] uppercase tracking-wider",
                  row.bias === "bullish" && "text-long",
                  row.bias === "bearish" && "text-short",
                  row.bias === "range" && "text-muted",
                )}
              >
                {row.bias}
              </span>
            </div>
            <div className="mt-1 flex items-center justify-between font-mono text-xs text-muted">
              <span>
                {row.price == null
                  ? row.status === "loading"
                    ? "…"
                    : "—"
                  : row.price.toLocaleString(undefined, { maximumFractionDigits: 6 })}
              </span>
              <span>
                {row.confidence == null ? "—" : `${Math.round(row.confidence * 100)}%`}
              </span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
