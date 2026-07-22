"use client";

import { motion } from "framer-motion";

type Props = {
  mode: string;
  label: string;
  liveEnabled: boolean;
};

export function ModeBanner({ mode, label, liveEnabled }: Props) {
  const isPaper = mode !== "live";
  return (
    <motion.div
      initial={{ y: -12, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      className={`w-full border-b px-4 py-2.5 text-center font-semibold tracking-[0.18em] ${
        isPaper
          ? "border-paper/40 bg-paper-bg text-paper"
          : "border-short/50 bg-[#2a1210] text-short"
      }`}
    >
      {isPaper ? "PAPER TRADING" : "LIVE"} — {label}
      {!liveEnabled && (
        <span className="ml-3 font-normal tracking-normal text-muted normal-case">
          No real orders. Ideas only.
        </span>
      )}
    </motion.div>
  );
}
