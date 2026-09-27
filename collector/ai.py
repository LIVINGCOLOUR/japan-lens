"""Claude で記事を出来事ごとにまとめ、要約と論調を付ける。

1回の呼び出しで、未処理の記事のまとまりと直近の出来事の一覧を渡し、
記事ごとに「どの出来事か（既存 / 新規）」「日本語の要約」「論調」を返してもらう。
"""

import json

import anthropic

MODEL = "claude-opus-5"
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


def classify(articles, events, outlet_names, client=None):
    """記事のまとまりを処理し、{"new_events": [...], "articles": [...]} を返す。"""
    client = client or anthropic.Anthropic()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        thinking={"type": "adaptive"},
        system=SYSTEM,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{
            "role": "user",
            "content": "次の記事を処理してください。\n\n" + _build_input(articles, events, outlet_names),
        }],
    )
    if response.stop_reason == "refusal":
        raise AIError(f"refusal: {response.stop_details} (request {response._request_id})")
    if response.stop_reason == "max_tokens":
        raise AIError(f"max_tokens で出力が途切れました (request {response._request_id})")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if text is None:
        raise AIError(f"テキストの応答がありません (request {response._request_id})")
    return json.loads(text)
