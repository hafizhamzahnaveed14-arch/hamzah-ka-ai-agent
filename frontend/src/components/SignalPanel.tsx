"use client";

import clsx from "clsx";
import type { TradeIdea } from "@/lib/api";

type Props = {
  idea: TradeIdea | null;
  formatted: string | null;
  loading: boolean;
  error: string | null;
  onEvaluate: () => void;
};

export function SignalPanel({ idea, formatted, loading, error, onEvaluate }: Props) {
  const action = idea?.action ?? null;
  return (
    <div className="rounded-xl border border-line bg-bg-panel/80 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold tracking-wide">Trade Idea</h2>
        <button
          type="button"
          onClick={onEvaluate}
          disabled={loading}
          className="rounded-md bg-accent px-3 py-1.5 text-xs font-semibold text-bg disabled:opacity-50"
        >
          {loading ? "Evaluating…" : "Evaluate setup"}
        </button>
      </div>

      {error && (
        <p className="mb-3 rounded-md border border-short/40 bg-[#2a1210] px-3 py-2 text-sm text-short">
          {error}
        </p>
      )}

      {!idea && !error && (
        <p className="text-sm text-muted">
          Run evaluate to get LONG / SHORT / NO TRADE with reasons. Confidence is not a profit
          guarantee.
        </p>
      )}

      {idea && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <div className="text-xs uppercase tracking-wider text-muted">Action</div>
              <div
                className={clsx(
                  "text-2xl font-bold",
                  action === "LONG" && "text-long",
                  action === "SHORT" && "text-short",
                  action === "NO_TRADE" && "text-notrade",
                )}
              >
                {action === "NO_TRADE" ? "NO TRADE" : action}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider text-muted">Confidence</div>
              <div className="font-mono text-xl">
                {action === "NO_TRADE" ? "—" : `${Math.round(idea.confidence * 100)}%`}
              </div>
            </div>
            {idea.risk && (
              <>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted">Leverage</div>
                  <div className="font-mono text-xl">{idea.risk.suggested_leverage}x</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted">Wallet risk</div>
                  <div className="font-mono text-xl">
                    {(idea.risk.risk_pct * 100).toFixed(2)}%
                  </div>
                </div>
              </>
            )}
          </div>

          {action === "NO_TRADE" && idea.no_trade_reason && (
            <p className="rounded-md border border-line bg-bg px-3 py-2 text-sm text-muted">
              Reason: {idea.no_trade_reason}
            </p>
          )}

          {idea.risk && action !== "NO_TRADE" && (
            <div className="grid grid-cols-2 gap-2 font-mono text-xs sm:grid-cols-3">
              <Metric label="Entry" value={idea.entry} />
              <Metric label="Stop" value={idea.risk.stop_loss} />
              <Metric label="TP1" value={idea.risk.take_profit_1} />
              <Metric
                label={idea.risk.margin_mode === "isolated" ? "Isolated" : "Cross init"}
                value={idea.risk.position_margin ?? idea.risk.isolated_margin}
              />
              <Metric label="Liq" value={idea.risk.liquidation_price} warn={idea.risk.liquidation_warning} />
              <Metric label="R:R" value={`1:${idea.risk.risk_reward}`} />
            </div>
          )}

          {idea.reasons.length > 0 && (
            <div>
              <div className="mb-1 text-xs uppercase tracking-wider text-muted">Reasons</div>
              <ul className="space-y-1 text-sm">
                {idea.reasons.map((r) => (
                  <li key={r} className="text-long/90">
                    ✓ {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <div className="mb-1 text-xs uppercase tracking-wider text-muted">
              Conflicts / Caution
            </div>
            {idea.conflicts.length === 0 ? (
              <p className="text-sm text-muted">– none noted (not a guarantee of profit)</p>
            ) : (
              <ul className="space-y-1 text-sm text-warn">
                {idea.conflicts.map((c) => (
                  <li key={c}>– {c}</li>
                ))}
              </ul>
            )}
          </div>

          {formatted && (
            <pre className="max-h-48 overflow-auto rounded-md border border-line bg-bg p-3 font-mono text-[11px] leading-relaxed text-muted whitespace-pre-wrap">
              {formatted}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  warn,
}: {
  label: string;
  value: string | number | null | undefined;
  warn?: boolean;
}) {
  return (
    <div className="rounded-md border border-line bg-bg px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={clsx("mt-0.5", warn && "text-warn")}>
        {value == null ? "—" : typeof value === "number" ? value.toPrecision(7) : value}
      </div>
    </div>
  );
}
