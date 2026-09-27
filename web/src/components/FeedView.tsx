"use client";

import { useMemo, useState } from "react";
import { MIN_ARTICLES } from "@/lib/rules";
import type { Article, Feed, Outlet, Tone } from "@/lib/types";

const TONES: { key: Tone; label: string }[] = [
  { key: "crit", label: "批判的" },
  { key: "neu", label: "中立" },
  { key: "fav", label: "好意的" },
];
const TONE_LABEL: Record<Tone, string> = { crit: "批判的", neu: "中立", fav: "好意的" };
const TONE_RANK: Record<Tone, number> = { crit: 0, neu: 1, fav: 2 };
const REGION_LABEL: Record<string, string> = { US: "米国", GB: "英国", DE: "ドイツ", SG: "シンガポール" };

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

function ToneBar({ articles }: { articles: Article[] }) {
  const total = articles.length || 1;
  const counts = TONES.map((t) => ({ ...t, n: articles.filter((a) => a.tone === t.key).length }));
  return (
    <div className="dist" aria-label="記事の論調の分布">
      <div className="dist-ttl">記事の論調</div>
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

function ArticleCard({ article, outlet, lang }: { article: Article; outlet?: Outlet; lang: Lang }) {
  const external = article.url.startsWith("http");
  return (
    <article className="card">
      <div className="band" style={{ background: `var(--${article.tone})` }} />
      <div className="card-body">
        <div className="outlet">
          <span className="flag" aria-hidden="true">{outlet?.flag}</span>
          <span className="cc">{outlet?.country_code}</span>
          <b>{outlet?.name ?? article.outlet_id}</b>
          {outlet && <span className="own-tag">{outlet.ownership}</span>}
        </div>
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
        <div className="card-foot">
          <span className={`tone ${article.tone}`}>{TONE_LABEL[article.tone]}</span>
          <time className="time" dateTime={article.published_at}>{formatTime(article.published_at)}</time>
          {external ? (
            <a href={article.url} target="_blank" rel="noopener noreferrer">記事へ ↗</a>
          ) : (
            <span className="time">サンプル</span>
          )}
        </div>
      </div>
    </article>
  );
}

export default function FeedView({ feed }: { feed: Feed }) {
  const [region, setRegion] = useState("all");
  const [sort, setSort] = useState<Sort>("tone");
  const [lang, setLang] = useState<Lang>("en");

  const outlets = useMemo(() => new Map(feed.outlets.map((o) => [o.id, o])), [feed.outlets]);
  const regions = useMemo(() => [...new Set(feed.outlets.map((o) => o.region))], [feed.outlets]);

  const events = feed.events.map((ev) => {
    const list = ev.articles
      .filter((a) => region === "all" || outlets.get(a.outlet_id)?.region === region)
      .sort((x, y) =>
        sort === "tone" ? TONE_RANK[x.tone] - TONE_RANK[y.tone] : y.published_at.localeCompare(x.published_at),
      );
    const countries = new Set(ev.articles.map((a) => outlets.get(a.outlet_id)?.country_code)).size;
    const outletCount = new Set(ev.articles.map((a) => a.outlet_id)).size;
    return { ev, list, countries, outletCount };
  });

  return (
    <>
      <div className="controls">
        <div className="group" role="group" aria-label="地域">
          <span className="lbl">地域</span>
          {["all", ...regions].map((r) => (
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
          <span className="lbl">見出し</span>
          <div className="seg">
            <button id="lang-en" aria-pressed={lang === "en"} onClick={() => setLang("en")}>原文</button>
            <button id="lang-ja" aria-pressed={lang === "ja"} onClick={() => setLang("ja")}>要約</button>
          </div>
        </div>
      </div>

      <div className="legend">
        <span className="ttl">記事の論調</span>
        <span>日本政府・日本側への評価</span>
        {TONES.map((t) => (
          <span key={t.key}>
            <i style={{ background: `var(--${t.key})` }} />
            {t.label}
          </span>
        ))}
      </div>

      <main className="events">
        {events.length === 0 && (
          <p className="empty">
            まだ掲載できる出来事がありません。複数の媒体から合計{MIN_ARTICLES}件以上の報道が集まった出来事を掲載します。
          </p>
        )}
        {events.map(({ ev, list, countries, outletCount }) => (
          <section className="event" key={ev.id}>
            <div className="ev-head">
              <div className="ev-meta">
                <span className="tag">{ev.category}</span>
                <span>{JST_DATE.format(new Date(ev.updated_at))}</span>
                <span>
                  {outletCount}媒体・{countries}か国
                </span>
              </div>
              <h2 className="ev-title">{ev.title_ja}</h2>
              <p className="ev-fact">{ev.fact_ja}</p>
              <ToneBar articles={list} />
            </div>
            {list.length ? (
              <div className="cards">
                {list.map((a) => (
                  <ArticleCard key={a.id} article={a} outlet={outlets.get(a.outlet_id)} lang={lang} />
                ))}
              </div>
            ) : (
              <p className="empty">この地域の媒体はこの出来事を報じていません。</p>
            )}
          </section>
        ))}
      </main>
    </>
  );
}
