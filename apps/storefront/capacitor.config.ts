import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Capacitor wraps the Next.js storefront for iOS/Android.
 *
 * Development (live WebView → Next server):
 *   Uncomment `server.url` and point at your machine / LAN IP so the native
 *   shell loads the SSR Next app while you iterate.
 *
 * Production / offline shell:
 *   Run `npm run mobile:prepare` which static-exports into `out/` and syncs.
 */
const config: CapacitorConfig = {
  appId: "com.visualshop.app",
  appName: "Visual Shop",
  webDir: "out",
  server: {
    androidScheme: "https",
    // Live-reload against Next during device/emulator development:
    // url: "http://10.0.2.2:3000",
    // cleartext: true,
  },
  plugins: {
    SplashScreen: {
      launchAutoHide: true,
    },
  },
};

export default config;
