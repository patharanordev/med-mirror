import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    AGENT_SERVICE_URL: process.env.AGENT_SERVICE_URL,
  },
};

export default nextConfig;
