import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  ...(process.env.CLOUDFLARE_BUILD === "1" ? { output: "export" as const } : {}),
};

export default nextConfig;
