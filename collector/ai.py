"""Claude で記事を出来事ごとにまとめ、要約と論調を付ける。

API の従量課金は使わず、Claude Code の CLI（`claude -p`）をサブスクリプションの認証で呼ぶ。
- ローカル: `claude` にログイン済みならそのまま動く
- GitHub Actions: `claude setup-token` で作ったトークンを CLAUDE_CODE_OAUTH_TOKEN に入れる

1回の呼び出しで、未処理の記事のまとまりと直近の出来事の一覧を渡し、
記事ごとに「どの出来事か（既存 / 新規）」「日本語の要約」「論調」を返してもらう。
"""

import json
import os
import shutil
import subprocess
import tempfile

# 未設定ならサブスクリプションの既定モデル。例: CLAUDE_MODEL=sonnet
MODEL = os.environ.get("CLAUDE_MODEL")
TIMEOUT_SECONDS = 600
CATEGORIES = ["外交", "安全保障", "政治", "経済", "社会", "文化", "スポーツ", "災害", "科学技術", "その他"]

SYSTEM = """あなたは海外メディアの日本報道を比較するニュースサイトの編集者です。
与えられた海外メディアの記事（見出しとリード文）を処理します。記事本文は持っていません。

記事ごとに次を決めてください。

1. relevant: 日本（日本政府・日本の社会・経済・企業・人物など）が記事の主要な対象なら true。
   日本がついでに触れられているだけ、または固有名詞の偶然の一致なら false。
2. event: この記事が報じている出来事。
   - 既存の出来事の一覧に同じ出来事があれば、その id を入れる。
   - なければ new_events に出来事を作り、その key（"n1", "n2", ...）を入れる。
   - 同じ出来事とは、同じ会談・発表・事件・決定などを指す。テーマが近いだけの別の出来事はまとめない。
   - relevant が false なら空文字にする。
3. summary_ja: 記事が何を伝えているかを日本語の一文（60字程度まで）で。
   原文の表現をそのまま訳さず、自分の言葉で要点をまとめる。見出しとリード文に書かれていないことは足さない。
4. tone: 記事の論調。「日本政府・日本側への評価」を軸に判定する。
   - "crit": 日本政府や日本側の対応に批判的、懸念や問題点が中心
   - "fav": 日本政府や日本側の対応を評価している、肯定的
   - "neu": 事実中心、評価がはっきりしない、または賛否を並べている
   迷ったら "neu" にする。媒体の一般的な評判ではなく、この記事の見出しとリード文だけで判断する。

新しい出来事（new_events）には次を書きます。
- title_ja: 出来事を表す中立的な一文の見出し（30字程度まで）。評価を含む言葉（「強硬」「弱腰」「歴史的」など）は使わない。
- fact_ja: 複数の媒体が一致して伝えている事実だけを1〜2文で。推測や評価は書かない。
- category: 指定の一覧から1つ。

relevant が true の記事が1件もない出来事は作らないでください。"""

SCHEMA = {
    "type": "object",
    "properties": {
        "new_events": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "title_ja": {"type": "string"},
                    "fact_ja": {"type": "string"},
                    "category": {"type": "string", "enum": CATEGORIES},
                },
                "required": ["key", "title_ja", "fact_ja", "category"],
                "additionalProperties": False,
            },
        },
        "articles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "relevant": {"type": "boolean"},
                    "event": {"type": "string"},
                    "summary_ja": {"type": "string"},
                    "tone": {"type": "string", "enum": ["crit", "neu", "fav"]},
                },
                "required": ["id", "relevant", "event", "summary_ja", "tone"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["new_events", "articles"],
    "additionalProperties": False,
}


class AIError(Exception):
    pass


def _build_input(articles, events, outlet_names):
    return json.dumps(
        {
            "existing_events": [
                {"id": e["id"], "title_ja": e["title_ja"], "category": e["category"],
                 "sample_headlines": e.get("sample_titles", [])}
                for e in events
            ],
            "articles": [
                {"id": a["id"], "outlet": outlet_names.get(a["outlet_id"], a["outlet_id"]),
                 "published_at": a["published_at"], "headline": a["title"],
                 "lead": a.get("description", "")}
                for a in articles
            ],
        },
        ensure_ascii=False,
    )


def available():
    return shutil.which("claude") is not None


def classify(articles, events, outlet_names):
    """記事のまとまりを処理し、{"new_events": [...], "articles": [...]} を返す。"""
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--json-schema", json.dumps(SCHEMA, ensure_ascii=False),
        "--system-prompt", SYSTEM,
        "--tools", "",
        "--no-session-persistence",
    ]
    if MODEL:
        cmd += ["--model", MODEL]
    prompt = "次の記事を処理してください。\n\n" + _build_input(articles, events, outlet_names)
    # 手元の CLAUDE.md や設定を拾わないよう、空の作業ディレクトリで実行する
    with tempfile.TemporaryDirectory() as cwd:
        try:
            proc = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                                  cwd=cwd, timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            raise AIError(f"{TIMEOUT_SECONDS}秒以内に応答がありませんでした")
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise AIError(f"claude の出力を読めません (exit {proc.returncode}): {(proc.stderr or proc.stdout)[:500]}")
    if out.get("is_error") or out.get("subtype") != "success":
        raise AIError(f"claude がエラーを返しました: {out.get('subtype')} {str(out.get('result'))[:500]}")
    result = out.get("structured_output")
    if not isinstance(result, dict):
        raise AIError("構造化された出力がありません")
    return result
