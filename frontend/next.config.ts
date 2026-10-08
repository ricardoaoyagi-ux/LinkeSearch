import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Pin the workspace root to this folder (a stray lockfile exists higher up in the user folder)
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
