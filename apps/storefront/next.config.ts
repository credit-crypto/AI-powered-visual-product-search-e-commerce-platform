import type { NextConfig } from "next";

/**
 * Web + Capacitor hosting strategy
 * --------------------------------
 * - Default (`npm run dev` / `build:web`): normal Next.js App Router (SSR/SSG).
 *   Use this for the browser storefront and for Capacitor live-reload via
 *   `server.url` pointed at the Next dev/prod host.
 * - Mobile static shell (`CAPACITOR=1` / `build:mobile`): `output: "export"`
 *   writes a static site to `out/`, which Capacitor loads from `webDir`.
 *   Prefer this for offline-capable native shells; avoid server-only features
 *   on routes that ship inside the WebView.
 *
 * Parallel workflow: keep web on SSR; for device testing either (1) point
 * Capacitor `server.url` at the running Next server, or (2) run
 * `npm run mobile:prepare` for a static sync into ios/android projects.
 */
const isCapacitorBuild = process.env.CAPACITOR === "1";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(isCapacitorBuild
    ? {
        output: "export" as const,
        images: { unoptimized: true },
        trailingSlash: true,
      }
    : {}),
};

export default nextConfig;
