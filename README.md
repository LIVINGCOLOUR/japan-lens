# Japan Lens

**公開サイト: 
https://japan-lens.makoto-monda.workers.dev
（Cloudflare Workers。main への push で自動デプロイ）

海外メディアが日本をどう報じているかを、出来事ごとに並べて比べるサイト。

- 本文は載せない。見出し・リンク・自前の要約（AI）・記事の論調だけを表示する。
- 媒体の政治的な立場（左右）はサイトに表示しない。媒体選定のバランス確認用の内部データとしてだけ持つ（`collector/outlets.py` の `lean`。`store.json` には書き出さない）。
- 国営・政府系の媒体（`ownership` が「国営」「政府系」）は、その国の政府の見方として載せるが、「海外の見方」の論調の集計には含めず別に示す。掲載条件でも同じ国の国営・政府系の媒体はまとめて1つと数え、国営・政府系ではない媒体が1つ以上報じた出来事だけを載せる（`collector/main.py` の `eligible` と `web/src/lib/rules.ts` の `isEligible`）。
- 出来事ごとに、日本の主要媒体（NHK・全国紙5紙・在京キー局4局）が報じたかを Google News の検索で確かめ、見つかった記事の見出しとリンクを表示する（`check_japan_coverage`）。「見つからない」出来事だけに絞り込める。
- 設立の背景は `/about`（このサイトについて）にまとめている。
- 記事カードの「AIで本文を読む」: 押したときだけ Worker（`web/worker/index.ts`）がその1記事を取得し、Claude API（Haiku 4.5）で要約・論調を判定する。媒体の robots.txt が `Claude-User`（人に頼まれて AI が読む場合）を拒否していれば読まない。読めるのはサイトに載っている記事（`/read-index.json`）だけ。結果は KV に30日保存し、まだ読んでいない記事の読み込みは1つの IP から1分10件まで。API キーは `cd web && npx wrangler secret put ANTHROPIC_API_KEY` で登録する（未登録の間は「準備中」と表示）。

## 構成

データベースは使わない。収集結果は `web/data/store.json` の1ファイルに持ち、リポジトリにコミットする。
閲覧にログインは不要（静的なページとして配信）。

| 場所 | 内容 |
|---|---|
| `collector/` | Python。RSS（RSS に日本の記事が少ない媒体は Google News のサイト内検索）を取得 → 日本関連で絞り込み → Claude で出来事のグループ化・要約・論調判定 → 日本の主要媒体の報道を確認 → `web/data/store.json` を更新。Claude は `claude -p`（Claude Code）をサブスクリプションの認証で呼ぶので API の従量課金はかからない |
| `web/worker/` | Cloudflare Worker。`/api/read`（AIで本文を読む）だけを処理し、それ以外は静的なページを返す |
| `web/` | Next.js。ビルド時に `data/store.json` を取り込み、出来事ごとに各媒体のカードを並べた静的ページを作る |
| `.github/workflows/collect.yml` | 1日1回（日本時間の朝6時）、収集処理を実行して `store.json` をコミット・push する |

更新の流れ: GitHub Actions（1日1回）→ `store.json` をコミット → ホスティングが push を検知して再ビルド → サイト更新

## ローカルで動かす

```sh
cd collector
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 事前に claude コマンドにログインしておく
.venv/bin/python main.py          # 収集 + AI 処理
.venv/bin/python main.py --no-ai  # 収集だけ
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
