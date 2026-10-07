// 掲載の条件: 2つ以上の媒体が報じている出来事だけを出す（記事の件数は問わない）。
// 比べる相手がいないと各社の報じ方を並べられないため
export const MIN_OUTLETS = 2;

// 掲載するカテゴリー。日本が政治的・経済的にどう見られているかに関わるものだけにする
// （スポーツ・災害・文化・市況などは「その他」として載せない）。collector/main.py の SHOWN_CATEGORIES と同じにする
export const SHOWN_CATEGORIES = [
  "政治",
  "外交",
  "安全保障",
  "経済政策",
  "企業・産業",
  "社会政策",
  "エネルギー・資源",
  "科学技術政策",
  "歴史認識",
];

// 国や政府が運営・出資する媒体。政府の見方を伝える材料として載せるが、「海外の見方」の論調の集計からは外し、
// 掲載条件では同じ国の政府系の媒体をまとめて1つと数える。collector/outlets.py の GOVERNMENT_OWNERSHIP と同じにする
export const GOVERNMENT_OWNERSHIP = ["国営", "政府系"];

export function isGovernment(outlet?: { ownership: string }) {
  return !!outlet && GOVERNMENT_OWNERSHIP.includes(outlet.ownership);
}

/**
 * 掲載条件: 海外の媒体が MIN_OUTLETS 以上の「声」で報じ、うち1つ以上が独立した媒体であること。
 * 同じ国の政府系の媒体はまとめて1つの声と数える（国営メディア2社だけで条件を満たさないように）。
 * collector/main.py の eligible と同じにする
 */
export function isEligible(overseasOutlets: { ownership: string; country_code: string }[]) {
  const independent = overseasOutlets.filter((o) => !isGovernment(o)).length;
  const govCountries = new Set(overseasOutlets.filter(isGovernment).map((o) => o.country_code)).size;
  return independent > 0 && independent + govCountries >= MIN_OUTLETS;
}

// 出来事ごとに報道を確かめる日本の主要媒体（NHK・全国紙5紙・在京キー局4局）の数。collector/outlets.py の JAPAN_MAIN_OUTLETS と同じにする
export const JAPAN_MAIN_COUNT = 10;
