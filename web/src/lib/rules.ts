// 掲載の条件: 合計3件以上の記事があり、かつ2つ以上の媒体が報じている出来事だけを出す
export const MIN_ARTICLES = 3;
export const MIN_OUTLETS = 2;

// 掲載するカテゴリー。日本が政治的・経済的にどう見られているかに関わるものだけにする
// （スポーツ・災害・文化などは載せない）。collector/main.py の SHOWN_CATEGORIES と同じにする
export const SHOWN_CATEGORIES = ["政治", "外交", "安全保障", "経済"];
