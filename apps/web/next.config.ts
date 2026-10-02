import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Small self-contained server for the Cloud Run image.
  output: "standalone",
};

export default nextConfig;
