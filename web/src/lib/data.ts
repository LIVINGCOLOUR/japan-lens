import sample from "@/data/sample.json";
// 収集処理（collector/）が更新し、GitHub Actions がコミットするファイル。ビルド時に取り込む。
import store from "../../data/store.json";
import type { Article, Feed, NewsEvent, Outlet } from "./types";

const EVENT_LIMIT = 30;

type StoredArticle = Article & { event_id: string | null; processed_at: string | null; relevant: boolean | null };
type Store = { outlets: Outlet[]; events: Omit<NewsEvent, "articles">[]; articles: StoredArticle[] };

function toFeed(outlets: Outlet[], events: NewsEvent[], source: Feed["source"]): Feed {
  const shown = events
    .filter((e) => e.articles.length > 0)
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
  const feed = toFeed(data.outlets, events, "live");
  // 表示できる出来事がまだない間は架空のサンプルを出す
  return feed.events.length ? feed : toFeed(sample.outlets, sample.events as NewsEvent[], "sample");
}
