import type { NextConfig } from "next";

function resolveApiUrl(): string | null {
  const raw = (process.env.NEXT_PUBLIC_API_URL || "").trim().replace(/\/$/, "");
  if (!raw) {
    // Local default only — Netlify must set NEXT_PUBLIC_API_URL
    if (process.env.NODE_ENV === "development") {
      return "http://127.0.0.1:8000";
    }
    return null;
  }
  if (raw.startsWith("http://") || raw.startsWith("https://")) {
    return raw;
  }
  // User often pastes host without scheme — fix it
  return `https://${raw}`;
}

const API_URL = resolveApiUrl();

const nextConfig: NextConfig = {
  async rewrites() {
    if (!API_URL) {
      return [];
    }
    return [
      {
        source: "/backend/:path*",
        destination: `${API_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
