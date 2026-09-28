"""収集処理の入口。1日1回（日本時間の朝6時）実行する想定。

    python main.py              # 収集して AI 処理まで
    python main.py --no-ai      # 収集だけ（AI を使わずに動作確認するとき）
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ai import available as ai_available
from fetch import fetch_outlet
from outlets import OUTLETS, public_outlet
from store import LEADS_PATH, STORE_PATH, Leads, Store

BATCH_SIZE = 30
EVENT_WINDOW_DAYS = 14
# 掲載条件（web/src/lib/rules.ts と同じ値にする）。条件を満たした出来事は記事を並べて判定し直す
MIN_ARTICLES = 3
MIN_OUTLETS = 2
# 掲載するカテゴリー（web/src/lib/rules.ts と同じ）。これ以外は判定し直さない
SHOWN_CATEGORIES = {"政治", "外交", "安全保障", "経済"}


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
            **_judgement(r), "processed_at": now,
        })
        store.touch_event(event_id, published)
        done += 1
    return done


def _with_leads(articles, leads):
    out = []
    for a in articles:
        lead = leads.get(a["url"])
        out.append({**a, "description": lead.get("lead", ""), "tags": lead.get("tags", [])})
    return out


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
            result = classify(_with_leads(batch, leads), events, names)
        except AIError as e:
            print(f"  AI 処理を中断しました: {e}", file=sys.stderr)
            return False
        total += apply_result(store, batch, result, {e["id"] for e in events})
        store.save()  # 途中で止まっても処理済みの分は残す
    print(f"  AI 処理 {total} 件")
    return True


def rejudge_events(store, leads):
    """掲載条件を満たした出来事のうち、前回の判定から記事が増えたものを並べて判定し直す。"""
    from ai import AIError, rejudge

    names = {o["id"]: o["name"] for o in OUTLETS}
    done = 0
    for ev in store.recent_events(EVENT_WINDOW_DAYS):
        if ev["category"] not in SHOWN_CATEGORIES:
            continue
        articles = store.articles_of(ev["id"])
        if len(articles) < MIN_ARTICLES or len({a["outlet_id"] for a in articles}) < MIN_OUTLETS:
            continue
        if ev.get("judged_count") == len(articles):
            continue
        try:
            result = rejudge(ev, _with_leads(articles, leads), names)
        except AIError as e:
            print(f"  判定し直しを中断しました: {e}", file=sys.stderr)
            break
        ids = {a["id"] for a in articles}
        for r in result["articles"]:
            if r["id"] in ids:
                store.update_article(r["id"], {"summary_ja": r["summary_ja"], **_judgement(r)})
        store.set_judged(ev["id"], len(articles), result["title_ja"], result["fact_ja"])
        store.save()
        done += 1
    print(f"  並べて判定し直した出来事 {done} 件")


def main():
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ai", action="store_true", help="収集だけ行い AI 処理をしない")
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
    finally:
        store.save()
        leads.save()


if __name__ == "__main__":
    main()
