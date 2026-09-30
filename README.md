# Japan Lens

**公開サイト: 
https://japan-lens.makoto-monda.workers.dev
（Cloudflare Workers。main への push で自動デプロイ）

海外メディアが日本をどう報じているかを、出来事ごとに並べて比べるサイト。

- 本文は載せない。見出し・リンク・自前の要約（AI）・記事の論調だけを表示する。
- 媒体の政治的な立場（左右）はサイトに表示しない。媒体選定のバランス確認用の内部データとしてだけ持つ（`collector/outlets.py` の `lean`。`store.json` には書き出さない）。
- 最小版の媒体: NYT、WSJ、BBC、CNA

## 構成

データベースは使わない。収集結果は `web/data/store.json` の1ファイルに持ち、リポジトリにコミットする。
閲覧にログインは不要（静的なページとして配信）。

| 場所 | 内容 |
|---|---|
| `collector/` | Python。RSS を取得 → 日本関連で絞り込み → Claude で出来事のグループ化・要約・論調判定 → `web/data/store.json` を更新。Claude は `claude -p`（Claude Code）をサブスクリプションの認証で呼ぶので API の従量課金はかからない |
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
