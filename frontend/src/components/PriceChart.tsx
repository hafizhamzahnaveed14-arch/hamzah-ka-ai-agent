"use client";

import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
} from "lightweight-charts";
import type { Candle } from "@/lib/api";

type Props = {
  candles: Candle[];
  symbol: string;
  timeframe: string;
  loading?: boolean;
  error?: string | null;
};

export function PriceChart({ candles, symbol, timeframe, loading, error }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8b9aab",
        fontFamily: "IBM Plex Mono, monospace",
      },
      grid: {
        vertLines: { color: "#1c262e" },
        horzLines: { color: "#1c262e" },
      },
      rightPriceScale: { borderColor: "#24303a" },
      timeScale: { borderColor: "#24303a", timeVisible: true },
      crosshair: {
        vertLine: { color: "#4db6d4", labelBackgroundColor: "#12171c" },
        horzLine: { color: "#4db6d4", labelBackgroundColor: "#12171c" },
      },
      width: containerRef.current.clientWidth,
      height: 360,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#2dd4a0",
      downColor: "#f07167",
      borderVisible: false,
      wickUpColor: "#2dd4a0",
      wickDownColor: "#f07167",
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const onResize = () => {
      if (!containerRef.current || !chartRef.current) return;
      chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener("resize", onResize);

    return () => {
      window.removeEventListener("resize", onResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;
    if (!candles.length) {
      seriesRef.current.setData([]);
      return;
    }
    seriesRef.current.setData(
      candles.map((c) => ({
        time: Math.floor(new Date(c.open_time).getTime() / 1000) as never,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      })),
    );
    chartRef.current.timeScale().fitContent();
  }, [candles]);

  const label = symbol === "XAUUSDT" ? "Gold (XAU)" : symbol;

  return (
    <div className="relative rounded-xl border border-line bg-bg-panel/80 p-3">
      <div className="mb-2 flex items-baseline justify-between">
        <h2 className="text-sm font-semibold tracking-wide text-text">
          {label} · {timeframe.toUpperCase()}
        </h2>
        <span className="font-mono text-xs text-muted">MEXC Futures</span>
      </div>
      <div ref={containerRef} className="w-full" />
      {(loading || error || candles.length === 0) && (
        <div className="pointer-events-none absolute inset-x-3 bottom-3 top-12 flex items-center justify-center rounded-lg bg-bg/70">
          <p className="px-4 text-center text-sm text-muted">
            {loading
              ? "Loading candles…"
              : error
                ? error
                : "No chart data for this symbol on MEXC yet."}
          </p>
        </div>
      )}
    </div>
  );
}
