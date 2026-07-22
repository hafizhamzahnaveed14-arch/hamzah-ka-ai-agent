"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ModeBanner } from "@/components/ModeBanner";
import { PriceChart } from "@/components/PriceChart";
import { Scanner, type ScanRow } from "@/components/Scanner";
import { SignalPanel } from "@/components/SignalPanel";
import { StatsBar } from "@/components/StatsBar";
import { Journal } from "@/components/Journal";
import { DeskControls } from "@/components/DeskControls";
import { LiveConfirmPanel } from "@/components/LiveConfirmPanel";
import {
  evaluateSignal,
  fetchHealth,
  fetchJournal,
  fetchKlines,
  fetchMode,
  fetchSymbols,
  fetchTicker,
  type Candle,
  type JournalEntry,
  type TradeIdea,
} from "@/lib/api";

const FALLBACK_SYMBOLS = [
  "ETHUSDT",
  "BTCUSDT",
  "SOLUSDT",
  "DOGEUSDT",
  "XAUUSDT",
  "ADAUSDT",
  "XRPUSDT",
  "BNBUSDT",
  "AAVEUSDT",
  "PEPEUSDT",
  "LINKUSDT",
  "AVAXUSDT",
];

function tightStop(entry: number, side: "LONG" | "SHORT", leverage: number): number {
  const mmr = 0.004;
  const maxDist = entry * Math.max(0, 1 / leverage - mmr) * 0.6;
  const dist = maxDist * 0.7;
  return side === "LONG" ? entry - dist : entry + dist;
}

export default function DashboardPage() {
  const [mode, setMode] = useState("paper");
  const [modeLabel, setModeLabel] = useState("PAPER TRADING");
  const [liveEnabled, setLiveEnabled] = useState(false);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [symbols, setSymbols] = useState<string[]>(FALLBACK_SYMBOLS);
  const [selected, setSelected] = useState("ETHUSDT");
  const [rows, setRows] = useState<ScanRow[]>([]);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [chartLoading, setChartLoading] = useState(false);
  const [chartError, setChartError] = useState<string | null>(null);
  const [idea, setIdea] = useState<TradeIdea | null>(null);
  const [formatted, setFormatted] = useState<string | null>(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [journal, setJournal] = useState<JournalEntry[]>([]);
  const [journalLoading, setJournalLoading] = useState(true);
  const [journalError, setJournalError] = useState<string | null>(null);

  const [side, setSide] = useState<"LONG" | "SHORT">("LONG");
  const [timeframe, setTimeframe] = useState("1h");
  const [equity, setEquity] = useState(10_000);
  const [riskPct, setRiskPct] = useState(0.005);
  const [leverage, setLeverage] = useState(200);
  const [marginMode, setMarginMode] = useState<"cross" | "isolated">("cross");
  const [autoStop, setAutoStop] = useState(true);
  const [newsBlackout, setNewsBlackout] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [health, modeInfo, sym] = await Promise.all([
          fetchHealth(),
          fetchMode(),
          fetchSymbols("active"),
        ]);
        if (cancelled) return;
        setApiOk(health.status === "ok");
        setMode(modeInfo.mode);
        setModeLabel(modeInfo.label);
        setLiveEnabled(modeInfo.live_execution_enabled);
        setSymbols(sym.symbols);
        if (!sym.symbols.includes(selected)) {
          setSelected(sym.symbols.includes("ETHUSDT") ? "ETHUSDT" : sym.symbols[0]);
        }
      } catch {
        if (!cancelled) setApiOk(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadJournal = useCallback(async () => {
    setJournalLoading(true);
    setJournalError(null);
    try {
      const data = await fetchJournal(40);
      setJournal(data.entries);
    } catch (err) {
      const raw = err instanceof Error ? err.message : "Journal load failed";
      if (raw.includes("Not Found") || raw.includes("404")) {
        setJournalError(
          "API pe journal route abhi deploy nahi hua. Railway → API → Ctrl+K → Deploy Latest Commit. /health mein api_build: journal-v1 aana chahiye.",
        );
      } else if (raw.includes("502") || raw.includes("failed to respond")) {
        setJournalError(
          "Railway API 502 — service down/restarting. Deployments → View logs check karo; start command uvicorn hona chahiye (scanner nahi).",
        );
      } else {
        setJournalError(raw);
      }
    } finally {
      setJournalLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadJournal();
    const id = window.setInterval(() => {
      void loadJournal();
    }, 60_000);
    return () => window.clearInterval(id);
  }, [loadJournal]);

  useEffect(() => {
    setRows(
      symbols.map((symbol) => ({
        symbol,
        price: null,
        bias: "range",
        confidence: null,
        status: "loading",
      })),
    );
  }, [symbols]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next: ScanRow[] = [];
      for (const symbol of symbols) {
        try {
          const t = await fetchTicker(symbol);
          if (cancelled) return;
          next.push({
            symbol,
            price: t.price,
            bias: "range",
            confidence: null,
            status: "idle",
          });
        } catch {
          next.push({
            symbol,
            price: null,
            bias: "range",
            confidence: null,
            status: "error",
          });
        }
      }
      if (!cancelled) setRows(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [symbols]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setChartLoading(true);
      setChartError(null);
      try {
        const data = await fetchKlines(selected, timeframe, 120);
        if (!cancelled) {
          setCandles(data.candles);
          if (!data.candles.length) {
            setChartError("Empty kline response from MEXC for this symbol.");
          }
        }
      } catch (err) {
        if (!cancelled) {
          setCandles([]);
          setChartError(err instanceof Error ? err.message : "Failed to load chart");
        }
      } finally {
        if (!cancelled) setChartLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, timeframe]);

  const lastClose = useMemo(() => {
    if (!candles.length) {
      const row = rows.find((r) => r.symbol === selected);
      return row?.price ?? null;
    }
    return candles[candles.length - 1]?.close ?? null;
  }, [candles, rows, selected]);

  const onEvaluate = useCallback(async () => {
    if (lastClose == null) {
      setEvalError("No price available for this symbol yet.");
      return;
    }
    setEvalLoading(true);
    setEvalError(null);
    try {
      const entry = lastClose;
      const stop_loss = autoStop
        ? Number(tightStop(entry, side, leverage).toFixed(8))
        : Number(
            (side === "LONG" ? entry * 0.995 : entry * 1.005).toFixed(8),
          );
      const bullish = side === "LONG";
      const bias = bullish ? "bullish" : "bearish";
      const result = await evaluateSignal({
        symbol: selected,
        side,
        entry,
        stop_loss,
        account_equity: equity,
        risk_pct: riskPct,
        timeframes: [
          { timeframe: "1d", bias },
          { timeframe: "4h", bias },
          { timeframe: "1h", bias },
          { timeframe: "15m", bias },
        ],
        confluence_labels: bullish
          ? [
              "Break of Structure (BOS)",
              "Bullish Order Block reaction",
              "FVG filled",
              "RSI recovering from oversold",
              "EMA alignment (Daily/4H/1H bullish)",
              "Above-average volume on trigger candle",
            ]
          : [
              "Break of Structure (BOS) bearish",
              "Bearish Order Block reaction",
              "FVG filled",
              "RSI rolling over from overbought",
              "EMA alignment (Daily/4H/1H bearish)",
              "Above-average volume on trigger candle",
            ],
        news_blackout: newsBlackout,
        news_reason: newsBlackout ? "Manual news blackout enabled in desk controls" : undefined,
      });
      setIdea(result.idea);
      setFormatted(result.formatted);
      void loadJournal();
      setRows((prev) =>
        prev.map((r) =>
          r.symbol === selected
            ? {
                ...r,
                confidence:
                  result.idea.action === "NO_TRADE" ? 0 : result.idea.confidence,
                bias:
                  result.idea.action === "LONG"
                    ? "bullish"
                    : result.idea.action === "SHORT"
                      ? "bearish"
                      : "range",
              }
            : r,
        ),
      );
    } catch (err) {
      setEvalError(err instanceof Error ? err.message : "Evaluate failed");
    } finally {
      setEvalLoading(false);
    }
  }, [
    loadJournal,
    autoStop,
    equity,
    lastClose,
    leverage,
    newsBlackout,
    riskPct,
    selected,
    side,
  ]);

  return (
    <div className="min-h-screen">
      <ModeBanner mode={mode} label={modeLabel} liveEnabled={liveEnabled} />

      <header className="border-b border-line px-4 py-4 md:px-6">
        <div className="mx-auto flex max-w-7xl flex-col gap-1 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.25em] text-accent">AlphaQuant AI</p>
            <h1 className="text-2xl font-semibold tracking-tight md:text-3xl">
              Futures Desk
            </h1>
            <p className="mt-1 max-w-xl text-sm text-muted">
              MEXC scanner with Gold (XAU), DOGE, BTC and more. Controls are for paper desk
              now — live needs cloud deploy + paper gate. No guaranteed profits.
            </p>
          </div>
          <div className="font-mono text-xs text-muted">
            Selected: <span className="text-text">{selected}</span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl space-y-4 px-4 py-4 md:px-6">
        <StatsBar
          equity={equity}
          riskPct={riskPct}
          leverage={leverage}
          apiOk={apiOk}
        />

        <DeskControls
          side={side}
          timeframe={timeframe}
          equity={equity}
          riskPct={riskPct}
          leverage={leverage}
          marginMode={marginMode}
          autoStop={autoStop}
          newsBlackout={newsBlackout}
          onSide={setSide}
          onTimeframe={setTimeframe}
          onEquity={setEquity}
          onRiskPct={setRiskPct}
          onLeverage={setLeverage}
          onMarginMode={setMarginMode}
          onAutoStop={setAutoStop}
          onNewsBlackout={setNewsBlackout}
        />

        {apiOk === false && (
          <div className="rounded-xl border border-warn/40 bg-[#2a2208] px-4 py-3 text-sm text-warn">
            Backend offline. Start API on the server (not only your laptop) for 24/7:
            <code className="mt-1 block font-mono text-xs text-text">
              python -m uvicorn alphaquant_api.main:app --app-dir api --host 0.0.0.0 --port 8000
            </code>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[300px_1fr]">
          <Scanner rows={rows} selected={selected} onSelect={setSelected} />
          <div className="space-y-4">
            <PriceChart
              candles={candles}
              symbol={selected}
              timeframe={timeframe}
              loading={chartLoading}
              error={chartError}
            />
            <div className="grid gap-4 xl:grid-cols-2">
              <SignalPanel
                idea={idea}
                formatted={formatted}
                loading={evalLoading}
                error={evalError}
                onEvaluate={onEvaluate}
              />
              <Journal
                entries={journal}
                loading={journalLoading}
                error={journalError}
                source="neon"
              />
            </div>
            <LiveConfirmPanel
              symbol={selected}
              side={side}
              entry={idea?.entry ?? lastClose}
              stopLoss={
                idea?.risk?.stop_loss ??
                (lastClose != null
                  ? tightStop(lastClose, side, leverage)
                  : null)
              }
              equity={equity}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
