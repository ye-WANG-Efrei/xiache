import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone output for lean Docker image
  output: "standalone",

  // Proxy /api/* to the backend during development so we avoid CORS issues.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.INTERNAL_API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
