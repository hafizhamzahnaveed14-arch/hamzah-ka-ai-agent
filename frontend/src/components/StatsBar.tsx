"use client";

type Props = {
  equity: number;
  riskPct: number;
  leverage: number;
  apiOk: boolean | null;
};

export function StatsBar({ equity, riskPct, leverage, apiOk }: Props) {
  return (
    <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
      <Stat label="Paper equity" value={`$${equity.toLocaleString()}`} />
      <Stat label="Risk / trade" value={`${(riskPct * 100).toFixed(2)}%`} />
      <Stat label="Target leverage" value={`${leverage}x`} />
      <Stat
        label="API"
        value={apiOk == null ? "…" : apiOk ? "Online" : "Offline"}
        tone={apiOk == null ? "muted" : apiOk ? "long" : "short"}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  tone = "text",
}: {
  label: string;
  value: string;
  tone?: "text" | "muted" | "long" | "short";
}) {
  const color =
    tone === "long"
      ? "text-long"
      : tone === "short"
        ? "text-short"
        : tone === "muted"
          ? "text-muted"
          : "text-text";
  return (
    <div className="rounded-xl border border-line bg-bg-panel/80 px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`mt-1 font-mono text-lg ${color}`}>{value}</div>
    </div>
  );
}
