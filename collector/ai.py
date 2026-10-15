"""Claude で記事を出来事ごとにまとめ、要約・切り口・論調を付ける。

API の従量課金は使わず、Claude Code の CLI（`claude -p`）をサブスクリプションの認証で呼ぶ。
- ローカル: `claude` にログイン済みならそのまま動く
- GitHub Actions: `claude setup-token` で作ったトークンを CLAUDE_CODE_OAUTH_TOKEN に入れる

処理は3段階。
1. classify: 未処理の記事を出来事に振り分け、要約・切り口・論調（1件ずつの判定）を付ける
2. rejudge: 掲載条件を満たした出来事について、全記事を並べて論調を判定し直す
3. confirm_japan_coverage: 日本の主要媒体の検索結果から、その出来事を報じた記事を選ぶ

判定の材料: 本文を読める媒体（robots.txt で AI を拒否していない媒体。今は CNA）は本文、
読めない媒体（NYT・BBC は AI を名指しで拒否、WSJ は自動取得を全面拒否）は見出し + RSS のリード文。
"""

import json
import os
import shutil
import subprocess
import tempfile

from outlets import GOVERNMENT

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
   side が "japan" の記事（日本の媒体）は、政治・外交・安全保障・経済政策・企業・社会政策・エネルギー・
   科学技術政策・歴史認識の話題なら true、それ以外（文化・生活・スポーツ・エンタメなど）は false。
2. event: この記事が報じている出来事。
   - 既存の出来事の一覧に同じ出来事があれば、その id を入れる。
   - なければ new_events に出来事を作り、その key（"n1", "n2", ...）を入れる。
   - 同じ出来事とは、同じ会談・発表・事件・決定などを指す。テーマが近いだけの別の出来事はまとめない。
   - ある出来事への反応・反論・抗議・論評・解説は、日がずれて出ても元の出来事にまとめる
     （例: 日本の閣僚の発言 → 数日後の中国外務省の反論や社説は、発言の出来事に入れる）。
     日本の媒体が先に報じ、海外の媒体が数日遅れて報じることはよくあるので、日付の差だけで別の出来事にしない。
   - ただし、元の出来事とは別に新しい決定や行動が起きた場合（例: 反発を受けて相手国が制裁を発動）は新しい出来事にする。
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

さらに、このサイトの中心となる「日本の立場 → 海外の見方」のまとめを書く。
記事には side があり、"japan" は日本の媒体（日本の立場を知る材料）、"overseas" は海外の媒体（海外の見方）。
- japan_position_ja: 日本（政府・当事者）の立場や主張、日本側の受け止めを2〜3文で。
  side が "japan" の記事があればそれを主な材料にする。なければ海外の記事が伝えている日本政府・当事者の説明を使う。
  どちらにもなければ空文字にする。推測で日本の立場を作らない。
- japan_basis: japan_position_ja の材料。"japanese_media"（日本の媒体）、"overseas_reports"（海外記事が伝えた日本側の説明）、"none"。
- japan_views: side が "japan" の記事を出した媒体ごとに、その媒体の伝え方を1〜2文で（媒体ごとに1件、なければ空の配列）。
  outlet には媒体名をそのまま書く。
- japan_split: 日本の媒体どうしで評価や強調点が食い違っていれば true。1社だけ、または同じ方向なら false。
  食い違うときは、japan_position_ja には日本政府・当事者の立場と両社が一致している事実だけを書き、
  それぞれの見方は japan_views に分けて書く。どちらか一方の見方を日本の立場として代表させない。
- 媒体を「右派」「左派」「保守」「リベラル」などの立場の言葉で呼ばない（このサイトは媒体の立場を表示しない方針）。
- overseas_view_ja: 海外でどう見られているかを3〜4文で。side が "overseas" の記事だけを材料にする。
  government_affiliated が true の記事は、国営・政府系の媒体（政府の見方を伝える媒体）の記事。
  全体の傾向は、government_affiliated が false の独立した媒体の記事から書く。国営・政府系の媒体の見方は、
  最後に「中国の国営メディアは○○と主張している」のように、国営・政府系であることを明記して分けて書く。
  国営・政府系の媒体の主張を「海外では」「各国の媒体は」のような全体の見方として書かない。
  国・地域による違い（例: 米国の媒体は○○を強調）や、批判的・好意的な見方があればどの媒体かを添える。
  記事に書かれていないことは足さない。
- japan_position_ja と overseas_view_ja には、材料についての説明（「日本の媒体の記事はない」「見出しだけでは分からない」
  「ロイター配信」「今回の材料は○○のみ」など）を書かない。材料の出どころは画面に別に表示する。内容だけを書く。
- search_ja: 日本の新聞・テレビがこの出来事を報じたかを Google News で調べるための日本語の検索語。
  出来事を特定できる語を2〜4個、半角スペース区切りで（例: 「日銀 利上げ」「王毅 岩屋 台湾」）。人名は確実に分かる公人だけ漢字にする。
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
        "japan_position_ja": {"type": "string"},
        "japan_basis": {"type": "string", "enum": ["japanese_media", "overseas_reports", "none"]},
        "japan_views": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"outlet": {"type": "string"}, "view_ja": {"type": "string"}},
                "required": ["outlet", "view_ja"],
                "additionalProperties": False,
            },
        },
        "japan_split": {"type": "boolean"},
        "overseas_view_ja": {"type": "string"},
        "search_ja": {"type": "string"},
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
    "required": ["title_ja", "fact_ja", "japan_position_ja", "japan_basis", "japan_views", "japan_split",
                 "overseas_view_ja", "search_ja", "articles"],
    "additionalProperties": False,
}


CONFIRM_SYSTEM = """あなたは海外メディアの日本報道を比較するニュースサイトの編集者です。
1つの出来事と、日本の新聞・テレビのサイトを Google News で検索して見つかった記事の見出し（候補）を渡します。
候補のうち、この出来事そのもの（同じ会談・発表・事件・決定など）を報じている記事の id だけを選んでください。
- 出来事への反応・論評・社説も、この出来事を扱っていれば含める。
- テーマが近いだけの別の出来事、検索語が偶然一致しただけの記事は含めない。
- 見出しだけで同じ出来事か判断できないものは含めない。"""

CONFIRM_SCHEMA = {
    "type": "object",
    "properties": {"matches": {"type": "array", "items": {"type": "string"}}},
    "required": ["matches"],
    "additionalProperties": False,
}


class AIError(Exception):
    pass


def available():
    return shutil.which("claude") is not None


def _article_input(a, outlet_names):
    return {"id": a["id"], "outlet": outlet_names.get(a["outlet_id"], a["outlet_id"]),
            "side": a.get("side", "overseas"),
            "government_affiliated": a["outlet_id"] in GOVERNMENT,
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


def confirm_japan_coverage(event, candidates):
    """日本の主要媒体の検索結果のうち、出来事を報じている候補の id の一覧を返す。"""
    payload = {
        "event": {"title_ja": event["title_ja"], "fact_ja": event["fact_ja"],
                  "first_seen": event["first_seen"], "updated_at": event["updated_at"]},
        "candidates": [{"id": c["id"], "outlet": c["outlet"], "headline": c["title"],
                        "published_at": c["published_at"]} for c in candidates],
    }
    result = _run(CONFIRM_SYSTEM, CONFIRM_SCHEMA,
                  "次の候補から、出来事を報じている記事を選んでください。\n\n" + json.dumps(payload, ensure_ascii=False))
    return [i for i in result["matches"] if isinstance(i, str)]


# ---- 世界の主要ニュース（日本以外の出来事を、各国の媒体がどう報じたか） ----

# 「その他」（スポーツ・芸能・生活情報・その国の中だけの小さな事件など）は掲載しない
WORLD_CATEGORIES = ["政治", "外交", "紛争・安全保障", "経済", "社会", "災害・事故", "科学・環境・保健", "その他"]

WORLD_CLUSTER_SYSTEM = f"""あなたは、世界の出来事を各国の媒体がどう報じたかを比べるニュースサイトの編集者です。
各国の媒体の見出しを「id|媒体の国|見出し」の形で渡します（あれば「 / 」のあとにリード文の冒頭）。
同じ出来事を報じた見出しをまとめてください。

- 同じ出来事とは、同じ会談・発表・攻撃・選挙・判決・災害などを指す。テーマや地域が近いだけの別の出来事はまとめない
  （例: 「ウクライナがロシアの製油所を攻撃」と「ロシアがキーウを空爆」は別の出来事）。
- 出来事への反応・論評・続報は元の出来事にまとめる。ただし、新しい決定や行動が起きた場合は新しい出来事にする。
- existing_stories に同じ出来事があれば、その key を使う。なければ新しい key（"n1", "n2", ...）を作る。
- 新しい出来事を作るのは、国際的に重要になりうるものだけ: 各国の政治・選挙、外交、紛争・安全保障、経済・市場の大きな動き、
  大きな災害・事故、科学・環境・保健。その国の中だけの小さな事件、スポーツの結果、芸能、生活情報、一般的なコラムなどは
  出来事を作らず、その見出しはどの出来事にも入れない。
- 見出しが1件だけでも、上の条件に合えば出来事を作ってよい（あとで別の媒体の見出しが加わることがある）。
- 日本が主な対象の出来事（日本政府・日本企業・日本国内の出来事）は japan_subject を true にする（別のページで扱う）。
- 新しい出来事には title_ja（中立的な一文の見出し、30字程度まで。評価を含む言葉は使わない）、category、
  search_ja（日本の新聞・テレビがこの出来事を報じたかを調べる日本語の検索語。出来事を特定できる語を2〜4個、半角スペース区切り）を書く。
  既存の出来事では title_ja と search_ja は空文字でよい。
- category: {"・".join(WORLD_CATEGORIES)} から1つ。
- 出来事ごとの articles には、その出来事を報じた見出しの id をすべて入れる。1つの見出しは1つの出来事にだけ入れる。

{WRITING_RULES}"""

WORLD_CLUSTER_SCHEMA = {
    "type": "object",
    "properties": {
        "stories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "title_ja": {"type": "string"},
                    "category": {"type": "string", "enum": WORLD_CATEGORIES},
                    "japan_subject": {"type": "boolean"},
                    "search_ja": {"type": "string"},
                    "articles": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["key", "title_ja", "category", "japan_subject", "search_ja", "articles"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["stories"],
    "additionalProperties": False,
}

WORLD_COMPARE_SYSTEM = f"""あなたは、世界の出来事を各国の媒体がどう報じたかを比べるニュースサイトの編集者です。
1つの出来事について、各国の媒体の記事（見出しと、あればリード文）と、
日本の新聞・テレビのサイトを検索して見つかった見出しの候補（japan_candidates）を渡します。
このサイトの目的は、日本の報道だけに頼らず、同じ出来事を世界の各国がどう伝えたかを並べて見せることです。

次を書いてください。
- title_ja: 出来事を表す中立的な一文の見出し（30字程度まで）。評価を含む言葉は使わない。
- fact_ja: 複数の媒体が一致して伝えている事実だけを1〜2文で。推測や評価は書かない。
- country_views: 記事のある国ごとに、その国の媒体がこの出来事のどこに焦点を当て、どう伝えているかを1〜2文で。
  country には記事の country をそのまま書く。government_affiliated が true の媒体（国営・政府系）の記事だけの国は、
  「国営・政府系の媒体は」と主語を明記する。独立した媒体と国営・政府系の媒体が両方ある国は、分けて書く。
- difference_ja: 国による伝え方の違いを2〜3文で。何を強調し、何に触れていないか、誰の声を載せているか、言葉の強さの違いなど。
  違いを無理に作らない。どの国も事実を淡々と伝えているなら、そう一文で書く。
  国営・政府系の媒体の主張を「その国の見方」「各国では」のような全体の見方として書かない。
- articles: 記事ごとに summary_ja（何を伝えているかを日本語の一文、60字程度まで）と angle（何に焦点を当てているか、12字以内）。
- japan_matches: japan_candidates のうち、この出来事そのもの（同じ会談・発表・攻撃・決定など）を報じている見出しの id。
  テーマが近いだけの別の出来事、検索語が偶然一致しただけのものは含めない。見出しだけで判断できないものも含めない。
- japan_view_ja: japan_matches の見出しから、日本の主要媒体がこの出来事のどこに焦点を当てているかを、各国の伝え方と比べて1〜2文で。
  見出しから分かる範囲に限る（例: 日本人の被害や日本への影響を中心に伝えている、など）。japan_matches が空なら空文字。
- search_ja: 日本の新聞・テレビがこの出来事を報じたかを調べる日本語の検索語（2〜4語、半角スペース区切り）。
- place_countries: 出来事が起きた国、または出来事の主な当事者の国の ISO 3166-1 alpha-2 コード（例: 米大統領の決定なら ["US"]、
  ウクライナとロシアの攻撃の応酬なら ["UA", "RU"]）。国際会議など特定の国に当たらなければ空の配列。

- 媒体を「右派」「左派」「保守」「リベラル」などの立場の言葉で呼ばない（このサイトは媒体の立場を表示しない方針）。
- 材料についての説明（「見出しだけでは分からない」「今回の材料は○○のみ」など）は書かない。内容だけを書く。
- 記事に書かれていないことは足さない。

{WRITING_RULES}"""

WORLD_COMPARE_SCHEMA = {
    "type": "object",
    "properties": {
        "title_ja": {"type": "string"},
        "fact_ja": {"type": "string"},
        "country_views": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"country": {"type": "string"}, "view_ja": {"type": "string"}},
                "required": ["country", "view_ja"],
                "additionalProperties": False,
            },
        },
        "difference_ja": {"type": "string"},
        "articles": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "summary_ja": {"type": "string"}, "angle": {"type": "string"}},
                "required": ["id", "summary_ja", "angle"],
                "additionalProperties": False,
            },
        },
        "japan_matches": {"type": "array", "items": {"type": "string"}},
        "japan_view_ja": {"type": "string"},
        "search_ja": {"type": "string"},
        "place_countries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title_ja", "fact_ja", "country_views", "difference_ja", "articles", "japan_matches",
                 "japan_view_ja", "search_ja", "place_countries"],
    "additionalProperties": False,
}


def cluster_world(lines, existing):
    """見出しの行（"id|国|見出し"）を出来事にまとめ、{"stories": [...]} を返す。
    existing は [{"key", "title_ja", "headlines": [...]}]。"""
    payload = {"existing_stories": existing, "headlines": lines}
    return _run(WORLD_CLUSTER_SYSTEM, WORLD_CLUSTER_SCHEMA,
                "次の見出しを出来事にまとめてください。\n\n" + json.dumps(payload, ensure_ascii=False))


def compare_world(story, articles, japan_candidates):
    """1つの出来事について、国ごとの伝え方と日本の主要媒体との違いをまとめる。"""
    payload = {
        "story": {"title_ja": story["title_ja"], "fact_ja": story.get("fact_ja", "")},
        "articles": articles,
        "japan_candidates": [{"id": c["id"], "outlet": c["outlet"], "headline": c["title"],
                              "published_at": c["published_at"]} for c in japan_candidates],
    }
    return _run(WORLD_COMPARE_SYSTEM, WORLD_COMPARE_SCHEMA,
                "次の出来事について、各国の伝え方を比べてください。\n\n" + json.dumps(payload, ensure_ascii=False))
