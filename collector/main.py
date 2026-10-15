"""収集処理の入口。1日1回（日本時間の朝6時）実行する想定。

    python main.py              # 収集して AI 処理まで
    python main.py --no-ai      # 収集だけ（AI を使わずに動作確認するとき）
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from pathlib import Path

from dotenv import load_dotenv

from ai import available as ai_available
from body import fetch_body
from fetch import fetch_outlet
from outlets import COUNTRY, GOVERNMENT, JAPAN_MAIN_OUTLETS, JAPAN_SIDE, OUTLETS, public_outlet
from store import LEADS_PATH, STORE_PATH, Leads, Store

BATCH_SIZE = 30
# 既存の出来事として AI に見せる期間。短いと、遅れて届いた記事が同じ出来事の重複を作る
EVENT_WINDOW_DAYS = 30
# 掲載条件（web/src/lib/rules.ts と同じ値にする）。条件を満たした出来事は記事を並べて判定し直す
MIN_OUTLETS = 2
# 判定の指示を変えたら上げる。上がると、掲載中の出来事をすべて判定し直す
JUDGE_VERSION = 2
# 読者が「AIで本文を読む」を押した記事の判定（web/worker/index.ts）。毎日の判定し直しの材料にする
READINGS_URL = "https://japan-lens.mon-m.workers.dev/api/readings"
# 日本の主要媒体の報道を確かめる出来事の数の上限（1回の実行あたり）。残りは次回に回す
COVERAGE_LIMIT = 20
# 日本の主要媒体の記事を探す期間。出来事の最初の記事の少し前から、最後の記事の少しあとまで
COVERAGE_BEFORE_DAYS = 2
COVERAGE_AFTER_DAYS = 4
# 媒体ごとの検索で AI に見せる候補の数と、検索の間隔
COVERAGE_PER_OUTLET = 5
COVERAGE_PAUSE_SECONDS = 0.5
# 掲載するカテゴリー（web/src/lib/rules.ts と同じ）。これ以外は判定し直さない
SHOWN_CATEGORIES = {"政治", "外交", "安全保障", "経済政策", "企業・産業", "社会政策",
                    "エネルギー・資源", "科学技術政策", "歴史認識"}


def eligible(outlet_ids):
    """掲載条件: 海外の媒体が MIN_OUTLETS 以上の「声」で報じ、うち1つ以上が独立した媒体であること。
    同じ国の国営・政府系の媒体はまとめて1つの声と数える（国営メディア2社だけで条件を満たさないように）。
    日本側の媒体は数えない。web/src/lib/rules.ts の isEligible と同じにする。"""
    overseas = {i for i in outlet_ids if i not in JAPAN_SIDE}
    independent = {i for i in overseas if i not in GOVERNMENT}
    gov_countries = {COUNTRY[i] for i in overseas if i in GOVERNMENT}
    return bool(independent) and len(independent) + len(gov_countries) >= MIN_OUTLETS


def shown(ev, articles):
    """サイトに掲載される出来事か（カテゴリー・評価の対象・掲載条件）。"""
    return (ev["category"] in SHOWN_CATEGORIES and bool(ev.get("target"))
            and eligible({a["outlet_id"] for a in articles}))


def collect(store, leads):
    store.upsert_outlets([public_outlet(o) for o in OUTLETS])
    for outlet in OUTLETS:
        found, errors = fetch_outlet(outlet)
        for e in errors:
            print(f"  [{outlet['id']}] フィード取得エラー: {e}", file=sys.stderr)
        new = store.add_articles(found, leads)
        print(f"  [{outlet['id']}] 日本関連 {len(found)} 件 / 新規 {len(new)} 件")


def _judgement(r):
    tone = r["tone"]
    return {"angle": r["angle"], "tone": tone, "evidence": r["evidence"] if tone != "none" else ""}


def apply_result(store, batch, result, existing_ids):
    by_id = {a["id"]: a for a in batch}
    new_events = {ev["key"]: ev for ev in result["new_events"]}
    created = {}  # key → id。記事が付いた出来事だけ作る
    now = datetime.now(timezone.utc).isoformat()
    done = 0
    for r in result["articles"]:
        if r["id"] not in by_id:
            continue
        if not r["relevant"]:
            store.update_article(r["id"], {"relevant": False, "processed_at": now})
            done += 1
            continue
        ref = r["event"]
        published = by_id[r["id"]]["published_at"]
        if ref in new_events:
            if ref not in created:
                ev = new_events[ref]
                created[ref] = store.create_event(ev["title_ja"], ev["fact_ja"], ev["category"],
                                                  ev["target"], published)
            event_id = created[ref]
        elif ref in existing_ids:
            event_id = ref
        else:
            continue  # 出来事が決まらなかった記事は次回に再処理
        store.update_article(r["id"], {
            "relevant": True, "event_id": event_id, "summary_ja": r["summary_ja"],
            **_judgement(r), **_basis(by_id[r["id"]]), "processed_at": now,
        })
        store.touch_event(event_id, published)
        done += 1
    return done


def load_readings():
    """読者の操作で AI が本文を読んだ記事の要約。取れなければ空（判定し直しは見出しなどで続ける）。"""
    import json
    import urllib.request

    try:
        req = urllib.request.Request(READINGS_URL, headers={"User-Agent": "JapanLensCollector/0.1"})
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print(f"  読者が読ませた記事の判定を取得できませんでした: {e}", file=sys.stderr)
        return {}


def _with_material(articles, leads, readings=None):
    """AI に渡す材料を付ける: 内部保存のリード文・タグと、読める媒体なら本文。
    自動では本文を読めない媒体でも、読者の操作で AI が本文を読んだ記事はその要約を本文の代わりに渡す。"""
    readings = readings or {}
    out = []
    for a in articles:
        lead = leads.get(a["url"])
        body = fetch_body(a)
        if not body and a["id"] in readings:
            body = "（読者の操作で AI が記事の本文を読んだ要約）" + readings[a["id"]].get("summary_ja", "")
        out.append({**a, "description": lead.get("lead", ""), "tags": lead.get("tags", []), "body": body,
                    "side": "japan" if a["outlet_id"] in JAPAN_SIDE else "overseas"})
    return out


def _basis(a):
    # 画面に「本文で判定」と出すための印
    return {"basis": "body" if a.get("body") else "headline"}


def process(store, leads):
    from ai import AIError, classify

    names = {o["id"]: o["name"] for o in OUTLETS}
    total = 0
    seen = set()
    while True:
        batch = [a for a in store.unprocessed_articles(BATCH_SIZE) if a["id"] not in seen]
        if not batch:
            break
        seen.update(a["id"] for a in batch)
        events = store.recent_events(EVENT_WINDOW_DAYS)
        try:
            material = _with_material(batch, leads)
            result = classify(material, events, names)
        except AIError as e:
            print(f"  AI 処理を中断しました: {e}", file=sys.stderr)
            return False
        total += apply_result(store, material, result, {e["id"] for e in events})
        store.save()  # 途中で止まっても処理済みの分は残す
    print(f"  AI 処理 {total} 件")
    return True


def rejudge_events(store, leads):
    """掲載条件を満たした出来事のうち、前回の判定から記事が増えたものを並べて判定し直す。"""
    from ai import AIError, rejudge

    names = {o["id"]: o["name"] for o in OUTLETS}
    readings = load_readings()
    done = 0
    # 期間では絞らない（判定済みで記事が増えていない出来事は下で飛ばすので、毎回の負担は増えない）
    for ev in store.recent_events(days=3650):
        articles = store.articles_of(ev["id"])
        # 画面に出さない出来事は判定し直さない
        if not shown(ev, articles):
            continue
        # 読者が本文を読ませた記事が増えたときも判定し直す
        read_count = sum(1 for a in articles if a["id"] in readings)
        if (ev.get("judged_count") == len(articles) and ev.get("judge_version") == JUDGE_VERSION
                and ev.get("read_count", 0) == read_count):
            continue
        try:
            material = _with_material(articles, leads, readings)
            result = rejudge(ev, material, names)
        except AIError as e:
            print(f"  判定し直しを中断しました: {e}", file=sys.stderr)
            break
        by_id = {a["id"]: a for a in material}
        for r in result["articles"]:
            if r["id"] in by_id:
                store.update_article(r["id"], {"summary_ja": r["summary_ja"], **_judgement(r),
                                               **_basis(by_id[r["id"]])})
        store.set_judged(ev["id"], len(articles), {
            "judge_version": JUDGE_VERSION,
            "read_count": read_count,
            **{k: result[k] for k in ("title_ja", "fact_ja", "japan_position_ja", "japan_basis",
                                      "japan_views", "japan_split", "overseas_view_ja", "search_ja")},
        })
        store.save()
        done += 1
    print(f"  並べて判定し直した出来事 {done} 件")


def _outlet_by_host(href):
    host = urlparse(href).netloc.lower()
    for o in JAPAN_MAIN_OUTLETS:
        if host in (o["domain"], "www." + o["domain"]):
            return o["name"]
    return None


def _japan_candidates(ev):
    """出来事の検索語で、日本の主要媒体の記事を Google News から探す。
    全媒体をまとめて1回で検索すると結果が一部の媒体に偏り、報じている媒体を見落とすので、媒体ごとに検索する。"""
    from fetch import google_news

    first = datetime.fromisoformat(ev["first_seen"]) - timedelta(days=COVERAGE_BEFORE_DAYS)
    last = datetime.fromisoformat(ev["updated_at"]) + timedelta(days=COVERAGE_AFTER_DAYS)
    candidates = []
    for o in JAPAN_MAIN_OUTLETS:
        query = f"{ev['search_ja']} site:{o['domain']} after:{first:%Y-%m-%d} before:{last:%Y-%m-%d}"
        entries, err = google_news(query, "ja", "JP")
        if err:
            return None, err
        for e in entries[:COVERAGE_PER_OUTLET]:
            if e["link"] and _outlet_by_host(e["source"]) == o["name"]:
                candidates.append({"id": f"c{len(candidates)}", "outlet": o["name"], "title": e["title"],
                                   "url": e["link"], "published_at": e["published"].isoformat()})
        time.sleep(COVERAGE_PAUSE_SECONDS)
    return candidates, None


def check_japan_coverage(store):
    """掲載中の出来事について、日本の主要媒体（NHK・全国紙・在京キー局）が報じたかを確かめる。
    「あえて報じない」ことを見えるようにするため。記事が増えた出来事だけ確かめ直す。"""
    from ai import AIError, confirm_japan_coverage

    done = 0
    for ev in store.recent_events(EVENT_WINDOW_DAYS):
        if done >= COVERAGE_LIMIT:
            break
        articles = store.articles_of(ev["id"])
        if not shown(ev, articles) or not ev.get("search_ja"):
            continue
        if ev.get("japan_main_count") == len(articles):
            continue
        candidates, err = _japan_candidates(ev)
        if err:
            print(f"  日本の主要媒体の検索に失敗しました: {err}", file=sys.stderr)
            continue
        try:
            matched = set(confirm_japan_coverage(ev, candidates)) if candidates else set()
        except AIError as e:
            print(f"  日本の主要媒体の確認を中断しました: {e}", file=sys.stderr)
            break
        found = [{k: c[k] for k in ("outlet", "title", "url", "published_at")}
                 for c in candidates if c["id"] in matched]
        store.update_event(ev["id"], {"japan_main": found, "japan_main_count": len(articles),
                                      "japan_main_checked_at": datetime.now(timezone.utc).isoformat()})
        store.save()
        done += 1
    print(f"  日本の主要媒体の報道を確かめた出来事 {done} 件")


def main():
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ai", action="store_true", help="収集だけ行い AI 処理をしない")
    parser.add_argument("--no-world", action="store_true", help="世界の主要ニュース（world.py）を処理しない")
    args = parser.parse_args()

    store = Store()
    leads = Leads()
    print(f"保存先: {STORE_PATH}（内部用: {LEADS_PATH}）")
    try:
        collect(store, leads)
        if args.no_ai:
            print("  AI 処理はスキップしました (--no-ai)")
        elif not ai_available():
            print("  claude コマンドが見つからないため AI 処理をスキップしました", file=sys.stderr)
        elif process(store, leads):
            rejudge_events(store, leads)
            check_japan_coverage(store)
    finally:
        store.save()
        leads.save()
    if not args.no_world:
        # 世界の主要ニュースは日本の出来事とは別のファイルに書く。失敗しても日本の出来事の更新は残す
        import world

        print("世界の主要ニュース")
        try:
            world.run(use_ai=not args.no_ai and ai_available())
        except Exception as e:
            print(f"  世界の主要ニュースの処理に失敗しました: {type(e).__name__}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
