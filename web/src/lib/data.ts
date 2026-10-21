import sample from "@/data/sample.json";
// 収集処理（collector/）が更新し、GitHub Actions がコミットするファイル。ビルド時に取り込む。
import store from "../../data/store.json";
// 読者が「AIで本文を読む」で予約した記事を、毎朝の収集で AI が読んだ結果（collector/reader.py）
import readings from "../../data/readings.json";
import { isEligible, SHOWN_CATEGORIES } from "./rules";
import type { Article, Feed, NewsEvent, Outlet, ReaderReading } from "./types";

const EVENT_LIMIT = 30;

type StoredArticle = Article & { event_id: string | null; processed_at: string | null; relevant: boolean | null };
type Store = { outlets: Outlet[]; events: Omit<NewsEvent, "articles">[]; articles: StoredArticle[] };

function toFeed(outlets: Outlet[], events: NewsEvent[], source: Feed["source"]): Feed {
  const byId = new Map(outlets.map((o) => [o.id, o]));
  const overseasOutlets = (e: NewsEvent) =>
    [...new Set(e.articles.map((a) => a.outlet_id))].map((id) => byId.get(id)).filter((o): o is Outlet => !!o && o.side !== "japan");
  const shown = events
    // 掲載するカテゴリーで、かつ「評価の対象」（日本の判断や行動）がある出来事だけ
    .filter((e) => SHOWN_CATEGORIES.includes(e.category) && !!e.target)
    // 掲載条件は海外の媒体で数える（日本側の媒体は「日本の立場」の材料で、比較の対象ではない）
    .filter((e) => isEligible(overseasOutlets(e)))
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, EVENT_LIMIT);
  return { outlets, events: shown, source };
}

/** 本文を読めた記事は、論調・切り口・根拠を本文での判定に置き換える */
function withReading(a: StoredArticle): StoredArticle {
  const r = (readings as unknown as Record<string, ReaderReading>)[a.id];
  if (!r) return a;
  if (r.status !== "ok") return { ...a, reader_reading: r };
  return {
    ...a,
    tone: r.tone,
    angle: r.angle || a.angle,
    evidence: r.evidence,
    basis: "body",
    read_by_reader: true,
    reader_reading: r,
  };
}

export function getFeed(): Feed {
  // JSON の中身は処理の途中で null を含むことがあるので、unknown を経由して型を当てる
  const data = store as unknown as Store;
  const events = data.events.map((e) => ({
    ...e,
    articles: data.articles.filter((a) => a.event_id === e.id && a.processed_at && a.relevant).map(withReading),
  }));
  // 収集データがまだ1件もない間だけ架空のサンプルを出す。
  // データはあるが条件を満たす出来事がない場合は、空の状態をそのまま見せる
  if (data.events.length === 0) {
    return { outlets: sample.outlets, events: sample.events as NewsEvent[], source: "sample" };
  }
  return toFeed(data.outlets, events, "live");
}
