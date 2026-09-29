"""Claude で記事を出来事ごとにまとめ、要約・切り口・論調を付ける。

API の従量課金は使わず、Claude Code の CLI（`claude -p`）をサブスクリプションの認証で呼ぶ。
- ローカル: `claude` にログイン済みならそのまま動く
- GitHub Actions: `claude setup-token` で作ったトークンを CLAUDE_CODE_OAUTH_TOKEN に入れる

処理は2段階。
1. classify: 未処理の記事を出来事に振り分け、要約・切り口・論調（1件ずつの判定）を付ける
2. rejudge: 掲載条件を満たした出来事について、全記事を並べて論調を判定し直す

判定の材料: 本文を読める媒体（robots.txt で AI を拒否していない媒体。今は CNA）は本文、
読めない媒体（NYT・BBC は AI を名指しで拒否、WSJ は自動取得を全面拒否）は見出し + RSS のリード文。
"""

import json
import os
import shutil
import subprocess
import tempfile

# 未設定ならサブスクリプションの既定モデル。例: CLAUDE_MODEL=sonnet
MODEL = os.environ.get("CLAUDE_MODEL")
TIMEOUT_SECONDS = 600
# 「日本が政治的・経済的にどう見られているか」に関わるカテゴリー。それ以外はすべて「その他」
CATEGORIES = ["政治", "外交", "安全保障", "経済政策", "企業・産業", "社会政策",
              "エネルギー・資源", "科学技術政策", "歴史認識", "その他"]
TONES = ["crit", "neu", "fav", "none"]

WRITING_RULES = """日本語の書き方:
- 原文の表現をそのまま訳さず、自分の言葉で要点をまとめる。記事に書かれていないことは足さない。
- 人名がローマ字でしか書かれていない場合、漢字を推測しない。カタカナで書く（例: Yuki Kurihara → クリハラ・ユキ選手）。
  漢字を使ってよいのは、首相・閣僚・日銀総裁など、誰のことか確実に分かる公人だけ。
- 地名・組織名も、確実に分からないものはカタカナか原文のまま書く。
- 性別・年齢・国籍・肩書きなど、記事に書かれていない属性を推測で足さない（例: "kid" を「少年」にしない）。
- 開催地・日付・背景などを自分の知識で補わない。正しいと思っても、記事に書かれていなければ書かない。"""

TONE_RULES = """論調の判定:
出来事ごとの「評価の対象」（target）に対して、この記事がどういう見方を示しているかを判定する。

手順:
1. 見出し・リード文・本文（あれば）から、評価の手がかりを探す。
   本文がある記事は、全体を通して何を強調しているか、どんな声を引用しているか、結論で何を言っているかを重視する。
   - 評価を含む言葉（例: muddied, reckless, bold, welcome, blow, boost, controversial）
   - 何を強調しているか（成果・利点か、リスク・負担・懸念か）
   - 誰の声を載せているか（支持する側か、批判する側か）
   - 記事の種類（Opinion, Analysis, Editorial などの表示）
2. 手がかりから判定する。
   - "crit": 手がかりが対象に否定的な向き（問題点・懸念・批判の強調、否定的な言葉）
   - "fav": 手がかりが対象に肯定的な向き（成果・評価・支持の強調、肯定的な言葉）
   - "neu": 手がかりはあるが両方の向きが釣り合っている、または対象に触れつつ事実を淡々と伝えている
   - "none": 評価の対象がない出来事（target が空）、または手がかりが見つからない
3. evidence に、判定の根拠にした語句を原文（英語）のまま短く（12語以内）書く。"none" のときは空文字。
   evidence は見出し・リード文・本文に実際にある語句だけにする。

媒体の一般的な評判では判断しない。この記事に書かれている内容だけで判断する。
本文がない記事は見出しとリード文だけで判断し、本文がある記事と比べて手がかりが少ないことを理由に無理に評価を付けない。
手がかりがないのに "neu" にしない。その場合は "none" にする。

angle（切り口）: 記事が何に焦点を当てているかを日本語で短く（12字以内）。論調に関係なく必ず書く。
例: 「被害の規模」「交通の混乱」「市場への影響」「米国の圧力」「家計の負担」"""

CLASSIFY_SYSTEM = f"""あなたは海外メディアの日本報道を比較するニュースサイトの編集者です。
与えられた海外メディアの記事を処理します。記事には見出しと、あればリード文（lead）、
さらに一部の媒体は本文（body）が付いています。本文がある記事は本文まで読んで判断してください。

記事ごとに次を決めてください。

1. relevant: 日本（日本政府・日本の社会・経済・企業・人物など）が記事の主要な対象なら true。
   日本がついでに触れられているだけ、または固有名詞の偶然の一致なら false。
2. event: この記事が報じている出来事。
   - 既存の出来事の一覧に同じ出来事があれば、その id を入れる。
   - なければ new_events に出来事を作り、その key（"n1", "n2", ...）を入れる。
   - 同じ出来事とは、同じ会談・発表・事件・決定などを指す。テーマが近いだけの別の出来事はまとめない。
   - relevant が false なら空文字にする。
3. summary_ja: 記事が何を伝えているかを日本語の一文（60字程度まで）で。
4. angle, tone, evidence: 下の「論調の判定」に従う。

新しい出来事（new_events）には次を書きます。
- title_ja: 出来事を表す中立的な一文の見出し（30字程度まで）。評価を含む言葉（「強硬」「弱腰」「歴史的」など）は使わない。
- fact_ja: 複数の媒体が一致して伝えている事実だけを1〜2文で。推測や評価は書かない。
- category: 指定の一覧から1つ。
  政治=政権運営・選挙・内閣。外交=首脳会談・国際機関での発言・二国間関係。安全保障=防衛・自衛隊・同盟。
  経済政策=日銀の金融政策・財政・税・為替介入・通商交渉。企業・産業=日本企業の投資・買収・海外展開・業界の動き。
  社会政策=移民・外国人労働者・少子化・法改正・難民や亡命への対応など政府の社会政策。
  エネルギー・資源=エネルギーや資源の調達・原発・処理水。科学技術政策=半導体支援・AI規制など国の技術政策。
  歴史認識=戦争の記憶・謝罪や談話・歴史をめぐる外交問題。
  その他=スポーツ、災害、文化・観光・エンタメ、事件・事故、訃報、毎日の市況（株価・為替の値動き・景気指標の発表）など。
- target: 論調を測る「評価の対象」を日本語で短く（例: 「日銀の利上げ判断」「高市首相の国連での要求」）。
  日本政府・日本の組織・日本企業などの判断や行動が対象になる。
  自然災害、スポーツの結果、事故、訃報など、評価する判断や行動がない出来事は空文字にする。

relevant が true の記事が1件もない出来事は作らないでください。

{TONE_RULES}

{WRITING_RULES}"""

REJUDGE_SYSTEM = f"""あなたは海外メディアの日本報道を比較するニュースサイトの編集者です。
1つの出来事について、複数の媒体の記事（見出し、あればリード文と本文）を並べて渡します。
記事どうしを比べて、各記事の論調・根拠・切り口を判定し直し、要約（summary_ja: 日本語の一文、60字程度まで）も書き直してください。

比べることで、1件だけでは見えない違いに注目する:
- 同じ事実を、ある社はリスクとして、ある社は成果として書いていないか
- ある社だけが批判的な声や特定の背景（例: 外国の圧力）を持ち出していないか
- 言葉の強さの違い（例: "raises" と "gambles on"）

ただし、違いを無理に作らない。どの記事も事実を淡々と伝えているなら、そのまま "neu" か "none" にする。
target が空の出来事では、全記事 "none" にし、angle だけ書く。

あわせて、出来事の見出し（title_ja）と事実の説明（fact_ja）を、全記事を踏まえた最新の内容に書き直す。
たとえば「利上げの見通し」の段階で作られた出来事に「利上げを決めた」記事が加わったなら、決定した事実に合わせる。
書き方の条件は元の見出し・説明と同じ（中立的な一文、複数の媒体が一致して伝えている事実だけ）。

{TONE_RULES}

{WRITING_RULES}"""

_JUDGEMENT = {
    "angle": {"type": "string"},
    "tone": {"type": "string", "enum": TONES},
    "evidence": {"type": "string"},
}

CLASSIFY_SCHEMA = {
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
                    "target": {"type": "string"},
                },
                "required": ["key", "title_ja", "fact_ja", "category", "target"],
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
                    **_JUDGEMENT,
                },
                "required": ["id", "relevant", "event", "summary_ja", "angle", "tone", "evidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["new_events", "articles"],
    "additionalProperties": False,
}

REJUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "title_ja": {"type": "string"},
        "fact_ja": {"type": "string"},
        "articles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "summary_ja": {"type": "string"}, **_JUDGEMENT},
                "required": ["id", "summary_ja", "angle", "tone", "evidence"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["title_ja", "fact_ja", "articles"],
    "additionalProperties": False,
}


class AIError(Exception):
    pass


def available():
    return shutil.which("claude") is not None


def _article_input(a, outlet_names):
    return {"id": a["id"], "outlet": outlet_names.get(a["outlet_id"], a["outlet_id"]),
            "published_at": a["published_at"], "headline": a["title"],
            "lead": a.get("description", ""), "body": a.get("body", "")}


def _run(system, schema, prompt):
    cmd = [
        "claude", "-p",
        "--output-format", "json",
        "--json-schema", json.dumps(schema, ensure_ascii=False),
        "--system-prompt", system,
        "--tools", "",
        "--no-session-persistence",
    ]
    if MODEL:
        cmd += ["--model", MODEL]
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


def classify(articles, events, outlet_names):
    """未処理の記事を処理し、{"new_events": [...], "articles": [...]} を返す。"""
    payload = {
        "existing_events": [
            {"id": e["id"], "title_ja": e["title_ja"], "category": e["category"],
             "target": e.get("target", ""), "sample_headlines": e.get("sample_titles", [])}
            for e in events
        ],
        "articles": [_article_input(a, outlet_names) for a in articles],
    }
    return _run(CLASSIFY_SYSTEM, CLASSIFY_SCHEMA,
                "次の記事を処理してください。\n\n" + json.dumps(payload, ensure_ascii=False))


def rejudge(event, articles, outlet_names):
    """1つの出来事の記事を並べて判定し直し、{"title_ja", "fact_ja", "articles": [...]} を返す。"""
    payload = {
        "event": {"title_ja": event["title_ja"], "fact_ja": event["fact_ja"],
                  "target": event.get("target", "")},
        "articles": [_article_input(a, outlet_names) for a in articles],
    }
    return _run(REJUDGE_SYSTEM, REJUDGE_SCHEMA,
                "次の出来事の記事を比べて判定してください。\n\n" + json.dumps(payload, ensure_ascii=False))
