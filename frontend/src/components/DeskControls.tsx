"use client";

type Props = {
  side: "LONG" | "SHORT";
  timeframe: string;
  equity: number;
  riskPct: number;
  leverage: number;
  marginMode: "cross" | "isolated";
  autoStop: boolean;
  newsBlackout: boolean;
  onSide: (v: "LONG" | "SHORT") => void;
  onTimeframe: (v: string) => void;
  onEquity: (v: number) => void;
  onRiskPct: (v: number) => void;
  onLeverage: (v: number) => void;
  onMarginMode: (v: "cross" | "isolated") => void;
  onAutoStop: (v: boolean) => void;
  onNewsBlackout: (v: boolean) => void;
};

const TIMEFRAMES = ["15m", "1h", "4h", "1d"];

export function DeskControls(props: Props) {
  return (
    <div className="rounded-xl border border-line bg-bg-panel/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide">Desk Controls</h2>
        <span className="text-xs text-muted">Paper settings · deploy-ready UI</span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7">
        <Field label="Side">
          <div className="flex gap-1">
            {(["LONG", "SHORT"] as const).map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => props.onSide(s)}
                className={`flex-1 rounded-md px-2 py-1.5 text-xs font-semibold ${
                  props.side === s
                    ? s === "LONG"
                      ? "bg-long text-bg"
                      : "bg-short text-bg"
                    : "border border-line bg-bg text-muted"
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Margin">
          <div className="flex gap-1">
            {(["cross", "isolated"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => props.onMarginMode(m)}
                className={`flex-1 rounded-md px-2 py-1.5 text-xs font-semibold uppercase ${
                  props.marginMode === m
                    ? "bg-accent text-bg"
                    : "border border-line bg-bg text-muted"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </Field>

        <Field label="Chart TF">
          <select
            value={props.timeframe}
            onChange={(e) => props.onTimeframe(e.target.value)}
            className="w-full rounded-md border border-line bg-bg px-2 py-1.5 font-mono text-xs"
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </Field>

        <Field label="Wallet equity ($)">
          <input
            type="number"
            min={50}
            step={50}
            value={props.equity}
            onChange={(e) => props.onEquity(Number(e.target.value) || 0)}
            className="w-full rounded-md border border-line bg-bg px-2 py-1.5 font-mono text-xs"
          />
        </Field>

        <Field label="Risk % (max 0.5)">
          <input
            type="number"
            min={0.1}
            max={0.5}
            step={0.05}
            value={Number((props.riskPct * 100).toFixed(2))}
            onChange={(e) => {
              const pct = Math.min(0.5, Math.max(0.1, Number(e.target.value) || 0.5));
              props.onRiskPct(pct / 100);
            }}
            className="w-full rounded-md border border-line bg-bg px-2 py-1.5 font-mono text-xs"
          />
        </Field>

        <Field label="Leverage">
          <input
            type="number"
            min={1}
            max={200}
            step={1}
            value={props.leverage}
            onChange={(e) =>
              props.onLeverage(Math.min(200, Math.max(1, Number(e.target.value) || 200)))
            }
            className="w-full rounded-md border border-line bg-bg px-2 py-1.5 font-mono text-xs"
          />
        </Field>

        <Field label="Safety toggles">
          <label className="flex items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={props.autoStop}
              onChange={(e) => props.onAutoStop(e.target.checked)}
            />
            Auto tight stop (pre-liq)
          </label>
          <label className="mt-1 flex items-center gap-2 text-xs text-muted">
            <input
              type="checkbox"
              checked={props.newsBlackout}
              onChange={(e) => props.onNewsBlackout(e.target.checked)}
            />
            News blackout ON
          </label>
        </Field>
      </div>

      {props.marginMode === "cross" && (
        <p className="mt-3 text-xs text-warn">
          CROSS + 200x: poora wallet margin share karta hai. 0.5% sirf init/stop budget hai —
          liquidation pe loss us se zyada ho sakta hai. Stop bilkul pehle rakho.
        </p>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-[11px] uppercase tracking-wider text-muted">{label}</span>
      {children}
    </label>
  );
}
