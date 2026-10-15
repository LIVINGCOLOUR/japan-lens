import type { Metadata } from "next";
import Link from "next/link";
import SiteNav from "@/components/SiteNav";
import WorldView from "@/components/WorldView";
import { REGION_LABEL } from "@/lib/regions";
import { getWorld } from "@/lib/world";

export const metadata: Metadata = {
  title: "世界の主要ニュース | Japan Lens",
  description: "世界の出来事を、各国の媒体はどう伝えたか。日本の主要媒体の見出しとも比べます。",
};

export default function World() {
  const feed = getWorld();
  // 掲載媒体を地域圏ごとに並べる
  const areas = ["米州", "欧州", "中東・アフリカ", "アジア", "オセアニア"];
  return (
    <div className="wrap">
      <header className="top">
        <div className="brand">
          <h1>
            <Link href="/" className="home-link">
              Japan <span>Lens</span>
            </Link>
          </h1>
          <p>世界の出来事を、世界はどう報じたか</p>
        </div>
        <Link href="/about" className="about-link header-about">このサイトを作った背景を読む →</Link>
      </header>
      <SiteNav current="world" />

      <WorldView feed={feed} />

      <section className="policy" aria-labelledby="world-policy-title">
        <h2 id="world-policy-title">掲載媒体について</h2>
        <p>
          「日本はどう報じられたか」と同じ媒体に、中東・アフリカ・中南米・ロシアなどの媒体を加えています。個々の媒体に政治的な立場の評価は付けていません。国営・政府系の媒体は、その国の政府の見方として載せますが、載せる出来事を選ぶときの国の数には数えていません。
        </p>
        <p>
          各社の世界・国際面のフィードから、1媒体あたり1日最大{feed.rules.per_outlet}件の見出しを集め、AIが同じ出来事ごとにまとめています。論調（批判的・好意的）は判定していません。評価する相手が出来事ごとに違うため、代わりに各国が何に焦点を当てたかを比べています。
        </p>
        {areas.map((area) => {
          const list = feed.outlets.filter((o) => feed.areas[o.country_code] === area);
          if (!list.length) return null;
          return (
            <div key={area} className="world-outlets">
              <h3>{area}</h3>
              <ul className="outlet-list">
                {list.map((o) => (
                  <li key={o.id}>
                    <span className="flag" aria-hidden="true">{o.flag}</span>
                    <span className="cc">{REGION_LABEL[o.country_code] ?? o.country_code}</span>
                    <a href={o.homepage} target="_blank" rel="noopener noreferrer">{o.name}</a>
                    <span className={o.ownership === "国営" || o.ownership === "政府系" ? "own-tag gov" : "own-tag"}>{o.ownership}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </section>

      <footer>
        <span>本文は掲載していません。見出し・リンク・自前の要約のみを表示し、記事は各媒体のサイトで読めます。</span>
        <span>出来事のまとめ、各国の伝え方、要約はAIによる自動判定です。見出しとリード文だけを材料にしているため、誤りを含むことがあります。</span>
        <span>「報道なし」は、このサイトが対象にしている媒体で報道が見つからなかった国です。その国のすべての媒体が報じていないという意味ではありません。</span>
      </footer>
    </div>
  );
}
