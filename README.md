# Japan Lens

**公開サイト: 
https://japan-lens.mon-m.workers.dev
（Cloudflare Workers。main への push で自動デプロイ）

海外メディアが日本をどう報じているかを、出来事ごとに並べて比べるサイト。

- 本文は載せない。見出し・リンク・自前の要約（AI）・記事の論調だけを表示する。
- 媒体の政治的な立場（左右）はサイトに表示しない。媒体選定のバランス確認用の内部データとしてだけ持つ（`collector/outlets.py` の `lean`。`store.json` には書き出さない）。
- 国営・政府系の媒体（`ownership` が「国営」「政府系」）は、その国の政府の見方として載せるが、「海外の見方」の論調の集計には含めず別に示す。掲載条件でも同じ国の国営・政府系の媒体はまとめて1つと数え、国営・政府系ではない媒体が1つ以上報じた出来事だけを載せる（`collector/main.py` の `eligible` と `web/src/lib/rules.ts` の `isEligible`）。
- 出来事ごとに、日本の主要媒体（NHK・全国紙5紙・在京キー局4局）が報じたかを Google News の検索で確かめ、見つかった記事の見出しとリンクを表示する（`check_japan_coverage`）。「見つからない」出来事だけに絞り込める。
- 設立の背景は `/about`（このサイトについて）にまとめている。
- `/world`（世界の主要ニュース）: 日本以外の出来事を各国の媒体がどう報じたかを並べ、日本の主要媒体の見出しとも比べる。日本の報道は世界の出来事の伝え方にも偏りがありうるため。情報が増えすぎないよう、載せる出来事は AI の判断ではなく数で決める（`collector/world.py`）: 国営・政府系ではない媒体が3か国以上で報じ、2つ以上の地域圏（米州・欧州・中東とアフリカ・アジア・オセアニア）にまたがる出来事を、報じた国の多い順に1日5件まで、直近7日分。スポーツ・芸能と、日本が主な対象の出来事は除く。論調は判定せず、国ごとの切り口を比べる。媒体は日本の出来事と同じ媒体の世界・国際面に、中東・アフリカ・中南米・ロシアなどの媒体（`WORLD_ONLY_OUTLETS`）を加えている。収集結果は `web/data/world.json`（公開分）と `collector/state/world.json`（内部用）。
- 記事カードの「AIで本文を読む」: 押したとき（と「記事へ」で記事を開いたとき）は、Worker（`web/worker/index.ts`）がその記事を予約として KV に記録するだけで、AI は呼ばない。翌朝の収集（`collector/reader.py`）が予約された記事をまとめて取得し、`claude -p`（サブスクリプション）で要約・論調を判定して `web/data/readings.json` に書く。サイトを作り直すと結果が表示され、記事の論調の表示も本文での判定に置き換わる。人に頼まれて読む記事なので、媒体の robots.txt が `Claude-User` を拒否していれば読まない。予約できるのはサイトに載っている記事（`/read-index.json`）だけで、1つの IP から1分10件まで、予約は3日で消える。API の従量課金は使わない。

## 構成

データベースは使わない。収集結果は `web/data/store.json` の1ファイルに持ち、リポジトリにコミットする。
閲覧にログインは不要（静的なページとして配信）。

| 場所 | 内容 |
|---|---|
| `collector/` | Python。RSS（RSS に日本の記事が少ない媒体は Google News のサイト内検索）を取得 → 日本関連で絞り込み → Claude で出来事のグループ化・要約・論調判定 → 日本の主要媒体の報道を確認 → `web/data/store.json` を更新。Claude は `claude -p`（Claude Code）をサブスクリプションの認証で呼ぶので API の従量課金はかからない |
| `web/worker/` | Cloudflare Worker。`/api/read`（AIで本文を読むの予約）と `/api/read-queue`（予約の一覧）だけを処理し、それ以外は静的なページを返す |
| `web/` | Next.js。ビルド時に `data/store.json` を取り込み、出来事ごとに各媒体のカードを並べた静的ページを作る（`data/readings.json` の読んだ結果も取り込む） |
| `.github/workflows/collect.yml` | 1日1回（日本時間の朝6時）、収集処理を実行して `store.json` をコミット・push する |

更新の流れ: GitHub Actions（1日1回）→ `store.json` をコミット → ホスティングが push を検知して再ビルド → サイト更新

## ローカルで動かす

```sh
cd collector
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 事前に claude コマンドにログインしておく
.venv/bin/python main.py          # 収集 + AI 処理
.venv/bin/python main.py --no-ai  # 収集だけ
.venv/bin/python world.py         # 世界の主要ニュースだけ（main.py の最後でも実行される。--no-world で外せる）
.venv/bin/python backfill.py --days 14  # 過去の記事をさかのぼって取り込む（Google News の検索 RSS。初回だけ）

cd ../web
npm install
npm run dev   # http://localhost:3000
```

表示できる出来事がまだない間は、架空のサンプルを表示する。

## 公開の手順

1. GitHub にリポジトリを作って push
2. 手元で `claude setup-token` を実行して出たトークンを、Secrets の `CLAUDE_CODE_OAUTH_TOKEN` に登録（Settings → Secrets and variables → Actions）
3. Cloudflare の Workers & Pages で GitHub のリポジトリを連携し、Worker を作る（無料の静的アセット配信）。ビルド設定は Root directory `web`、Build command `npm run build`、Deploy command `npx wrangler deploy`（配信するフォルダは `web/wrangler.jsonc` で `out/` を指定済み）。main への push で自動デプロイ
4. Actions の collect を手動実行して、`store.json` のコミットとサイトの更新を確認

## 公開前に確認すること

- 各社の RSS 利用規約（公開サイト・商用での利用可否、見出しの表示条件）
- 媒体の立場データ（`lean`）の根拠となる外部評価機関の格付け
