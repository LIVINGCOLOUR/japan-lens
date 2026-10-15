"""世界の主要ニュース: 日本以外の出来事を、各国の媒体がどう報じたかを並べる。

日本の報道は世界の出来事の伝え方にも偏りがありうるので、同じ出来事を各国の媒体がどう伝えたかを並べ、
日本の主要媒体（NHK・全国紙・在京キー局）の見出しとも比べられるようにする。

情報が増えすぎないよう、AI の判断ではなく数で「主要なニュース」を決める（rules() を参照）:
- 国営・政府系ではない媒体が MIN_COUNTRIES か国以上で報じ、MIN_AREAS つ以上の地域圏（米州・欧州・アジアなど）にまたがる
- カテゴリーが「その他」（スポーツ・芸能など）ではなく、日本が主な対象ではない（日本の出来事はメインのページで扱う）
- そのうえで、1日（最初に報じられた日、日本時間）あたり、報じた国の多い順に PER_DAY 件まで。直近 DAYS 日分を載せる

    python world.py           # 収集して AI 処理まで
    python world.py --no-ai   # 収集だけ

内部用の全データは collector/state/world.json（リード文を含むので公開しない）、
サイトに載せる分だけを web/data/world.json に書き出す。
"""

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from fetch import fetch_feeds
from outlets import AREA, WORLD_COUNTRY, WORLD_GOVERNMENT, WORLD_OUTLETS, public_outlet

STATE_PATH = Path(__file__).resolve().parent / "state" / "world.json"
PUBLIC_PATH = Path(__file__).resolve().parent.parent / "web" / "data" / "world.json"

# 主要なニュースの条件（サイトの説明文にも world.json の rules として渡す）
MIN_COUNTRIES = 3
MIN_AREAS = 2
PER_DAY = 5
DAYS = 7

# 取得: 1媒体あたり新しい順にこの件数まで（国営通信など1日に数百件出す媒体で量が偏らないように）
PER_OUTLET = 40
MAX_AGE = timedelta(days=2)
# AI でまとめる見出しの1回あたりの件数と、既存の出来事として見せる期間
CLUSTER_BATCH = 250
CLUSTER_WINDOW_DAYS = 3
# 比べ直す出来事の数の上限（1回の実行あたり）と、1つの出来事で AI に見せる記事の数
COMPARE_LIMIT = 12
COMPARE_MAX_ARTICLES = 40
# 内部用データを残す期間。出来事に入らなかった見出しは短めに消す
KEEP_STORY_DAYS = 14
KEEP_LOOSE_DAYS = 4

JST = timezone(timedelta(hours=9))
PUBLIC_ARTICLE_FIELDS = ("id", "outlet_id", "url", "title", "published_at", "summary_ja", "angle")
PUBLIC_STORY_FIELDS = ("id", "title_ja", "fact_ja", "category", "first_seen", "updated_at", "country_views",
                       "difference_ja", "japan_main", "japan_view_ja", "japan_main_checked_at", "place_countries")


def _now():
    return datetime.now(timezone.utc)


def _since(days):
    return (_now() - timedelta(days=days)).isoformat()


def _norm(title):
    return " ".join(title.lower().split())


class WorldStore:
    def __init__(self, path=STATE_PATH):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"stories": [], "articles": []}

    @property
    def stories(self):
        return self.data["stories"]

    @property
    def articles(self):
        return self.data["articles"]

    def add(self, found):
        urls = {a["url"] for a in self.articles}
        titles = {(a["outlet_id"], _norm(a["title"])) for a in self.articles}
        added = 0
        for a in found:
            key = (a["outlet_id"], _norm(a["title"]))
            if a["url"] in urls or key in titles:
                continue
            urls.add(a["url"])
            titles.add(key)
            self.articles.append({
                "id": str(uuid.uuid4()), "outlet_id": a["outlet_id"], "url": a["url"], "title": a["title"],
                "published_at": a["published_at"], "description": a.get("description", "")[:400],
                "story_id": None, "clustered": False, "summary_ja": None, "angle": None,
            })
            added += 1
        return added

    def articles_of(self, story_id):
        return [a for a in self.articles if a["story_id"] == story_id]

    def story(self, story_id):
        return next((s for s in self.stories if s["id"] == story_id), None)

    def touch(self, story):
        times = [a["published_at"] for a in self.articles_of(story["id"])]
        if times:
            story["first_seen"], story["updated_at"] = min(times), max(times)

    def prune(self):
        keep_story = _since(KEEP_STORY_DAYS)
        self.data["stories"] = [s for s in self.stories if s["updated_at"] >= keep_story]
        alive = {s["id"] for s in self.stories}
        loose = _since(KEEP_LOOSE_DAYS)
        self.data["articles"] = [a for a in self.articles
                                 if (a["story_id"] in alive) or (a["story_id"] is None and a["published_at"] >= loose)]
        has_articles = {a["story_id"] for a in self.articles}
        self.data["stories"] = [s for s in self.stories if s["id"] in has_articles]

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        tmp.replace(self.path)


def collect(ws):
    for outlet in WORLD_OUTLETS:
        found, errors = fetch_feeds(outlet, outlet["world_feeds"], japan_only=False, max_age=MAX_AGE)
        for e in errors:
            print(f"  [world:{outlet['id']}] フィード取得エラー: {e}", file=sys.stderr)
        found.sort(key=lambda a: a["published_at"], reverse=True)
        added = ws.add(found[:PER_OUTLET])
        print(f"  [world:{outlet['id']}] {len(found)} 件 / 新規 {added} 件")


# ---- 主要なニュースの判定（数で決める） ----

def stats(articles):
    outlets = {a["outlet_id"] for a in articles}
    independent = {WORLD_COUNTRY[o] for o in outlets if o not in WORLD_GOVERNMENT and o in WORLD_COUNTRY}
    return {
        "outlets": len(outlets),
        "countries": len({WORLD_COUNTRY[o] for o in outlets if o in WORLD_COUNTRY}),
        "independent_countries": len(independent),
        "areas": len({AREA[c] for c in independent if c in AREA}),
    }


def qualifies(story, st):
    return (story["category"] != "その他" and not story.get("japan_subject")
            and st["independent_countries"] >= MIN_COUNTRIES and st["areas"] >= MIN_AREAS)


def select(ws):
    """掲載する出来事を選ぶ: 条件を満たすもののうち、最初に報じられた日ごとに報じた国の多い順で PER_DAY 件まで。"""
    since = _since(DAYS)
    by_day = {}
    for s in ws.stories:
        if s["first_seen"] < since:
            continue
        st = stats(ws.articles_of(s["id"]))
        if not qualifies(s, st):
            continue
        day = datetime.fromisoformat(s["first_seen"]).astimezone(JST).date().isoformat()
        by_day.setdefault(day, []).append((s, st))
    chosen = []
    for day, items in by_day.items():
        items.sort(key=lambda x: (x[1]["independent_countries"], x[1]["countries"], x[1]["outlets"],
                                  x[0]["updated_at"]), reverse=True)
        chosen += [(s, st, day) for s, st in items[:PER_DAY]]
    chosen.sort(key=lambda x: (x[2], x[1]["independent_countries"], x[1]["outlets"]), reverse=True)
    return chosen


# ---- AI 処理 ----

def cluster(ws):
    from ai import AIError, cluster_world

    total = 0
    while True:
        batch = sorted((a for a in ws.articles if not a["clustered"]), key=lambda a: a["published_at"])[:CLUSTER_BATCH]
        if not batch:
            break
        since = _since(CLUSTER_WINDOW_DAYS)
        recent = [s for s in ws.stories if s["updated_at"] >= since]
        existing_key = {f"s{i}": s["id"] for i, s in enumerate(recent, 1)}
        existing = [{"key": k, "title_ja": ws.story(sid)["title_ja"],
                     "headlines": [a["title"] for a in ws.articles_of(sid)][:3]}
                    for k, sid in existing_key.items()]
        short = {f"a{i}": a for i, a in enumerate(batch, 1)}
        lines = [f"{k}|{WORLD_COUNTRY.get(a['outlet_id'], '?')}|{a['title']}" for k, a in short.items()]
        try:
            result = cluster_world(lines, existing)
        except AIError as e:
            print(f"  世界の見出しのまとめを中断しました: {e}", file=sys.stderr)
            return False
        touched = set()
        for st in result["stories"]:
            members = [short[i] for i in st["articles"] if i in short and short[i]["story_id"] is None]
            if not members:
                continue
            if st["key"] in existing_key:
                story = ws.story(existing_key[st["key"]])
            else:
                story = {"id": str(uuid.uuid4()), "title_ja": st["title_ja"], "fact_ja": "",
                         "category": st["category"], "japan_subject": st["japan_subject"],
                         "search_ja": st["search_ja"], "compared_count": 0,
                         "first_seen": members[0]["published_at"], "updated_at": members[0]["published_at"]}
                ws.stories.append(story)
            for a in members:
                a["story_id"] = story["id"]
            touched.add(story["id"])
        for a in batch:
            a["clustered"] = True
        for sid in touched:
            ws.touch(ws.story(sid))
        total += len(batch)
        ws.save()
    print(f"  世界の見出しをまとめた件数 {total} 件 / 出来事 {len(ws.stories)} 件")
    return True


def compare(ws, chosen):
    from ai import AIError, compare_world
    from main import _japan_candidates  # 日本の主要媒体の検索は、日本の出来事と同じ方法で行う

    names = {o["id"]: o["name"] for o in WORLD_OUTLETS}
    done = 0
    for story, _st, _day in chosen:
        if done >= COMPARE_LIMIT:
            break
        articles = ws.articles_of(story["id"])
        if story.get("compared_count") == len(articles):
            continue
        candidates = []
        if story.get("search_ja"):
            candidates, err = _japan_candidates(story)
            if err:
                print(f"  日本の主要媒体の検索に失敗しました: {err}", file=sys.stderr)
                candidates = []
        shown = sorted(articles, key=lambda a: a["published_at"])[:COMPARE_MAX_ARTICLES]
        short = {f"a{i}": a for i, a in enumerate(shown, 1)}
        material = [{"id": k, "outlet": names.get(a["outlet_id"], a["outlet_id"]),
                     "country": WORLD_COUNTRY.get(a["outlet_id"], ""),
                     "government_affiliated": a["outlet_id"] in WORLD_GOVERNMENT,
                     "published_at": a["published_at"], "headline": a["title"], "lead": a.get("description", "")}
                    for k, a in short.items()]
        try:
            result = compare_world(story, material, candidates)
        except AIError as e:
            print(f"  世界の出来事の比較を中断しました: {e}", file=sys.stderr)
            break
        for r in result["articles"]:
            if r["id"] in short:
                short[r["id"]].update(summary_ja=r["summary_ja"], angle=r["angle"])
        matched = set(result["japan_matches"])
        story.update({
            "title_ja": result["title_ja"], "fact_ja": result["fact_ja"],
            "country_views": result["country_views"], "difference_ja": result["difference_ja"],
            "japan_main": [{k: c[k] for k in ("outlet", "title", "url", "published_at")}
                           for c in candidates if c["id"] in matched],
            "japan_view_ja": result["japan_view_ja"] if matched else "",
            "search_ja": result["search_ja"] or story.get("search_ja", ""),
            # 各社の世界・国際面から集めているので、出来事が起きた国の媒体は国内面で報じていても拾えないことがある。
            # その国はサイトの「報道なし」に含めない
            "place_countries": [c.upper() for c in result["place_countries"] if isinstance(c, str)],
            "compared_count": len(articles),
        })
        if story.get("search_ja"):
            story["japan_main_checked_at"] = _now().isoformat()
        ws.save()
        done += 1
    print(f"  各国の伝え方を比べた出来事 {done} 件")


# ---- 書き出し ----

def export(ws, chosen):
    stories, articles = [], []
    for story, st, day in chosen:
        row = {k: story.get(k) for k in PUBLIC_STORY_FIELDS}
        row.update(day=day, **{f"n_{k}": v for k, v in st.items()})
        stories.append(row)
        for a in ws.articles_of(story["id"]):
            articles.append({**{k: a.get(k) for k in PUBLIC_ARTICLE_FIELDS}, "story_id": story["id"]})
    data = {
        "generated_at": _now().isoformat(),
        "rules": {"min_countries": MIN_COUNTRIES, "min_areas": MIN_AREAS, "per_day": PER_DAY, "days": DAYS,
                  "per_outlet": PER_OUTLET},
        "areas": AREA,
        "outlets": [public_outlet(o) for o in WORLD_OUTLETS],
        "stories": stories,
        "articles": articles,
    }
    PUBLIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"  世界の主要ニュース {len(stories)} 件を書き出しました")


def run(use_ai=True):
    ws = WorldStore()
    try:
        collect(ws)
        ws.save()
        if use_ai and cluster(ws):
            compare(ws, select(ws))
        ws.prune()
        export(ws, select(ws))
    finally:
        ws.save()


def main():
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ai", action="store_true", help="収集だけ行い AI 処理をしない")
    args = parser.parse_args()
    from ai import available
    use_ai = not args.no_ai and available()
    if not use_ai:
        print("  AI 処理はスキップしました")
    print(f"保存先: {PUBLIC_PATH}（内部用: {STATE_PATH}）")
    run(use_ai)


if __name__ == "__main__":
    main()
