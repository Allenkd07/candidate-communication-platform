import type { NextConfig } from "next";

// Where the Next server forwards /api/* (the Django API). Read at build time.
const apiOrigin = process.env.API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  output: "standalone",
  // Django URLs end in "/"; don't let Next strip the slash before proxying.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      // `:path*` drops a trailing slash, so slash-terminated URLs get their own rule.
      { source: "/api/:path*/", destination: `${apiOrigin}/api/:path*/` },
      { source: "/api/:path*", destination: `${apiOrigin}/api/:path*` },
    ];
  },
};

export default nextConfig;
