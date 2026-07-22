const API_BASE =
  typeof window === "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
    : "/backend";

export type TradingModeInfo = {
  mode: string;
  label: string;
  live_execution_enabled: boolean;
  note: string;
};

export type HealthInfo = {
  status: string;
  app: string;
  trading_mode: string;
  disclaimer: string;
};

export type Candle = {
  symbol: string;
  timeframe: string;
  open_time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type TradeIdea = {
  symbol: string;
  action: "LONG" | "SHORT" | "NO_TRADE";
  side?: string | null;
  entry?: number | null;
  confidence: number;
  risk?: {
    account_equity: number;
    risk_pct: number;
    position_size: number;
    position_notional: number;
    isolated_margin?: number | null;
    margin_mode?: "cross" | "isolated";
    position_margin?: number | null;
    stop_loss: number;
    take_profit_1: number;
    take_profit_2: number;
    take_profit_3: number;
    risk_reward: number;
    suggested_leverage: number;
    liquidation_price: number;
    liquidation_warning: boolean;
    liquidation_warning_note?: string | null;
  } | null;
  reasons: string[];
  conflicts: string[];
  no_trade_reason?: string | null;
  trading_mode: string;
};

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function fetchHealth(): Promise<HealthInfo> {
  return getJson("/health");
}

export async function fetchMode(): Promise<TradingModeInfo> {
  return getJson("/api/v1/mode");
}

export async function fetchSymbols(
  universe: "phase1" | "phase2" | "active" | "all" = "active",
): Promise<{
  universe: string;
  phase: number;
  symbols: string[];
  labels?: Record<string, string>;
}> {
  return getJson(`/api/v1/symbols?universe=${universe}`);
}

export async function fetchKlines(
  symbol: string,
  timeframe = "1h",
  limit = 120,
): Promise<{ candles: Candle[]; exchange: string }> {
  return getJson(
    `/api/v1/market/${encodeURIComponent(symbol)}/klines?timeframe=${timeframe}&limit=${limit}&exchange=mexc`,
  );
}

export async function fetchTicker(
  symbol: string,
): Promise<{ symbol: string; price: number; exchange: string }> {
  return getJson(`/api/v1/market/${encodeURIComponent(symbol)}/ticker?exchange=mexc`);
}

export async function evaluateSignal(body: {
  symbol: string;
  side: "LONG" | "SHORT";
  entry: number;
  stop_loss: number;
  account_equity: number;
  risk_pct?: number;
  timeframes: { timeframe: string; bias: string }[];
  confluence_labels: string[];
  conflicts?: string[];
  news_blackout?: boolean;
  news_reason?: string;
}): Promise<{ idea: TradeIdea; formatted: string; disclaimer: string }> {
  const res = await fetch(`${API_BASE}/api/v1/signals/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Evaluate failed: ${res.status}`);
  }
  return res.json();
}

export type JournalEntry = {
  id: number;
  created_at: string | null;
  symbol: string;
  action: "LONG" | "SHORT" | "NO_TRADE" | string;
  trading_mode: string;
  confidence: number;
  entry?: number | null;
  stop_loss?: number | null;
  take_profit_1?: number | null;
  risk_reward?: number | null;
  reasons: string[];
  conflicts: string[];
  no_trade_reason?: string | null;
};

export async function fetchJournal(
  limit = 40,
  symbol?: string,
): Promise<{ source: string; count: number; entries: JournalEntry[]; note: string }> {
  const q = new URLSearchParams({ limit: String(limit) });
  if (symbol) q.set("symbol", symbol);
  return getJson(`/api/v1/signals/journal?${q.toString()}`);
}
