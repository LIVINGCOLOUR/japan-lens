import sample from "@/data/sample.json";
// 収集処理（collector/）が更新し、GitHub Actions がコミットするファイル。ビルド時に取り込む。
import store from "../../data/store.json";
import { MIN_ARTICLES, MIN_OUTLETS, SHOWN_CATEGORIES } from "./rules";
import type { Article, Feed, NewsEvent, Outlet } from "./types";

const EVENT_LIMIT = 30;

type StoredArticle = Article & { event_id: string | null; processed_at: string | null; relevant: boolean | null };
type Store = { outlets: Outlet[]; events: Omit<NewsEvent, "articles">[]; articles: StoredArticle[] };

function toFeed(outlets: Outlet[], events: NewsEvent[], source: Feed["source"]): Feed {
  const shown = events
    .filter((e) => SHOWN_CATEGORIES.includes(e.category))
    .filter((e) => e.articles.length >= MIN_ARTICLES && new Set(e.articles.map((a) => a.outlet_id)).size >= MIN_OUTLETS)
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, EVENT_LIMIT);
  return { outlets, events: shown, source };
}

export function getFeed(): Feed {
  const data = store as Store;
  const events = data.events.map((e) => ({
    ...e,
    articles: data.articles.filter((a) => a.event_id === e.id && a.processed_at && a.relevant),
  }));
  // 収集データがまだ1件もない間だけ架空のサンプルを出す。
  // データはあるが条件を満たす出来事がない場合は、空の状態をそのまま見せる
  if (data.events.length === 0) {
    return { outlets: sample.outlets, events: sample.events as NewsEvent[], source: "sample" };
  }
  return toFeed(data.outlets, events, "live");
}
