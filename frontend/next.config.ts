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
