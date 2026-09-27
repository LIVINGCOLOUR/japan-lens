import type { NextConfig } from "next";

// 静的なファイル（out/）として書き出し、Cloudflare Pages の無料枠で配信する
const nextConfig: NextConfig = {
  output: "export",
};

export default nextConfig;
