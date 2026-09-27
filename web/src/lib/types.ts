export type Tone = "crit" | "neu" | "fav";

// 公開用の媒体情報。左右の立場はここに含めない（サイトでは表示しない方針）。
export type Outlet = {
  id: string;
  name: string;
  country_code: string;
  flag: string;
  region: string;
  ownership: string;
  homepage: string;
};

export type Article = {
  id: string;
  outlet_id: string;
  url: string;
  title: string;
  published_at: string;
  summary_ja: string;
  tone: Tone;
};

export type NewsEvent = {
  id: string;
  title_ja: string;
  fact_ja: string;
  category: string;
  first_seen: string;
  updated_at: string;
  articles: Article[];
};

export type Feed = {
  outlets: Outlet[];
  events: NewsEvent[];
  source: "live" | "sample";
};
