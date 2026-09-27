import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Sans_JP, Zen_Kaku_Gothic_New } from "next/font/google";
import "./globals.css";

const sans = IBM_Plex_Sans_JP({
  variable: "--font-sans",
  weight: ["400", "500", "700"],
  subsets: ["latin"],
  preload: false,
});

const display = Zen_Kaku_Gothic_New({
  variable: "--font-display",
  weight: ["700", "900"],
  subsets: ["latin"],
  preload: false,
});

const mono = IBM_Plex_Mono({
  variable: "--font-mono",
  weight: ["400", "500"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Japan Lens",
  description: "海外メディアは日本をどう報じたか。出来事ごとに各国の報道を並べて比べます。",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ja" className={`${sans.variable} ${display.variable} ${mono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
