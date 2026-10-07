import Link from "next/link";
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
        <Link href="/about" className="about-link header-about">このサイトについて</Link>
      </header>

      <Link href="/about" className="about-banner">
        <span className="about-banner-kicker">なぜ海外の報道で日本を見るのか</span>
        <span className="about-banner-title">日本の報道を、そのまま信じにくい理由</span>
        <span className="about-banner-text">
          日本の報道の自由度は180か国中62位。誤報や「あえて報じない」こと、外国からの影響を確かめる仕組みがないことをまとめました。
        </span>
        <span className="about-banner-cta">このサイトを作った背景を読む →</span>
      </Link>

      <FeedView feed={feed} />

      <section className="policy" aria-labelledby="policy-title">
        <h2 id="policy-title">掲載媒体について</h2>
        <p>
          各国で政治的な立場の異なる媒体を、偏りが出ないよう組み合わせて選んでいます。個々の媒体に政治的な立場の評価は付けていません。日本の政治・外交・安全保障・経済などについて、日本の判断や行動が評価の対象になる出来事のうち、海外の{MIN_OUTLETS}つ以上の媒体が報じたものを掲載しています。「日本の立場」は日本の英字メディア（The Japan Times、JAPAN Forward）の報道などをもとにまとめ、海外の論調の集計には含めていません。
        </p>
        <p>
          <b>国営・政府系の媒体の扱い</b>：中国の国営メディアなど、国や政府が運営・出資する媒体は、その国の政府の見方を知る材料として掲載し、「国営」「政府系」と表示しています。ただし「海外の見方」の論調の集計には含めず、別に示しています。掲載の条件でも、同じ国の国営・政府系の媒体はまとめて1つと数え、国営・政府系ではない媒体が1つ以上報じた出来事だけを載せています。
        </p>
        <p>
          <b>日本の主要媒体の報道</b>：出来事ごとに、NHK・全国紙5紙・在京の民放4局のサイトを検索し、報道が見つかったかを示しています。「見つからなかった」は検索で見つからなかったという意味で、報じていないと断定するものではありません。
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
        <span>「報道なし」は、このサイトが対象にしている媒体で報道が見つからなかった国です。その国のすべての媒体が報じていないという意味ではありません。</span>
        <span>
          「AIで本文を読む」は、押したときだけその記事を取得し、AIが本文を読んで要約と論調を示します。媒体がAIによる閲覧を認めていない記事（robots.txt）や、有料記事は読めません。
        </span>
        <span>
          論調の判定の材料は媒体によって異なります。AIによる閲覧を認めている媒体は記事の本文を、認めていない媒体は見出しとリード文を使っています（各カードに表示）。
        </span>
      </footer>
    </div>
  );
}
