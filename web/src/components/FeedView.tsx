"use client";

import { useEffect, useMemo, useState } from "react";
import { isGovernment, JAPAN_MAIN_COUNT, MIN_OUTLETS } from "@/lib/rules";
import { REGION_LABEL } from "@/lib/regions";
import type { Article, Feed, NewsEvent, Outlet, Tone } from "@/lib/types";

const TONES: { key: Tone; label: string }[] = [
  { key: "crit", label: "批判的" },
  { key: "neu", label: "中立" },
  { key: "fav", label: "好意的" },
];
const TONE_LABEL: Record<Tone, string> = { crit: "批判的", neu: "中立", fav: "好意的", none: "評価なし" };
const TONE_RANK: Record<Tone, number> = { crit: 0, neu: 1, fav: 2, none: 3 };

type Sort = "tone" | "time";
type Lang = "en" | "ja";

// サーバーとブラウザで表示がずれないよう、常に日本時間で表示する
const JST = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});
const JST_DATE = new Intl.DateTimeFormat("sv-SE", { timeZone: "Asia/Tokyo" });

function formatTime(iso: string) {
  return JST.format(new Date(iso));
}

function ToneBar({ articles, target }: { articles: Article[]; target?: string }) {
  // 「評価なし」の記事は割合に含めない
  const judged = articles.filter((a) => a.tone !== "none");
  const unjudged = articles.length - judged.length;
  if (!target) {
    return <p className="dist-note">評価の対象がない出来事のため、論調は判定していません。各社の切り口を比べてください。</p>;
  }
  if (judged.length === 0) {
    return (
      <p className="dist-note">
        「{target}」について、見出しとリード文から論調を判断できる記事はありませんでした。
      </p>
    );
  }
  const total = judged.length;
  const counts = TONES.map((t) => ({ ...t, n: judged.filter((a) => a.tone === t.key).length }));
  return (
    <div className="dist" aria-label="記事の論調の分布">
      <div className="dist-ttl">
        「{target}」への論調{unjudged > 0 && <span className="dist-sub">（評価なし {unjudged}件を除く）</span>}
      </div>
      <div className="bar">
        {counts
          .filter((c) => c.n)
          .map((c) => (
            <span key={c.key} style={{ width: `${(c.n / total) * 100}%`, background: `var(--${c.key})` }} title={`${c.label} ${c.n}件`} />
          ))}
      </div>
      <div className="dist-lbl">
        {counts.map((c) => (
          <span key={c.key}>
            {c.label} <b>{c.n}</b>
          </span>
        ))}
      </div>
    </div>
  );
}

/** 国営・政府系の媒体の論調。「海外の見方」の集計には含めず、国ごとに分けて示す */
function GovernmentTone({ articles, outlets }: { articles: Article[]; outlets: Map<string, Outlet> }) {
  if (articles.length === 0) return null;
  const byCountry = new Map<string, Article[]>();
  for (const a of articles) {
    const c = outlets.get(a.outlet_id)?.country_code ?? "";
    byCountry.set(c, [...(byCountry.get(c) ?? []), a]);
  }
  return (
    <div className="gov-tone">
      <p className="gov-tone-ttl">国営・政府系メディアの論調（上の集計には含めていません）</p>
      <ul>
        {[...byCountry].map(([c, list]) => {
          const names = [...new Set(list.map((a) => outlets.get(a.outlet_id)?.name ?? a.outlet_id))].join("・");
          const counts = (["crit", "neu", "fav", "none"] as Tone[])
            .map((t) => ({ t, n: list.filter((a) => a.tone === t).length }))
            .filter((x) => x.n);
          return (
            <li key={c}>
              <b>{COUNTRY_LABEL[c] ?? c}</b>
              <span className="gov-tone-names">{names}</span>
              {counts.map((x) => (
                <span key={x.t} className={`tone ${x.t}`}>
                  {TONE_LABEL[x.t]} {x.n}
                </span>
              ))}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

type Reading =
  | { status: "ok"; summary_ja: string; angle: string; tone: Tone; evidence: string }
  | { status: "blocked" | "unavailable" | "error"; message: string };
// 読者が本文を読ませた記事の判定（worker/index.ts の /api/readings）。記事の id → 判定
type Readings = Record<string, { tone: Tone; angle: string; evidence: string }>;
type OnRead = (articleId: string, reading: { tone: Tone; angle: string; evidence: string }) => void;

type ReadState = "idle" | "loading" | Reading;

/**
 * 記事の本文を AI に読ませて要約と論調を出す（worker/index.ts）。
 * 「AIで本文を読む」を押したときと、「記事へ」で記事を開いたときに動く（読者の操作があったときだけ）
 */
function useReadWithAI(articleId: string, onRead: OnRead) {
  const [state, setState] = useState<ReadState>("idle");
  const run = async () => {
    if (state !== "idle") return; // 読み込み中・読み込み済みなら何もしない
    setState("loading");
    try {
      const res = await fetch("/api/read", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ id: articleId }),
        // 記事を新しいタブで開いた直後でも、要求を最後まで送る
        keepalive: true,
      });
      const reading = (await res.json()) as Reading;
      setState(reading);
      // 本文での判定をカード・論調の分布・国ごとの色に反映する
      if (reading.status === "ok") onRead(articleId, reading);
    } catch {
      setState({ status: "error", message: "読み込みに失敗しました。時間をおいて試してください。" });
    }
  };
  return { state, run };
}

function ReadWithAI({ state, run }: { state: ReadState; run: () => void }) {
  if (state === "idle") {
    return (
      <button className="read-ai" onClick={run}>
        AIで本文を読む
      </button>
    );
  }
  if (state === "loading") return <p className="read-ai-note" role="status">AIが本文を読んでいます…</p>;
  if (state.status !== "ok") return <p className="read-ai-note">{state.message}</p>;
  return (
    <div className="read-ai-result">
      <p className="read-ai-ttl">
        AIが本文を読んだ要約
        <span className={`tone ${state.tone}`}>本文での論調：{TONE_LABEL[state.tone]}</span>
      </p>
      <p>{state.summary_ja}</p>
      {state.evidence && (
        <p className="evidence">
          根拠 <q lang="en">{state.evidence}</q>
        </p>
      )}
    </div>
  );
}

function ArticleCard({ article, outlet, lang, onRead }: { article: Article; outlet?: Outlet; lang: Lang; onRead: OnRead }) {
  const external = article.url.startsWith("http");
  const reading = useReadWithAI(article.id, onRead);
  return (
    <article className="card">
      <div className="band" style={{ background: `var(--${article.tone})` }} />
      <div className="card-body">
        <div className="outlet">
          <span className="flag" aria-hidden="true">{outlet?.flag}</span>
          <span className="cc">{outlet?.country_code}</span>
          <b>{outlet?.name ?? article.outlet_id}</b>
          {outlet && <span className={isGovernment(outlet) ? "own-tag gov" : "own-tag"}>{outlet.ownership}</span>}
          {article.kind === "opinion" && <span className="kind-tag">解説・論説</span>}
        </div>
        {article.angle && <p className="angle">切り口：{article.angle}</p>}
        {lang === "en" ? (
          <>
            <p className="headline" lang="en">{article.title}</p>
            <p className="summary">{article.summary_ja}</p>
          </>
        ) : (
          <>
            <p className="headline">{article.summary_ja}</p>
            <p className="summary" lang="en">{article.title}</p>
          </>
        )}
        {article.evidence && (
          <p className="evidence">
            根拠 <q lang="en">{article.evidence}</q>
          </p>
        )}
        {external && <ReadWithAI state={reading.state} run={reading.run} />}
        <div className="card-foot">
          <span className="tone-wrap">
            <span className={`tone ${article.tone}`}>{TONE_LABEL[article.tone]}</span>
            <span
              className="basis"
              title={
                article.read_by_reader
                  ? "読者の操作でAIが記事の本文を読んで判定"
                  : article.basis === "body"
                    ? "記事の本文を読んで判定"
                    : "見出しとリード文から判定"
              }
            >
              {article.basis === "body" ? "本文で判定" : "見出しで判定"}
            </span>
          </span>
          <time className="time" dateTime={article.published_at}>{formatTime(article.published_at)}</time>
          {external ? (
            // 記事を開いたら、裏で AI に本文を読ませる（ページの移動は妨げない）
            <a href={article.url} target="_blank" rel="noopener noreferrer" onClick={() => void reading.run()}>
              記事へ ↗
            </a>
          ) : (
            <span className="time">サンプル</span>
          )}
        </div>
      </div>
    </article>
  );
}

const BASIS_NOTE: Record<string, string> = {
  japanese_media: "日本の媒体（The Japan Times・JAPAN Forward）の報道から",
  overseas_reports: "海外の記事が伝えた日本側の説明から",
};

function JapanLinks({ articles, outlets }: { articles: Article[]; outlets: Map<string, Outlet> }) {
  if (articles.length === 0) return null;
  return (
    <div className="jp-links">
      <p className="jp-links-ttl">日本の報道</p>
      <ul>
        {articles.map((a) => (
          <li key={a.id}>
            <span className="jp-links-outlet">{outlets.get(a.outlet_id)?.name ?? a.outlet_id}</span>
            {a.url.startsWith("http") ? (
              <a href={a.url} target="_blank" rel="noopener noreferrer" lang="en">
                {a.title} ↗
              </a>
            ) : (
              <span lang="en">{a.title}</span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

/** 日本の主要媒体（NHK・全国紙・在京キー局）がこの出来事を報じたか。「あえて報じない」を見えるようにする */
function JapanMainCoverage({ ev }: { ev: NewsEvent }) {
  if (!ev.japan_main_checked_at) return null;
  const found = ev.japan_main ?? [];
  if (found.length === 0) {
    return (
      <div className="jp-main none">
        <p className="jp-main-ttl">日本の主要媒体では、この出来事の報道が見つかりませんでした</p>
        <p className="jp-main-note">
          NHK・全国紙5紙・在京の民放4局のサイトを検索した結果です。報じていないと断定するものではありません。
        </p>
      </div>
    );
  }
  // 媒体ごとに1件ずつ示す
  const first = new Map<string, (typeof found)[number]>();
  for (const f of found) if (!first.has(f.outlet)) first.set(f.outlet, f);
  return (
    <div className="jp-main">
      <p className="jp-main-ttl">日本の主要媒体の報道（{JAPAN_MAIN_COUNT}媒体中{first.size}媒体で見つかりました）</p>
      <div className="jp-main-chips">
        {[...first.values()].map((f) => (
          <a key={f.outlet} className="jp-main-chip" href={f.url} target="_blank" rel="noopener noreferrer" title={f.title}>
            {f.outlet} ↗
          </a>
        ))}
      </div>
    </div>
  );
}

function Summary({
  ev,
  overseas,
  japan,
  outlets,
}: {
  ev: NewsEvent;
  overseas: Article[];
  japan: Article[];
  outlets: Map<string, Outlet>;
}) {
  const independent = overseas.filter((a) => !isGovernment(outlets.get(a.outlet_id)));
  const government = overseas.filter((a) => isGovernment(outlets.get(a.outlet_id)));
  return (
    <div className="summary-grid">
      <section className="stance japan" aria-label="日本の立場">
        <h3>日本の立場</h3>
        {ev.japan_position_ja ? (
          <>
            <p>{ev.japan_position_ja}</p>
            {ev.japan_views && ev.japan_views.length > 0 && (
              <div className="jp-views">
                {ev.japan_split && <p className="jp-split">日本の報道の間でも見方が分かれています</p>}
                <ul>
                  {ev.japan_views.map((v) => (
                    <li key={v.outlet}>
                      <b>{v.outlet}</b>
                      {v.view_ja}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {ev.japan_basis && BASIS_NOTE[ev.japan_basis] && <p className="stance-note">{BASIS_NOTE[ev.japan_basis]}</p>}
          </>
        ) : (
          <p className="stance-empty">日本側の立場を示す報道はまだ集まっていません。</p>
        )}
        <JapanLinks articles={japan} outlets={outlets} />
        <JapanMainCoverage ev={ev} />
      </section>
      <section className="stance overseas" aria-label="海外の見方">
        <h3>それに対して、海外では</h3>
        {ev.overseas_view_ja ? <p>{ev.overseas_view_ja}</p> : <p className="stance-empty">まとめを作成中です。</p>}
        <ToneBar articles={independent} target={ev.target} />
        {ev.target && <GovernmentTone articles={government} outlets={outlets} />}
      </section>
    </div>
  );
}

const COUNTRY_LABEL: Record<string, string> = { ...REGION_LABEL };

/** どの国の媒体が報じ、どの国が報じていないか。報じた国は多い論調の色で示す */
function Coverage({
  overseas,
  outlets,
  countries,
}: {
  overseas: Article[];
  outlets: Map<string, Outlet>;
  countries: string[];
}) {
  const byCountry = new Map<string, Article[]>();
  for (const a of overseas) {
    const c = outlets.get(a.outlet_id)?.region;
    if (!c) continue;
    byCountry.set(c, [...(byCountry.get(c) ?? []), a]);
  }
  const reported = countries.filter((c) => byCountry.has(c));
  const govOnly = (list: Article[]) => list.every((a) => isGovernment(outlets.get(a.outlet_id)));
  const silent = countries.filter((c) => !byCountry.has(c));
  const mainTone = (list: Article[]): Tone => {
    const judged = list.filter((a) => a.tone !== "none");
    if (!judged.length) return "none";
    const n = (t: Tone) => judged.filter((a) => a.tone === t).length;
    return (["crit", "fav", "neu"] as Tone[]).sort((x, y) => n(y) - n(x))[0];
  };
  return (
    <div className="coverage">
      {reported.length === 1 && (
        <p className="only-one">{COUNTRY_LABEL[reported[0]] ?? reported[0]}の媒体だけが報じた出来事です</p>
      )}
      <div className="coverage-row">
        <span className="coverage-lbl">報じた国</span>
        {reported.map((c) => {
          const list = byCountry.get(c)!;
          if (govOnly(list)) {
            return (
              <span key={c} className="cov-chip on gov" title={`${COUNTRY_LABEL[c] ?? c}: 国営・政府系の媒体だけが報じています（${list.length}件）`}>
                {COUNTRY_LABEL[c] ?? c}（政府系のみ）
              </span>
            );
          }
          const t = mainTone(list.filter((a) => !isGovernment(outlets.get(a.outlet_id))));
          return (
            <span key={c} className={`cov-chip on ${t}`} title={`${COUNTRY_LABEL[c] ?? c}: ${list.length}件（${TONE_LABEL[t]}が中心）`}>
              {COUNTRY_LABEL[c] ?? c}
            </span>
          );
        })}
      </div>
      {silent.length > 0 && (
        <div className="coverage-row">
          <span className="coverage-lbl">報道なし</span>
          {silent.map((c) => (
            <span key={c} className="cov-chip off">
              {COUNTRY_LABEL[c] ?? c}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

type Tab = "overseas" | "japan";

function ArticlesPanel({
  eventId,
  overseas,
  japan,
  outlets,
  lang,
  region,
  onRead,
}: {
  eventId: string;
  overseas: Article[];
  japan: Article[];
  outlets: Map<string, Outlet>;
  lang: Lang;
  region: string;
  onRead: OnRead;
}) {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("overseas");
  const shown = tab === "overseas" ? overseas.filter((a) => region === "all" || outlets.get(a.outlet_id)?.region === region) : japan;
  const panelId = `articles-${eventId}`;
  return (
    <div className="articles">
      <button
        id={`toggle-${eventId}`}
        className="articles-toggle"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen(!open)}
      >
        {open ? "各社の記事を閉じる" : "各社の記事を見る"}
        <span className="articles-count">
          海外 {overseas.length}件{japan.length > 0 && ` ・ 日本 ${japan.length}件`}
        </span>
      </button>
      {open && (
        <div id={panelId}>
          <div className="tabs" role="tablist" aria-label="記事の種類">
            <button id={`tab-overseas-${eventId}`} role="tab" aria-selected={tab === "overseas"} onClick={() => setTab("overseas")}>
              海外の報道 <span>{overseas.length}</span>
            </button>
            <button
              id={`tab-japan-${eventId}`}
              role="tab"
              aria-selected={tab === "japan"}
              onClick={() => setTab("japan")}
              disabled={japan.length === 0}
            >
              日本の報道 <span>{japan.length}</span>
            </button>
          </div>
          {shown.length ? (
            <div className="cards" role="tabpanel">
              {shown.map((a) => (
                <ArticleCard key={a.id} article={a} outlet={outlets.get(a.outlet_id)} lang={lang} onRead={onRead} />
              ))}
            </div>
          ) : (
            <p className="empty">この地域の媒体はこの出来事を報じていません。</p>
          )}
        </div>
      )}
    </div>
  );
}

export default function FeedView({ feed }: { feed: Feed }) {
  const [region, setRegion] = useState("all");
  const [sort, setSort] = useState<Sort>("tone");
  const [lang, setLang] = useState<Lang>("en");
  const [onlyOne, setOnlyOne] = useState(false);
  const [noJapanMain, setNoJapanMain] = useState(false);
  const [readings, setReadings] = useState<Readings>({});

  // 誰かが「AIで本文を読む」を押した記事は、全員の画面で本文での判定に置き換える
  useEffect(() => {
    fetch("/api/readings")
      .then((res) => (res.ok ? res.json() : {}))
      .then((data: Readings) => setReadings(data))
      .catch(() => {}); // 読み込めなければ見出しでの判定のまま表示する
  }, []);
  const onRead: OnRead = (id, r) => setReadings((prev) => ({ ...prev, [id]: r }));
  const withReading = (a: Article): Article => {
    const r = readings[a.id];
    return r ? { ...a, tone: r.tone, angle: r.angle || a.angle, evidence: r.evidence, basis: "body", read_by_reader: true } : a;
  };

  const outlets = useMemo(() => new Map(feed.outlets.map((o) => [o.id, o])), [feed.outlets]);
  // 対象にしている海外の国・地域（「報道なし」の表示に使う。日本の媒体は「日本の報道」タブにまとめる）
  const regions = useMemo(
    () => [...new Set(feed.outlets.filter((o) => o.side !== "japan").map((o) => o.region))],
    [feed.outlets],
  );
  // 地域の絞り込みには、掲載中の出来事に記事がある国・地域だけを出す
  const activeRegions = useMemo(() => {
    const used = new Set(feed.events.flatMap((ev) => ev.articles.map((a) => outlets.get(a.outlet_id)?.region)));
    return regions.filter((r) => used.has(r));
  }, [feed.events, outlets, regions]);
  const isJapan = (a: Article) => outlets.get(a.outlet_id)?.side === "japan";
  // 国営・政府系の媒体の記事は、独立した媒体の記事のあとに並べる
  const govRank = (a: Article) => (isGovernment(outlets.get(a.outlet_id)) ? 1 : 0);
  const order = (x: Article, y: Article) =>
    govRank(x) - govRank(y) ||
    (sort === "tone" ? TONE_RANK[x.tone] - TONE_RANK[y.tone] : y.published_at.localeCompare(x.published_at));

  const allEvents = feed.events.map((ev) => {
    const articles = ev.articles.map(withReading);
    const overseas = articles.filter((a) => !isJapan(a)).sort(order);
    const japan = articles.filter(isJapan).sort(order);
    const countries = new Set(overseas.map((a) => outlets.get(a.outlet_id)?.country_code)).size;
    const outletCount = new Set(overseas.map((a) => a.outlet_id)).size;
    return { ev, overseas, japan, countries, outletCount };
  });
  // 「1か国だけが報じた出来事」「日本の主要媒体で報道が見つからない出来事」だけに絞る
  const missingInJapan = (e: (typeof allEvents)[number]) => !!e.ev.japan_main_checked_at && (e.ev.japan_main ?? []).length === 0;
  const events = allEvents.filter((e) => (!onlyOne || e.countries === 1) && (!noJapanMain || missingInJapan(e)));
  const onlyOneCount = allEvents.filter((e) => e.countries === 1).length;
  const noJapanMainCount = allEvents.filter(missingInJapan).length;
  const japanMainChecked = allEvents.some((e) => !!e.ev.japan_main_checked_at);

  return (
    <>
      <div className="controls">
        <div className="group" role="group" aria-label="地域">
          <span className="lbl">海外の地域</span>
          {["all", ...activeRegions].map((r) => (
            <button key={r} id={`region-${r}`} className="chip" aria-pressed={region === r} onClick={() => setRegion(r)}>
              {r === "all" ? "すべて" : REGION_LABEL[r] ?? r}
            </button>
          ))}
        </div>
        <div className="group">
          <span className="lbl">並び</span>
          <div className="seg">
            <button id="sort-tone" aria-pressed={sort === "tone"} onClick={() => setSort("tone")}>論調順</button>
            <button id="sort-time" aria-pressed={sort === "time"} onClick={() => setSort("time")}>新しい順</button>
          </div>
          <button
            id="only-one"
            className="chip"
            aria-pressed={onlyOne}
            onClick={() => setOnlyOne(!onlyOne)}
            title="1か国の媒体だけが報じ、ほかの国は報じていない出来事"
          >
            1か国だけが報じた出来事 {onlyOneCount}
          </button>
          {japanMainChecked && (
            <button
              id="no-japan-main"
              className="chip"
              aria-pressed={noJapanMain}
              onClick={() => setNoJapanMain(!noJapanMain)}
              title="海外では報じられたが、日本の主要媒体（NHK・全国紙・在京キー局）のサイトで報道が見つからなかった出来事"
            >
              日本の主要媒体で報道が見つからない {noJapanMainCount}
            </button>
          )}
          <span className="lbl">見出し</span>
          <div className="seg">
            <button id="lang-en" aria-pressed={lang === "en"} onClick={() => setLang("en")}>原文</button>
            <button id="lang-ja" aria-pressed={lang === "ja"} onClick={() => setLang("ja")}>要約</button>
          </div>
        </div>
      </div>

      <div className="legend">
        <span className="ttl">海外の論調</span>
        <span>出来事ごとの「評価の対象」に対する見方</span>
        {TONES.map((t) => (
          <span key={t.key}>
            <i style={{ background: `var(--${t.key})` }} />
            {t.label}
          </span>
        ))}
        <span>
          <i className="swatch-none" />
          評価なし（手がかりがない）
        </span>
      </div>

      <main className="events">
        {events.length === 0 && (
          <p className="empty">
            {noJapanMain || onlyOne
              ? "条件に合う出来事はありません。"
              : `まだ掲載できる出来事がありません。海外の${MIN_OUTLETS}つ以上の媒体（うち1つ以上は国営・政府系ではない媒体）が報じた出来事を掲載します。`}
          </p>
        )}
        {events.map(({ ev, overseas, japan, countries, outletCount }) => (
          <section className="event" key={ev.id}>
            <div className="ev-head">
              <div className="ev-meta">
                <span className="tag">{ev.category}</span>
                <span>{JST_DATE.format(new Date(ev.updated_at))}</span>
                <span>
                  海外{outletCount}媒体・{countries}か国
                </span>
              </div>
              <h2 className="ev-title">{ev.title_ja}</h2>
              <p className="ev-fact">{ev.fact_ja}</p>
            </div>
            <Coverage overseas={overseas} outlets={outlets} countries={regions} />
            <Summary ev={ev} overseas={overseas} japan={japan} outlets={outlets} />
            <ArticlesPanel eventId={ev.id} overseas={overseas} japan={japan} outlets={outlets} lang={lang} region={region} onRead={onRead} />
          </section>
        ))}
      </main>
    </>
  );
}
