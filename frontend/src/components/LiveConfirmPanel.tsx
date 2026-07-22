"use client";

import { useCallback, useEffect, useState } from "react";

type LiveStatus = {
  trading_mode: string;
  live_trading_enabled: boolean;
  armed: boolean;
  autopilot: boolean;
  mexc_keys_configured?: boolean;
  ready_for_preview?: boolean;
  egress_ip?: string | null;
  missing?: string[];
  kill_switch?: string;
  note: string;
};

type Props = {
  symbol: string;
  side: "LONG" | "SHORT";
  entry: number | null;
  stopLoss: number | null;
  equity: number;
};

const API =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
    : "/backend";

export function LiveConfirmPanel({ symbol, side, entry, stopLoss, equity }: Props) {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [typedYes, setTypedYes] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [accountNote, setAccountNote] = useState<string | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/live/status`, { cache: "no-store" });
      setStatus(await res.json());
    } catch {
      setStatus(null);
    }
  }, []);

  const refreshAccount = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/live/account`, { cache: "no-store" });
      if (!res.ok) {
        setAccountNote(null);
        return;
      }
      const data = await res.json();
      const n = data.open_position_count ?? 0;
      const eq = data.suggested_desk_equity_usdt;
      setAccountNote(
        n > 0
          ? `MEXC open positions: ${n}. Set Desk Wallet Equity to ~${eq ?? "your USDT balance"} (not 10000). CROSS shares margin — avoid stacking more 200x.`
          : eq != null
            ? `MEXC equity ~${eq} USDT — use this in Desk Wallet Equity.`
            : null,
      );
    } catch {
      setAccountNote(null);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
    const id = window.setInterval(() => void refreshStatus(), 30_000);
    return () => window.clearInterval(id);
  }, [refreshStatus]);

  useEffect(() => {
    if (status?.mexc_keys_configured) {
      void refreshAccount();
    }
  }, [status?.mexc_keys_configured, refreshAccount]);

  const canPreview = Boolean(status?.armed && status?.mexc_keys_configured !== false);

  const onPreview = async () => {
    if (entry == null || stopLoss == null) {
      setError("Need entry + stop from Evaluate first (or wait for price).");
      return;
    }
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API}/api/v1/live/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          side,
          entry,
          stop_loss: stopLoss,
          account_equity: equity,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      if (!data.ok) {
        setToken(null);
        setPreview(data);
        setMessage(data.reason || "NO TRADE — live blocked");
        return;
      }
      setToken(data.confirm_token);
      setPreview(data);
      setMessage("Preview ready. Type YES then Confirm to place REAL order.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Preview failed");
    } finally {
      setLoading(false);
    }
  };

  const onConfirm = async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/live/confirm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm_token: token, typed_yes: typedYes }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || JSON.stringify(data));
      setMessage(`ORDER SUBMITTED · id=${data.order_id ?? "?"} — check MEXC app`);
      setToken(null);
      setTypedYes("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Confirm failed");
    } finally {
      setLoading(false);
      void refreshStatus();
    }
  };

  return (
    <div className="rounded-xl border border-short/40 bg-[#1a1010] p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-short">Live Order (Real Money)</h2>
        <span className="font-mono text-[11px] text-muted">
          {status?.armed ? "ARMED" : "DISARMED"} · autopilot OFF
        </span>
      </div>
      <p className="mb-3 text-xs text-muted">{status?.note}</p>

      {!status?.armed && (
        <div className="mb-3 rounded-md border border-warn/40 bg-[#2a2208] px-3 py-2 text-xs text-warn">
          <p className="mb-1 font-semibold">Railway API pe yeh set karo, phir redeploy:</p>
          <code className="block font-mono text-[11px] text-text whitespace-pre-wrap">
            {`TRADING_MODE=live
LIVE_TRADING_ENABLED=true
MEXC_API_KEY=...
MEXC_API_SECRET=...
CORS_ORIGINS=https://tradingagen.netlify.app`}
          </code>
          {status?.missing && status.missing.length > 0 && (
            <ul className="mt-2 list-disc pl-4 text-[11px] text-muted">
              {status.missing.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {accountNote && (
        <p className="mb-3 rounded-md border border-warn/40 bg-[#2a2208] px-3 py-2 text-xs text-warn">
          {accountNote}
        </p>
      )}

      {status?.armed && status.egress_ip && (
        <p className="mb-3 rounded-md border border-line bg-bg px-3 py-2 font-mono text-[11px] text-muted">
          MEXC whitelist IP: <span className="text-text">{status.egress_ip}</span>
        </p>
      )}

      {status?.kill_switch && (
        <p className="mb-3 text-[11px] text-muted">Kill switch: {status.kill_switch}</p>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={loading || !canPreview}
          onClick={onPreview}
          className="rounded-md bg-warn px-3 py-1.5 text-xs font-semibold text-bg disabled:opacity-40"
        >
          1. Preview live order
        </button>
        <input
          value={typedYes}
          onChange={(e) => setTypedYes(e.target.value)}
          placeholder="Type YES"
          className="w-28 rounded-md border border-line bg-bg px-2 py-1.5 font-mono text-xs"
        />
        <button
          type="button"
          disabled={loading || !token || typedYes.toUpperCase() !== "YES"}
          onClick={onConfirm}
          className="rounded-md bg-short px-3 py-1.5 text-xs font-semibold text-bg disabled:opacity-40"
        >
          2. Confirm REAL order
        </button>
      </div>

      {message && <p className="mt-3 text-sm text-long">{message}</p>}
      {error && <p className="mt-3 text-sm text-short">{error}</p>}
      {preview && (
        <pre className="mt-3 max-h-40 overflow-auto rounded-md border border-line bg-bg p-2 font-mono text-[10px] text-muted">
          {JSON.stringify(preview, null, 2)}
        </pre>
      )}
    </div>
  );
}
