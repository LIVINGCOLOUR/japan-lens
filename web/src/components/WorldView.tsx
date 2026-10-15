"use client";

import { useMemo, useState } from "react";
import { REGION_LABEL } from "@/lib/regions";
import { isGovernment, JAPAN_MAIN_COUNT } from "@/lib/rules";
import type { Outlet } from "@/lib/types";
import type { WorldArticle, WorldFeed, WorldStory } from "@/lib/world";

type Lang = "en" | "ja";

const JST = new Intl.DateTimeFormat("ja-JP", {
  timeZone: "Asia/Tokyo",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});
const DAY = new Intl.DateTimeFormat("ja-JP", { month: "long", day: "numeric", weekday: "short", timeZone: "UTC" });

function dayLabel(day: string) {
  return DAY.format(new Date(`${day}T00:00:00Z`));
}

/** どの国の媒体が報じ、どの国が報じていないか */
function Coverage({ story, outlets, countries }: { story: WorldStory; outlets: Map<string, Outlet>; countries: string[] }) {
  const byCountry = new Map<string, Outlet[]>();
  for (const a of story.articles) {
    const o = outlets.get(a.outlet_id);
    if (!o) continue;
    const list = byCountry.get(o.country_code) ?? [];
    if (!list.includes(o)) list.push(o);
    byCountry.set(o.country_code, list);
  }
  const reported = countries.filter((c) => byCountry.has(c));
  // 出来事が起きた国は「報道なし」に含めない（各社の国際面から集めているため、その国の国内の報道は拾えない）
  const place = new Set(story.place_countries ?? []);
  const silent = countries.filter((c) => !byCountry.has(c) && !place.has(c));
  return (
    <div className="coverage">
      <div className="coverage-row">
        <span className="coverage-lbl">報じた国</span>
        {reported.map((c) => {
          const list = byCountry.get(c)!;
          const govOnly = list.every((o) => isGovernment(o));
          const names = list.map((o) => o.name).join("・");
          return govOnly ? (
            <span key={c} className="cov-chip on gov" title={`${names}（国営・政府系）`}>
              {REGION_LABEL[c] ?? c}（政府系のみ）
            </span>
          ) : (
            <span key={c} className="cov-chip on none" title={names}>
              {REGION_LABEL[c] ?? c}
            </span>
          );
        })}
      </div>
      {silent.length > 0 && (
        <div className="coverage-row">
          <span className="coverage-lbl">報道なし</span>
          {silent.map((c) => (
            <span key={c} className="cov-chip off">
              {REGION_LABEL[c] ?? c}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function CountryViews({ story, flags }: { story: WorldStory; flags: Map<string, string> }) {
  const views = story.country_views ?? [];
  return (
    <section className="stance overseas" aria-label="各国の伝え方">
      <h3>各国の伝え方</h3>
      {views.length > 0 ? (
        <ul className="country-views">
          {views.map((v) => (
            <li key={v.country}>
              <b>
                <span className="flag" aria-hidden="true">{flags.get(v.country)}</span>
                {REGION_LABEL[v.country] ?? v.country}
              </b>
              {v.view_ja}
            </li>
          ))}
        </ul>
      ) : (
        <p className="stance-empty">まとめを作成中です。</p>
      )}
    </section>
  );
}

/** 日本の主要媒体（NHK・全国紙・在京キー局）がこの出来事をどう報じたか。見出しを並べて世界の伝え方と比べられるようにする */
function JapanMain({ story }: { story: WorldStory }) {
  if (!story.japan_main_checked_at) {
    return <p className="stance-empty">日本の主要媒体の報道はまだ確かめていません。</p>;
  }
  const found = story.japan_main ?? [];
  if (found.length === 0) {
    return (
      <div className="jp-main none">
        <p className="jp-main-ttl">日本の主要媒体では、この出来事の報道が見つかりませんでした</p>
        <p className="jp-main-note">NHK・全国紙5紙・在京の民放4局のサイトを検索した結果です。報じていないと断定するものではありません。</p>
      </div>
    );
  }
  // 媒体ごとに1件（いちばん新しい見出し）
  const first = new Map<string, (typeof found)[number]>();
  for (const f of [...found].sort((x, y) => y.published_at.localeCompare(x.published_at))) {
    if (!first.has(f.outlet)) first.set(f.outlet, f);
  }
  return (
    <>
      {story.japan_view_ja && <p>{story.japan_view_ja}</p>}
      <div className="jp-links">
        <p className="jp-links-ttl">
          見つかった見出し（{JAPAN_MAIN_COUNT}媒体中{first.size}媒体）
        </p>
        <ul>
          {[...first.values()].map((f) => (
            <li key={f.url}>
              <span className="jp-links-outlet">{f.outlet}</span>
              <a href={f.url} target="_blank" rel="noopener noreferrer">
                {f.title} ↗
              </a>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}

function ArticleCard({ article, outlet, lang }: { article: WorldArticle; outlet?: Outlet; lang: Lang }) {
  const summary = article.summary_ja ?? "";
  return (
    <article className="card">
      <div className="card-body">
        <div className="outlet">
          <span className="flag" aria-hidden="true">{outlet?.flag}</span>
          <span className="cc">{outlet?.country_code}</span>
          <b>{outlet?.name ?? article.outlet_id}</b>
          {outlet && <span className={isGovernment(outlet) ? "own-tag gov" : "own-tag"}>{outlet.ownership}</span>}
        </div>
        {article.angle && <p className="angle">切り口：{article.angle}</p>}
        {lang === "ja" && summary ? (
          <>
            <p className="headline">{summary}</p>
            <p className="summary">{article.title}</p>
          </>
        ) : (
          <>
            <p className="headline">{article.title}</p>
            {summary && <p className="summary">{summary}</p>}
          </>
        )}
        <div className="card-foot">
          <time className="time" dateTime={article.published_at}>{JST.format(new Date(article.published_at))}</time>
          <a href={article.url} target="_blank" rel="noopener noreferrer">
            記事へ ↗
          </a>
        </div>
      </div>
    </article>
  );
}

function Articles({ story, outlets, lang }: { story: WorldStory; outlets: Map<string, Outlet>; lang: Lang }) {
  const [open, setOpen] = useState(false);
  const panelId = `world-articles-${story.id}`;
  // 国営・政府系の媒体の記事は、独立した媒体の記事のあとに並べる
  const sorted = [...story.articles].sort(
    (x, y) =>
      Number(isGovernment(outlets.get(x.outlet_id))) - Number(isGovernment(outlets.get(y.outlet_id))) ||
      y.published_at.localeCompare(x.published_at),
  );
  return (
    <div className="articles">
      <button className="articles-toggle" aria-expanded={open} aria-controls={panelId} onClick={() => setOpen(!open)}>
        {open ? "各社の記事を閉じる" : "各社の記事を見る"}
        <span className="articles-count">{story.articles.length}件</span>
      </button>
      {open && (
        <div id={panelId} className="cards">
          {sorted.map((a) => (
            <ArticleCard key={a.id} article={a} outlet={outlets.get(a.outlet_id)} lang={lang} />
          ))}
        </div>
      )}
    </div>
  );
}

function Story({
  story,
  outlets,
  flags,
  countries,
  lang,
}: {
  story: WorldStory;
  outlets: Map<string, Outlet>;
  flags: Map<string, string>;
  countries: string[];
  lang: Lang;
}) {
  return (
    <section className="event">
      <div className="ev-head">
        <div className="ev-meta">
          <span className="tag">{story.category}</span>
          <span>
            {story.n_countries}か国・{story.n_outlets}媒体
          </span>
        </div>
        <h3 className="ev-title">{story.title_ja}</h3>
        {story.fact_ja && <p className="ev-fact">{story.fact_ja}</p>}
      </div>
      <Coverage story={story} outlets={outlets} countries={countries} />
      <div className="summary-grid">
        <CountryViews story={story} flags={flags} />
        <div className="world-side">
          {story.difference_ja && (
            <section className="stance" aria-label="伝え方の違い">
              <h3>伝え方の違い</h3>
              <p>{story.difference_ja}</p>
            </section>
          )}
          <section className="stance japan" aria-label="日本の主要媒体では">
            <h3>日本の主要媒体では</h3>
            <JapanMain story={story} />
          </section>
        </div>
      </div>
      <Articles story={story} outlets={outlets} lang={lang} />
    </section>
  );
}

export default function WorldView({ feed }: { feed: WorldFeed }) {
  const [category, setCategory] = useState("all");
  const [lang, setLang] = useState<Lang>("ja");
  const outlets = useMemo(() => new Map(feed.outlets.map((o) => [o.id, o])), [feed.outlets]);
  const flags = useMemo(() => new Map(feed.outlets.map((o) => [o.country_code, o.flag])), [feed.outlets]);
  // 対象にしている国（「報道なし」の表示に使う）。地域圏ごとにまとめて並べる
  const countries = useMemo(() => {
    const order = ["米州", "欧州", "中東・アフリカ", "アジア", "オセアニア"];
    const cs = [...new Set(feed.outlets.map((o) => o.country_code))];
    return cs.sort((a, b) => order.indexOf(feed.areas[a] ?? "") - order.indexOf(feed.areas[b] ?? ""));
  }, [feed.outlets, feed.areas]);
  const categories = [...new Set(feed.stories.map((s) => s.category))];
  const stories = feed.stories.filter((s) => category === "all" || s.category === category);
  const days = [...new Set(stories.map((s) => s.day))];
  const { rules } = feed;

  return (
    <>
      <div className="world-intro">
        <p>
          日本の報道は、世界の出来事の伝え方にも偏りがありえます。ここでは日本以外の出来事を、各国の媒体がどう伝えたかを並べ、日本の主要媒体の見出しとも比べます。
        </p>
        <p className="world-rule">
          <b>載せる出来事の選び方</b>：国営・政府系ではない媒体が<b>{rules.min_countries}か国以上</b>で報じ、
          <b>{rules.min_areas}つ以上の地域圏</b>（米州・欧州・中東とアフリカ・アジア・オセアニア）にまたがった出来事だけを、
          報じた国の多い順に<b>1日{rules.per_day}件まで</b>、直近{rules.days}日分載せています。スポーツ・芸能と、日本が主な対象の出来事（「日本はどう報じられたか」で扱います）は除いています。
        </p>
      </div>

      <div className="controls">
        <div className="group" role="group" aria-label="分野">
          <span className="lbl">分野</span>
          {["all", ...categories].map((c) => (
            <button key={c} className="chip" aria-pressed={category === c} onClick={() => setCategory(c)}>
              {c === "all" ? "すべて" : c}
            </button>
          ))}
        </div>
        <div className="group">
          <span className="lbl">見出し</span>
          <div className="seg">
            <button aria-pressed={lang === "ja"} onClick={() => setLang("ja")}>要約</button>
            <button aria-pressed={lang === "en"} onClick={() => setLang("en")}>原文</button>
          </div>
        </div>
      </div>

      <main className="events">
        {stories.length === 0 && (
          <p className="empty">
            まだ掲載できる出来事がありません。{rules.min_countries}か国以上・{rules.min_areas}つ以上の地域圏の媒体が報じた出来事を掲載します。
          </p>
        )}
        {days.map((day) => (
          <div key={day} className="world-day">
            <h2 className="world-day-ttl">{dayLabel(day)}</h2>
            {stories
              .filter((s) => s.day === day)
              .map((s) => (
                <Story key={s.id} story={s} outlets={outlets} flags={flags} countries={countries} lang={lang} />
              ))}
          </div>
        ))}
      </main>
    </>
  );
}
