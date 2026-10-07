import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "このサイトについて | Japan Lens",
  description: "日本の報道をそのまま信じることのリスクと、海外の報道から日本を見るサイトを作った背景。",
};

// RSF 2026 日本の項目別の評価。説明は RSF の評価方法（methodology 2026）を要約したもの
const RSF_INDICATORS = [
  { name: "政治", rank: 67, desc: "政府や政党の圧力から、報道がどれだけ自立できているか" },
  { name: "経済", rank: 43, desc: "広告主や経営者、政府の政策によって、報じる内容が縛られていないか" },
  { name: "法制度", rank: 68, desc: "検閲を受けずに報道でき、取材源が法律で守られているか" },
  { name: "社会", rank: 108, desc: "社会の空気や慣習によって、特定の話題や組織を報じにくくなっていないか" },
  { name: "安全", rank: 52, desc: "記者が暴力や嫌がらせ、仕事上の報復を受けずに取材できるか" },
];

// ロイター研究所 Digital News Report の日本の媒体別「信頼できない」の割合（%）。2026年の高い順
const DISTRUST = [
  { name: "週刊文春", y2024: 35, y2025: 35, y2026: 36 },
  { name: "週刊新潮", y2024: 29, y2025: 29, y2026: 31 },
  { name: "朝日新聞", y2024: 20, y2025: 20, y2026: 21 },
  { name: "フジテレビ", y2024: 15, y2025: 29, y2026: 20 },
  { name: "産経新聞", y2024: 15, y2025: 18, y2026: 19 },
  { name: "毎日新聞", y2024: 17, y2025: 17, y2026: 18 },
  { name: "TBS", y2024: 15, y2025: 17, y2026: 18 },
  { name: "テレビ朝日", y2024: 16, y2025: 18, y2026: 18 },
  { name: "読売新聞", y2024: 14, y2025: 17, y2026: 17 },
  { name: "NHK", y2024: 13, y2025: 15, y2026: 16 },
  { name: "日本テレビ", y2024: 12, y2025: 17, y2026: 16 },
  { name: "日本経済新聞", y2024: 12, y2025: 13, y2026: 14 },
  { name: "Yahoo!ニュース", y2024: 15, y2025: 17, y2026: 14 },
  { name: "地方紙", y2024: 11, y2025: 13, y2026: 13 },
  { name: "テレビ東京", y2024: 12, y2025: 15, y2026: 13 },
];
const DISTRUST_MAX = 40;

type Case = { year: string; text: string };
type OutletCases = { outlet: string; cases: Case[] };

const ADMITTED_MORE: OutletCases[] = [
  {
    outlet: "朝日新聞",
    cases: [
      { year: "1989年", text: "沖縄のサンゴに付けられた落書きを報じましたが、傷はカメラマン自身が付けたものでした。社長が辞任しました。" },
      { year: "2014年", text: "福島第一原発の吉田昌郎所長の聴取記録（吉田調書）をめぐる記事を取り消し、社長が辞任しました。" },
    ],
  },
  {
    outlet: "読売新聞",
    cases: [
      { year: "2012年", text: "iPS細胞を使った世界初の臨床応用に成功したという研究者の話を1面で報じましたが、話は虚偽でした。おわびを掲載し、編集局長ら7人を処分しました。" },
      { year: "2024年", text: "紅麹サプリの問題で、取引先の社長の談話を記者が捏造していました。記者を諭旨退職とし、編集局の幹部を更迭しました。" },
    ],
  },
  {
    outlet: "毎日新聞",
    cases: [
      { year: "2008年", text: "英語版サイトのコラム「WaiWai」で、日本人の性に関する根拠のない記事を長年配信していました。おわびと検証記事を掲載し、関係者を処分しました。" },
      { year: "2024年", text: "芸能人のなりすましアカウントの投稿をもとに記事を配信し、削除しておわびしました。記事は外部の制作会社が作っていました。" },
    ],
  },
  {
    outlet: "産経新聞",
    cases: [
      { year: "2018年", text: "沖縄の事故で米兵が日本人を救助したと報じ、地元紙がそれを報じないと批判した記事を、事実を確認できなかったとして削除し、おわびしました。" },
      { year: "2020年", text: "フジテレビとの合同世論調査で、14回分・約2500件の架空の回答が見つかり、関連する記事を取り消しました。" },
      { year: "2011年", text: "中国の江沢民・元国家主席が死去したと報じましたが、誤報でした。" },
    ],
  },
  {
    outlet: "NHK",
    cases: [
      { year: "2021年", text: "東京五輪のドキュメンタリーで、取材相手が「五輪反対デモにお金をもらって参加した」という、確認していない字幕を付けました。放送倫理・番組向上機構（BPO）は重大な放送倫理違反と判断しました。" },
      { year: "2014年", text: "「クローズアップ現代」の出家詐欺の特集で、やらせが指摘されました。BPOは重大な放送倫理違反と判断しました。" },
      { year: "1993年", text: "「NHKスペシャル」のネパール・ムスタンの番組で、多くの場面にやらせがあったことがわかりました。" },
      { year: "2018年", text: "ニュースアプリなどで、北朝鮮がミサイルを発射したという誤った速報を流しました。" },
    ],
  },
  {
    outlet: "日本テレビ",
    cases: [{ year: "2009年", text: "「真相報道バンキシャ!」で、虚偽の証言をもとに岐阜県の裏金を報じました。社長が辞任しました。" }],
  },
  {
    outlet: "TBS",
    cases: [
      { year: "1989年", text: "坂本堤弁護士のインタビュー映像を、放送前にオウム真理教の幹部に見せていました。坂本弁護士一家はその後に殺害されています。TBSが事実を認めたのは1996年で、社長が辞任しました。" },
    ],
  },
  {
    outlet: "関西テレビ（フジテレビ系列）",
    cases: [{ year: "2007年", text: "「発掘!あるある大事典II」で、納豆のダイエット効果の実験データが捏造されていました。番組は打ち切られ、関西テレビは日本民間放送連盟から除名されました。" }],
  },
  {
    outlet: "テレビ朝日",
    cases: [{ year: "1985年", text: "「アフタヌーンショー」で、暴走族のリンチの場面を番組の側が仕込んでいました。" }],
  },
];

const COURT_MORE: OutletCases[] = [
  {
    outlet: "産経新聞",
    cases: [
      { year: "2017年", text: "沖縄県宮古島市の元市議についてのネット記事で、名誉毀損と認める判決が確定しました。記事が削除されたのは、掲載から6年以上たってからでした。" },
      { year: "2004年", text: "新潟の男性を国際テロ組織「アルカイダ」と関係があるかのように報じ、2007年の東京地裁判決で330万円の賠償を命じられました。男性は無関係で、同じように報じた共同通信にも賠償を命じる判決が出ています。" },
    ],
  },
];

const NOT_REPORTED_MORE: OutletCases[] = [
  {
    outlet: "フジテレビ",
    cases: [
      { year: "2025年", text: "中居正広さんの問題は、週刊誌の報道で明るみに出ました。第三者委員会は「業務の延長線上における性暴力」と認定し、経営陣が人権の問題として受け止められなかったと批判しました。" },
    ],
  },
  {
    outlet: "朝日新聞",
    cases: [{ year: "2014年", text: "自社の慰安婦報道を批判した池上彰さんのコラムの掲載を、いったん見送りました。社内外から批判を受けて掲載し、判断の誤りを認めて謝罪しました。" }],
  },
  {
    outlet: "NHK",
    cases: [{ year: "2001年", text: "戦時中の性暴力を扱った番組「ETV2001」が、放送前日に幹部が自民党の政治家と面会したあとで、内容を変えて放送されました。" }],
  },
];

const SOURCES: { section: string; links: { label: string; url: string }[] }[] = [
  {
    section: "報道の自由度",
    links: [
      { label: "RSF「Japan」国別ページ（2026年）", url: "https://rsf.org/en/country/japan" },
      { label: "RSF 2026年の評価方法", url: "https://rsf.org/en/methodology-used-compiling-world-press-freedom-index-2026" },
      { label: "nippon.com「報道の自由度ランキング」推移", url: "https://www.nippon.com/ja/japan-data/h02781/" },
      { label: "聯合報：台湾は28位（2026年）", url: "https://udn.com/news/story/7314/9474422" },
    ],
  },
  {
    section: "媒体ごとの不信度",
    links: [{ label: "ロイター研究所 Digital News Report 2026「Japan」", url: "https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/japan" }],
  },
  {
    section: "誤りを認めた例",
    links: [
      { label: "現代ビジネス：朝日新聞「従軍慰安婦」記事の取り消し", url: "https://gendai.media/articles/-/40260" },
      { label: "J-CAST：読売新聞、石破首相「退陣」誤報を謝罪", url: "https://www.j-cast.com/2025/09/03507264.html" },
      { label: "プレジデント：朝日新聞サンゴ記事ねつ造事件", url: "https://president.jp/articles/-/13435" },
      { label: "デイリー：朝日新聞 吉田調書でも記事取り消し", url: "https://www.daily.co.jp/gossip/2014/09/12/1p_0007322508.shtml" },
      { label: "文春オンライン：読売新聞の紅麹談話捏造", url: "https://bunshun.jp/articles/-/70637" },
      { label: "J-CAST：毎日新聞「WaiWai」問題で処分", url: "https://www.j-cast.com/2008/06/28022609.html" },
      { label: "アゴラ：毎日新聞、なりすましアカウントで記事を書き削除", url: "https://agora-web.jp/?p=448148" },
      { label: "琉球新報：産経新聞「おわびと削除」", url: "https://ryukyushimpo.jp/news/entry-661904.html" },
      { label: "デイリー：フジ・産経 世論調査で架空回答", url: "https://www.daily.co.jp/gossip/2020/06/19/0013436544.shtml" },
      { label: "ニューズウィーク日本版：江沢民死去の誤報", url: "https://www.newsweekjapan.jp/articles/-/5135" },
      { label: "プレジデント：BPO「河瀬直美が見つめた東京五輪」", url: "https://president.jp/articles/-/61631" },
      { label: "デイリー：「クローズアップ現代」やらせ問題", url: "https://www.daily.co.jp/newsflash/gossip/2015/05/14/0008025108.shtml" },
      { label: "ITmedia：NHK「ムスタン」やらせ事件", url: "https://www.itmedia.co.jp/news/article/2501/15/1250115079/2" },
      { label: "CNN：NHKがミサイル発射の誤速報", url: "https://www.cnn.co.jp/world/35113266.html" },
      { label: "The Japan Times：日本テレビ社長が辞任（バンキシャ）", url: "https://info.japantimes.co.jp/weekly/news/nn2009/nn20090321a1.htm" },
      { label: "imidas：発掘!あるある大事典II 捏造問題", url: "https://imidas.jp/genre/detail/F-106-0042.html" },
    ],
  },
  {
    section: "誤りを認めなかった例",
    links: [
      { label: "アゴラ：原英史氏の毎日新聞訴訟、勝訴が確定", url: "https://agora-web.jp/?p=403419" },
      { label: "琉球新報：産経新聞に記事削除と賠償命令（元宮古島市議）", url: "https://ryukyushimpo.jp/news/entry-1669909.html" },
      { label: "debito.org：産経新聞にアルカイダ報道で賠償命令", url: "https://www.debito.org/?p=849" },
      { label: "The Daily Star：共同通信にアルカイダ報道で賠償命令", url: "https://tds-images.thedailystar.net/2006/09/01/d60901012317.htm" },
      { label: "J-CAST：毎日新聞、石破首相の退陣報道を説明", url: "https://www.j-cast.com/2025/09/08507365.html" },
    ],
  },
  {
    section: "あえて報じなかった例",
    links: [
      { label: "J-CAST：テレビ局のジャニーズ報道の自己検証", url: "https://www.j-cast.com/2023/09/12468674.html?p=all" },
      { label: "J-CAST：ジャニーズ会見、新聞各社の社説", url: "https://www.j-cast.com/2023/10/04470218.html" },
      { label: "フジテレビ 第三者委員会 調査報告書（2025年3月31日）", url: "https://file.ray.co.jp/lw/jocx/doc/250331_2025033112520.pdf" },
      { label: "J-CAST：朝日新聞、いったんボツの池上コラムを掲載", url: "https://www.j-cast.com/2014/09/04214973.html" },
      { label: "しんぶん赤旗：NHK番組改変問題", url: "https://www.jcp.or.jp/akahata/aik4/2005-01-13/01_01.html" },
    ],
  },
  {
    section: "外国（中国）からの影響",
    links: [
      { label: "WION：米国の新聞にチャイナデイリーが支払った額（FARAの届け出）", url: "https://www.wionews.com/world/us-media-outlets-received-millions-of-dollars-from-china-to-sell-its-propaganda-report-396678" },
      { label: "China Media Project：China Daily USA", url: "https://chinamediaproject.org/2023/03/16/the-ins-and-outs-of-the-china-daily-usa/" },
      { label: "Freedom House：Beijing's Global Media Influence 2022", url: "https://freedomhouse.org/report/beijing-global-media-influence/2022/authoritarian-expansion-power-democratic-resilience" },
      { label: "Freedom House：米国の評価（2022年）", url: "https://freedomhouse.org/country/united-states/beijings-global-media-influence/2022" },
      { label: "Asian Review of Books：Silent Invasion", url: "https://asianreviewofbooks.com/silent-invasion-chinas-influence-in-australia-by-clive-hamilton/" },
      { label: "Apple Daily：ASPI報告（豪州の中国語メディア）", url: "https://collection.news/appledaily/articles/DIGOIZZMDRDIXEY7IW7PHAZZBI" },
      { label: "Friedrich Naumann Foundation：ドイツへの中国の影響", url: "https://freiheit.org/chinas-influence-germany-academia-and-media-are-achilles-heel" },
      { label: "Weblio：チャイナデイリー（毎日新聞のチャイナ・ウオッチ配布）", url: "https://www.weblio.jp/content/China_Daily" },
      { label: "Logically：処理水をめぐる中国の協調キャンペーン", url: "https://www.logically.ai/resources/fukushima-daiichi-wastewater-release" },
      { label: "笹川平和財団 IINA：中国の対日情報工作", url: "https://www.spf.org/iina/articles/ryohei_suzuki_01.html" },
      { label: "nippon.com：NHK中国語ラジオの発言で理事が辞任", url: "https://nippon.com/en/news/yjj2024091001071" },
      { label: "Adnkronos：自民党、外国代理人の届け出制度を検討", url: "https://english.adnkronos.com/2026/02/21/exclusive-ldp-eyes-mandatory-reporting-by-foreign-agents-in-japan/" },
      { label: "ニューズウィーク日本版：日本の情報機関改革", url: "https://www.newsweekjapan.jp/articles/-/323040" },
    ],
  },
  {
    section: "お金と権力との近さ",
    links: [
      { label: "文春オンライン：黒川検事長の賭けマージャン", url: "https://bunshun.jp/articles/-/38031" },
      { label: "J-CAST：官房機密費をめぐる証言", url: "https://www.j-cast.com/2010/05/30067532.html" },
      { label: "日本新聞協会：新聞への軽減税率の適用について", url: "https://www.pressnet.or.jp/news/20191001.pdf" },
    ],
  },
];

function More({ label, children }: { label: string; children: ReactNode }) {
  return (
    <details className="more">
      <summary>{label}</summary>
      <div className="more-body">{children}</div>
    </details>
  );
}

function CaseGroups({ groups }: { groups: OutletCases[] }) {
  return (
    <div className="case-groups">
      {groups.map((g) => (
        <div key={g.outlet} className="case-group">
          <h4>{g.outlet}</h4>
          <ul className="cases">
            {g.cases.map((c) => (
              <li key={c.year + c.text.slice(0, 8)}>
                <span className="case-year">{c.year}</span>
                {c.text}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

function DistrustChart() {
  return (
    <figure className="vbar">
      <figcaption>「この媒体のニュースは信頼できない」と答えた人の割合（ロイター研究所 2026年、日本）</figcaption>
      <div className="vbar-plot" role="img" aria-label="媒体ごとの不信度。高い順に、週刊文春36%、週刊新潮31%、朝日新聞21%、フジテレビ20%、産経新聞19%など">
        {DISTRUST.map((d) => (
          <div key={d.name} className="vbar-col" title={`${d.name}：${d.y2026}%`}>
            <span className="vbar-track">
              <span className="vbar-val">{d.y2026}</span>
              <span className="vbar-fill" style={{ height: `${(d.y2026 / DISTRUST_MAX) * 100}%` }} />
            </span>
            <span className="vbar-name">{d.name}</span>
          </div>
        ))}
      </div>
      <p className="vbar-unit">単位：%　左ほど不信が高い</p>
    </figure>
  );
}

export default function About() {
  return (
    <div className="wrap">
      <header className="top">
        <div className="brand">
          <h1>
            <Link href="/" className="home-link">
              Japan <span>Lens</span>
            </Link>
          </h1>
          <p>このサイトについて</p>
        </div>
        <Link href="/" className="about-link">← 出来事の一覧へ</Link>
      </header>

      <article className="about">
        <div className="about-lead">
          <h2>日本の報道をそのまま信じることのリスク</h2>
        </div>

        <section>
          <h2>なぜ作ったのか</h2>
          <p>
            日本の新聞やテレビの報道には、事実と誤りが混ざった記事がときどき見つかります。報道が一方向に偏りやすい仕組みがあることも、国内外から指摘されています。
          </p>
          <p>さらに日本には、外国からの影響を含めて、報道がゆがめられていないかを確かめる仕組みがほとんどありません。</p>
          <p>
            そこでこのサイトでは、日本の判断や行動について海外の媒体がどう報じたかを、出来事ごとに集めて並べています。日本の報道だけに頼らず、外からの視点で日本を見るためのサイトです。
          </p>
        </section>

        <section>
          <h2>報道の自由度は180か国中62位</h2>
          <p>
            国境なき記者団（RSF）は、記者が政治や経済、法律、社会からの干渉を受けずに報道できているかを、毎年180の国と地域で評価しています。
          </p>
          <p>
            2026年の日本は<b>62位</b>（100点満点で62.90点）でした。RSFは点数で国を5段階に分けていて、日本は「問題がある」と評価されています。アジアでも台湾（28位）や韓国（47位）より低く、先進国としてはかなり低い評価です。2010年前後は10位台でしたが、2013年以降は60〜70位台が続いています。
          </p>
          <h3>5つの評価項目</h3>
          <p>順位は次の5つの項目で決まります。</p>
          <div className="about-table-wrap">
            <table className="about-table indicators">
              <caption>RSF 2026年 日本の項目別の順位（180か国・地域中）</caption>
              <thead>
                <tr>
                  <th scope="col">項目</th>
                  <th scope="col">何を見ているか</th>
                  <th scope="col">順位</th>
                </tr>
              </thead>
              <tbody>
                {RSF_INDICATORS.map((r) => (
                  <tr key={r.name} className={r.rank > 100 ? "weak" : undefined}>
                    <th scope="row">{r.name}</th>
                    <td className="desc">{r.desc}</td>
                    <td>{r.rank}位</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            日本は、記者の身の安全は比較的守られています。一方で、いちばん低い「社会」は108位でした。RSFはその理由を「政府や企業が日常的に圧力をかけ、記者が敏感な話題を自分から避ける自己検閲が広がっている」と書いています。伝えるべきことが伝えられていない可能性を示す評価です。
          </p>
        </section>

        <section>
          <h2>媒体ごとの不信度</h2>
          <p>
            日本の新聞やテレビの偏りを、外部の機関が継続して格付けしている例は見当たりません。いちばん近いのが、英オックスフォード大学ロイター研究所が毎年行っている調査です。これは<b>利用者へのアンケート</b>で、「この媒体のニュースを信頼できるか」を0〜10で答えてもらいます。報道の正確さを専門家が調べたものではありません。調べている媒体は毎年同じ15です。
          </p>
          <DistrustChart />
          <p>出来事があると不信は動きます。フジテレビは、中居正広さんの問題が明るみに出た2025年に、15%から29%へほぼ倍になりました。</p>
          <More label="年ごとの変化を見る">
            <div className="about-table-wrap">
              <table className="about-table years">
                <caption>「信頼できない」と答えた人の割合（%）</caption>
                <thead>
                  <tr>
                    <th scope="col">媒体</th>
                    <th scope="col">2024年</th>
                    <th scope="col">2025年</th>
                    <th scope="col">2026年</th>
                  </tr>
                </thead>
                <tbody>
                  {DISTRUST.map((d) => (
                    <tr key={d.name}>
                      <th scope="row">{d.name}</th>
                      <td>{d.y2024}</td>
                      <td>{d.y2025}</td>
                      <td>{d.y2026}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </More>
        </section>

        <section>
          <h2>誤りを認めた例</h2>
          <p>大手の報道機関でも、誤った内容を事実として報じ、あとから取り消した例がいくつもあります。特定の会社や立場に限った話ではありません。</p>
          <ul className="cases">
            <li>
              <span className="case-year">朝日新聞 2014年</span>
              慰安婦問題で、吉田清治氏の「強制連行した」という証言を扱った一連の記事を、証言が虚偽だったとして取り消しました。最初の記事から32年後のことです。
            </li>
            <li>
              <span className="case-year">読売新聞 2025年</span>
              「石破首相退陣へ」と報じた記事について、「結果として誤報となった」と謝罪し、編集局長らを処分しました。
            </li>
          </ul>
          <More label="ほかの例を見る">
            <CaseGroups groups={ADMITTED_MORE} />
          </More>
        </section>

        <section>
          <h2>誤りを認めなかった例</h2>
          <p>
            誤りを認めないまま、裁判で名誉毀損と認められた記事もあります。名誉毀損と認められたのは、記事の内容を真実と信じるだけの十分な根拠を、報道機関が示せなかったということです。
          </p>
          <ul className="cases">
            <li>
              <span className="case-year">毎日新聞 2019年</span>
              国家戦略特区のワーキンググループ委員だった原英史さんについての記事。2024年に最高裁で毎日の敗訴が確定し、220万円の賠償が命じられました。
            </li>
          </ul>
          <More label="ほかの例を見る">
            <CaseGroups groups={COURT_MORE} />
            <h4 className="more-sub">謝罪や訂正をしなかった例</h4>
            <ul className="cases">
              <li>
                <span className="case-year">毎日新聞 2025年</span>
                読売と同じく「石破首相退陣へ」と報じました。読売が謝罪したのに対し、毎日は記事を出した経緯を説明しただけでした。
              </li>
            </ul>
          </More>
        </section>

        <section>
          <h2>あえて報じなかった例</h2>
          <p>誤報よりも見えにくいのが、知っていても報じないことです。</p>
          <p>
            旧ジャニーズ事務所の創業者による性加害は、週刊誌の報道や裁判で早くから知られていました。しかし国内の大手の新聞やテレビは、ほとんど報じてきませんでした。2023年に英BBCがドキュメンタリーで取り上げたことで、ようやく国内でも大きく扱われるようになりました。
          </p>
          <p>
            NHK、日本テレビ、TBSは、報じてこなかった理由を自ら検証する番組を放送しました。そこで挙げられた理由は、芸能スキャンダルを軽く見ていたこと、そして出演者の起用をめぐって事務所に忖度していたことです。一方、大手新聞の社説で「メディアの責任」に触れたものは少数でした。
          </p>
          <p>
            誤報は訂正記事として記録に残ります。しかし報じなかったことは、自分から検証しないかぎり記録に残りません。ジャニーズの問題は、ほぼ唯一の大規模な自己検証です。
          </p>
          <More label="ほかの例を見る">
            <CaseGroups groups={NOT_REPORTED_MORE} />
          </More>
        </section>

        <section>
          <h2>偏向報道が起きる理由</h2>

          <h3>外国（中国）からの影響</h3>
          <p>米国、オーストラリア、ドイツでは、中国政府が報道に影響を与えようとしてきたことが、調査や法律によって明らかになっています。</p>
          <div className="about-table-wrap">
            <table className="about-table countries">
              <caption>各国で明らかになったこと</caption>
              <tbody>
                <tr>
                  <th scope="row">米国</th>
                  <td>
                    中国政府系の英字紙チャイナデイリーが、ワシントン・ポストに460万ドル以上、ウォール・ストリート・ジャーナルに約600万ドルを払い、記事のように見える宣伝の付録「China Watch」を新聞に挟んでいました。
                  </td>
                </tr>
                <tr>
                  <th scope="row">オーストラリア</th>
                  <td>中国共産党とつながる実業家から献金を受けた上院議員が辞職しました。中国語メディアの多くも、北京寄りの勢力の影響下にあると報告されています。</td>
                </tr>
                <tr>
                  <th scope="row">ドイツ</th>
                  <td>大手紙が、China Watchの有料コンテンツを掲載していました。最大の通信社dpaのニュースレターには、中国国営の新華社の記事が載りました。</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>
            日本でも、毎日新聞が2016年8月からChina Watchを配っています。2023年に福島第一原発の処理水の放出が始まった際は、中国の国営メディアや政府関係者が、事実と異なる情報をSNSで一斉に広めました。
          </p>
          <More label="各国の詳しい状況を見る">
            <h4 className="more-sub">米国</h4>
            <ul className="plain">
              <li>
                米国には、外国の代理人に活動の届け出を義務づける法律（外国代理人登録法、FARA）があります。チャイナデイリーの支払いは、この届け出から明らかになりました。米国の新聞への広告費は、2016年11月から2020年までで約1100万ドルです。Time誌やロサンゼルス・タイムズなどにも支払っていました。
              </li>
              <li>
                米国の人権団体フリーダムハウスの2022年の調査では、中国による影響工作の強さは「非常に高い」と評価されました。一方で、社会がそれを見抜いて跳ね返す力も「非常に高い」とされています。
              </li>
            </ul>
            <h4 className="more-sub">オーストラリア</h4>
            <ul className="plain">
              <li>
                2018年、労働党のダスティアリ上院議員が辞職しました。中国共産党とつながる実業家から献金を受け、南シナ海の問題で党の方針と違う発言をしていました。クライブ・ハミルトン氏の著書『サイレント・インベージョン』（日本語版『目に見えぬ侵略』）は、この事件をきっかけに書かれました。
              </li>
              <li>
                豪州戦略政策研究所（ASPI）の2020年の報告によると、豪州の中国語メディアのうち、少なくとも4社が中国共産党から資金を受けているか、党に所有されていました。さらに17社が、中国政府の在外華人向けの部署と近い関係にありました。
              </li>
              <li>豪州は2018年に、外国からの干渉を取り締まる法律と、外国の影響を受けた活動を登録させる制度をつくりました。</li>
            </ul>
            <h4 className="more-sub">ドイツ</h4>
            <ul className="plain">
              <li>ハンデルスブラット、南ドイツ新聞、フランクフルター・アルゲマイネ（FAZ）が、China Watchの有料コンテンツを掲載していました。</li>
              <li>台湾のシンクタンクの調査では、ドイツで中国の影響を最も受けやすい分野は「大学」と「メディア」とされています。</li>
            </ul>
            <h4 className="more-sub">日本</h4>
            <ul className="plain">
              <li>
                処理水をめぐっては、中国の国営メディア、政府関係者、インフルエンサーによる投稿が2023年7月に集中し、独自の投稿だけで3500件を超えました。
              </li>
              <li>
                2024年、NHKの中国語ラジオで、中国籍の外部スタッフが原稿にない「尖閣諸島は中国の領土」という発言をしました。NHKは謝罪し、担当の理事が辞任しました。組織的な工作だったという証拠は示されていません。
              </li>
              <li>
                日本政府は、処理水、沖縄、尖閣をめぐる情報工作の例が多数あると指摘しています。狙いは、日本の評価を下げること、同盟国との間を裂くこと、国内を分断することだとしています。
              </li>
            </ul>
          </More>

          <h3>日本には確かめる仕組みがない</h3>
          <p>米国では、届け出の義務があったから、中国からの支払いの額まで明らかになりました。オーストラリアは法律をつくり、ドイツでも調査が進んでいます。</p>
          <p>
            日本には、外国の代理人に届け出をさせる法律がありません。自民党が検討を始めていますが、制度づくりは2027年以降になる見通しです。フリーダムハウスが30か国を調べた2022年の調査にも、日本は入っていません。
          </p>
          <p className="about-emph">日本の報道に外国の影響があるとしても、今の日本では、それに気づくことができない状態です。</p>

          <h3>報道の仕組みの問題</h3>
          <p>国内の仕組みにも、報道を一方向に寄せやすい特徴があります。</p>
          <ul className="plain">
            <li>
              <b>記者クラブ</b>：官庁や政党の記者会見に出られるのは、多くの場合、大手の報道機関でつくる記者クラブの会員だけです。各社が同じ説明を聞いて記事を書くため、報道が当局の発表に寄り、各社で似た内容になります。
            </li>
            <li>
              <b>政府と放送局の近さ</b>：テレビ局の免許は、独立した委員会ではなく政府（総務省）が出しています。
            </li>
            <li>
              <b>新聞とテレビの系列</b>：読売、朝日、日経、毎日、フジ・産経の5つのグループが、新聞とテレビ局をそれぞれ持っていて、互いを批判しにくくなっています。
            </li>
          </ul>
          <More label="詳しく見る">
            <ul className="plain">
              <li>2016年、総務大臣が国会で、政治的に公平でない放送を繰り返す局には電波の停止もありうると答弁しました。国連の特別報告者は2017年、政府から独立した放送の監督機関をつくるよう日本に勧めています。</li>
              <li>同じ会社が新聞とテレビを持つこと（クロスオーナーシップ）を制限する規制は、日本にはありません。</li>
              <li>特定秘密保護法は、秘密に指定された情報を不正に得て公表すると、最長10年の懲役になりうる法律です。RSFは、取材源を守る仕組みが不十分だと指摘しています。</li>
            </ul>
          </More>

          <h3>お金と権力との近さ</h3>
          <More label="詳しく見る">
            <ul className="plain">
              <li>
                <b>検事長との賭けマージャン（2020年）</b>：東京高検の黒川弘務検事長が、緊急事態宣言の最中に、産経新聞の記者2人と朝日新聞の社員と賭けマージャンをしていたことがわかり、辞職しました。
              </li>
              <li>
                <b>官房機密費（2010年）</b>：野中広務・元官房長官が、在任中に官房機密費から政治評論家に「盆暮れに500万円ずつ」届けていたと証言しました。
              </li>
              <li>
                <b>新聞の軽減税率（2019年）</b>：新聞業界は、新聞を消費税の軽減税率の対象にするよう求め、実際に対象になりました。
              </li>
            </ul>
          </More>
        </section>

        <section>
          <h2>まとめ</h2>
          <p>
            日本の報道は、記者の安全が守られ、新聞やテレビも身近な存在です。しかし報道の自由度は先進国の中でかなり低く、大手の媒体でも誤報や、知っていて報じないことが繰り返されてきました。外国からの影響を確かめる仕組みもありません。
          </p>
          <p>
            日本のニュースは、それだけをそのまま信じるのではなく、ほかの見方と照らし合わせて読む必要があります。Japan Lensは、そのために海外の報道を出来事ごとに並べています。
          </p>
          <p>
            海外の媒体にも、それぞれの国の事情や立場による偏りがあります。そのためこのサイトでは、1つの国や1つの媒体ではなく、複数の国の、立場の異なる媒体を並べています。中国の国営メディアも、中国政府の見方を知る材料として掲載していますが、「国営」と表示し、「海外の見方」の論調の集計からは外しています。同じ国の国営メディアだけが報じた出来事は載せません。また出来事ごとに、日本の主要媒体（NHK・全国紙・在京の民放）のサイトで報道が見つかったかを示しています。
          </p>
        </section>

        <section className="about-sources">
          <h2>出典</h2>
          <More label="出典を見る">
            {SOURCES.map((s) => (
              <div key={s.section}>
                <h4 className="more-sub">{s.section}</h4>
                <ul>
                  {s.links.map((l) => (
                    <li key={l.url}>
                      <a href={l.url} target="_blank" rel="noopener noreferrer">
                        {l.label} ↗
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </More>
        </section>
      </article>
    </div>
  );
}
