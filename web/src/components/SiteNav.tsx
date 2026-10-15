import Link from "next/link";

// 2つの画面の切り替え。「日本が世界からどう報じられたか」と「世界の出来事を世界がどう報じたか」
export default function SiteNav({ current }: { current: "japan" | "world" }) {
  return (
    <nav className="site-nav" aria-label="画面の切り替え">
      <Link href="/" aria-current={current === "japan" ? "page" : undefined}>
        日本はどう報じられたか
      </Link>
      <Link href="/world" aria-current={current === "world" ? "page" : undefined}>
        世界の主要ニュース
      </Link>
    </nav>
  );
}
