"""収集処理の入口。1日1回（日本時間の朝6時）実行する想定。

    python main.py              # 収集して AI 処理まで
    python main.py --no-ai      # 収集だけ（APIキーなしで動作確認するとき）
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from ai import available as ai_available
from fetch import fetch_outlet
from outlets import OUTLETS, public_outlet
from store import STORE_PATH, Store

BATCH_SIZE = 30
EVENT_WINDOW_DAYS = 7


def collect(store):
    store.upsert_outlets([public_outlet(o) for o in OUTLETS])
    added = []
    for outlet in OUTLETS:
        found, errors = fetch_outlet(outlet)
        for e in errors:
            print(f"  [{outlet['id']}] フィード取得エラー: {e}", file=sys.stderr)
        new = store.add_articles(found)
        print(f"  [{outlet['id']}] 日本関連 {len(found)} 件 / 新規 {len(new)} 件")
        added.extend(new)
    return added


def apply_result(store, batch, result, existing_ids):
    by_id = {a["id"]: a for a in batch}
    event_ids = {}
    for ev in result["new_events"]:
        event_ids[ev["key"]] = None  # 記事が付くまで作らない
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
        if ref in event_ids:
            if event_ids[ref] is None:
                ev = next(e for e in result["new_events"] if e["key"] == ref)
                event_ids[ref] = store.create_event(ev["title_ja"], ev["fact_ja"], ev["category"])
            event_id = event_ids[ref]
        elif ref in existing_ids:
            event_id = ref
        else:
            continue  # 出来事が決まらなかった記事は次回に再処理
        store.update_article(r["id"], {
            "relevant": True, "event_id": event_id, "summary_ja": r["summary_ja"],
            "tone": r["tone"], "processed_at": now,
        })
        store.touch_event(event_id)
        done += 1
    return done


def process(store, descriptions):
    from ai import AIError, classify

    names = {o["id"]: o["name"] for o in OUTLETS}
    total = 0
    seen = set()
    while True:
        batch = [a for a in store.unprocessed_articles(BATCH_SIZE) if a["id"] not in seen]
        if not batch:
            break
        seen.update(a["id"] for a in batch)
        for a in batch:
            a["description"] = descriptions.get(a["url"], "")
        events = store.recent_events(EVENT_WINDOW_DAYS)
        try:
            result = classify(batch, events, names)
        except AIError as e:
            print(f"  AI 処理を中断しました: {e}", file=sys.stderr)
            break
        total += apply_result(store, batch, result, {e["id"] for e in events})
    print(f"  AI 処理 {total} 件")


def main():
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-ai", action="store_true", help="収集だけ行い AI 処理をしない")
    args = parser.parse_args()

    store = Store()
    print(f"保存先: {STORE_PATH}")
    try:
        added = collect(store)
        if args.no_ai:
            print("  AI 処理はスキップしました (--no-ai)")
        elif not ai_available():
            print("  claude コマンドが見つからないため AI 処理をスキップしました", file=sys.stderr)
        else:
            process(store, {a["url"]: a.get("description", "") for a in added})
    finally:
        store.save()


if __name__ == "__main__":
    main()
