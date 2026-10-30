import type { NextConfig } from "next";

// Origin of the Django API that /api/* is proxied to. Rewrites are resolved at build time.
const apiOrigin = process.env.API_ORIGIN;
if (!apiOrigin) {
  throw new Error("API_ORIGIN is not set; see .env.example.");
}

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  // Dev server only: on Windows the app is opened at 127.0.0.1 (localhost can hang on IPv6),
  // and Next blocks its dev resources for hosts other than localhost unless listed here.
  allowedDevOrigins: ["127.0.0.1"],
  // Django URLs end in "/"; keep the trailing slash instead of redirecting it away.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      // `:path*` drops a trailing slash, so slash-terminated URLs need their own rule.
      { source: "/api/:path*/", destination: `${apiOrigin}/api/:path*/` },
      { source: "/api/:path*", destination: `${apiOrigin}/api/:path*` },
    ];
  },
};

export default nextConfig;
