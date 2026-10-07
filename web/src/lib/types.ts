// none = 評価の対象がない、または見出し・リード文に評価の手がかりがない
export type Tone = "crit" | "neu" | "fav" | "none";

// 公開用の媒体情報。左右の立場はここに含めない（サイトでは表示しない方針）。
export type Outlet = {
  id: string;
  name: string;
  country_code: string;
  flag: string;
  region: string;
  ownership: string;
  homepage: string;
  side?: "overseas" | "japan"; // japan = 日本の立場を示す媒体（論調の分布や掲載条件には数えない）
};

export type Article = {
  id: string;
  outlet_id: string;
  url: string;
  title: string;
  published_at: string;
  summary_ja: string;
  tone: Tone;
  angle?: string; // 切り口（記事が何に焦点を当てているか）
  evidence?: string; // 論調の根拠にした原文の語句
  kind?: "news" | "opinion";
  basis?: "body" | "headline"; // 論調判定の材料。本文を読める媒体だけ body
};

export type NewsEvent = {
  id: string;
  title_ja: string;
  fact_ja: string;
  category: string;
  target?: string; // 論調を測る「評価の対象」。空なら論調を出さない
  japan_position_ja?: string; // 日本の立場のまとめ
  japan_basis?: "japanese_media" | "overseas_reports" | "none";
  japan_views?: { outlet: string; view_ja: string }[]; // 日本の媒体ごとの伝え方
  japan_split?: boolean; // 日本の媒体どうしで見方が食い違っているか
  overseas_view_ja?: string; // 海外の見方のまとめ
  japan_main?: { outlet: string; title: string; url: string; published_at: string }[]; // 日本の主要媒体で見つかった記事
  japan_main_checked_at?: string; // 日本の主要媒体の報道を確かめた日時。なければ未確認
  first_seen: string;
  updated_at: string;
  articles: Article[];
};

export type Feed = {
  outlets: Outlet[];
  events: NewsEvent[];
  source: "live" | "sample";
};
