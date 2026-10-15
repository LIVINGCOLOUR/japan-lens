// 世界の主要ニュース。収集処理（collector/world.py）が web/data/world.json に書き出したものをビルド時に取り込む。
// どの出来事を載せるか（主要なニュースの条件）は collector/world.py が決める。ここでは並べるだけ
import world from "../../data/world.json";
import type { Outlet } from "./types";

export type WorldArticle = {
  id: string;
  story_id: string;
  outlet_id: string;
  url: string;
  title: string;
  published_at: string;
  summary_ja: string | null;
  angle: string | null;
};

export type WorldStory = {
  id: string;
  day: string; // 最初に報じられた日（日本時間）
  title_ja: string;
  fact_ja: string;
  category: string;
  first_seen: string;
  updated_at: string;
  country_views: { country: string; view_ja: string }[] | null;
  difference_ja: string | null;
  japan_main: { outlet: string; title: string; url: string; published_at: string }[] | null;
  japan_view_ja: string | null;
  japan_main_checked_at: string | null;
  // 出来事が起きた国・主な当事者の国。各社の国際面から集めているので、この国の媒体は国内面で報じていても拾えないことがある
  place_countries: string[] | null;
  n_outlets: number;
  n_countries: number;
  n_independent_countries: number;
  n_areas: number;
  articles: WorldArticle[];
};

export type WorldRules = { min_countries: number; min_areas: number; per_day: number; days: number; per_outlet: number };

export type WorldFeed = {
  generated_at: string | null;
  rules: WorldRules;
  areas: Record<string, string>;
  outlets: Outlet[];
  stories: WorldStory[];
};

type Stored = Omit<WorldFeed, "stories"> & { stories: Omit<WorldStory, "articles">[]; articles: WorldArticle[] };

export function getWorld(): WorldFeed {
  const data = world as unknown as Stored;
  const stories = data.stories.map((s) => ({ ...s, articles: data.articles.filter((a) => a.story_id === s.id) }));
  return { generated_at: data.generated_at, rules: data.rules, areas: data.areas, outlets: data.outlets, stories };
}
