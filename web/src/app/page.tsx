import FeedView from "@/components/FeedView";
import { getFeed } from "@/lib/data";
import { MIN_OUTLETS } from "@/lib/rules";

export default function Home() {
  const feed = getFeed();

  return (
    <div className="wrap">
      <header className="top">
        <div className="brand">
          <h1>
            Japan <span>Lens</span>
          </h1>
          <p>海外メディアは日本をどう報じたか</p>
        </div>
        {feed.source === "sample" && (
          <div className="sample-note">サンプル表示中：媒体名・見出しは架空です。収集処理を動かすと実データに切り替わります</div>
        )}
      </header>

      <FeedView feed={feed} />

      <section className="policy" aria-labelledby="policy-title">
        <h2 id="policy-title">掲載媒体について</h2>
        <p>
          各国で政治的な立場の異なる媒体を、偏りが出ないよう組み合わせて選んでいます。選定には外部の評価機関の格付けを参考にしています。個々の媒体に政治的な立場の評価は付けていません。日本の政治・外交・安全保障・経済などについて、日本の判断や行動が評価の対象になる出来事のうち、{MIN_OUTLETS}つ以上の媒体が報じたものを掲載しています。
        </p>
        <ul className="outlet-list">
          {feed.outlets.map((o) => (
            <li key={o.id}>
              <span className="flag" aria-hidden="true">{o.flag}</span>
              <span className="cc">{o.country_code}</span>
              {o.homepage.startsWith("http") ? (
                <a href={o.homepage} target="_blank" rel="noopener noreferrer">{o.name}</a>
              ) : (
                o.name
              )}
              <span className="own-tag">{o.ownership}</span>
            </li>
          ))}
        </ul>
      </section>

      <footer>
        <span>本文は掲載していません。見出し・リンク・自前の要約のみを表示し、記事は各媒体のサイトで読めます。</span>
        <span>要約と記事の論調はAIによる自動判定です。誤りを含むことがあります。</span>
        <span>
          論調の判定の材料は媒体によって異なります。AIによる閲覧を認めている媒体は記事の本文を、認めていない媒体は見出しとリード文を使っています（各カードに表示）。
        </span>
      </footer>
    </div>
  );
}
