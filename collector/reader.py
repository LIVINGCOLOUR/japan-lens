"""読者が「AIで本文を読む」で予約した記事を、毎日の収集でまとめて読む。

サイトのボタンを押しても、その場では AI を呼ばない（API の従量課金を使わないため）。
Worker（web/worker/index.ts）が予約を記録し、この処理が翌朝 `claude -p`（サブスクリプション）でまとめて読む。
結果は web/data/readings.json に書き、サイトのビルド時に取り込む。

人に頼まれて読む記事なので、robots.txt は Claude-User で確かめる（body.py の fetch_requested）。
"""

import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from body import fetch_requested
from outlets import OUTLETS

QUEUE_URL = "https://japan-lens.mon-m.workers.dev/api/read-queue"
READINGS_PATH = Path(__file__).resolve().parent.parent / "web" / "data" / "readings.json"
# 1回の実行で読む記事の数の上限（サブスクリプションの利用枠を使いすぎないように）。残りは次回に回す
MAX_PER_RUN = 40
# 1回の claude -p に渡す記事の数
BATCH_SIZE = 8
# 読めなかった記事（robots.txt・有料記事など）は、この日数が過ぎて予約されたらもう一度試す
RETRY_DAYS = 7


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_readings():
    """記事の id → 読んだ結果（{"status": "ok", "summary_ja", "angle", "tone", "evidence", "read_at"}
    または {"status": "blocked" | "unavailable", "message", "read_at"}）。"""
    if READINGS_PATH.exists():
        return json.loads(READINGS_PATH.read_text(encoding="utf-8"))
    return {}


def ok_readings():
    """本文を読めた記事だけ（判定し直しの材料にする）。"""
    return {k: v for k, v in load_readings().items() if v.get("status") == "ok"}


def _save(readings):
    READINGS_PATH.write_text(json.dumps(readings, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def _queue():
    try:
        req = urllib.request.Request(QUEUE_URL, headers={"User-Agent": "JapanLensCollector/0.1"})
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read().decode("utf-8"))
    except Exception as e:
        print(f"  読者の予約を取得できませんでした: {e}", file=sys.stderr)
        return {}


def _due(reading):
    if reading is None:
        return True
    if reading.get("status") == "ok":
        return False
    since = (datetime.now(timezone.utc) - timedelta(days=RETRY_DAYS)).isoformat()
    return reading.get("read_at", "") < since


def read_reserved(store):
    """予約された記事を読み、読んだ件数を返す。"""
    from ai import AIError, read_requested

    readings = load_readings()
    queue = _queue()
    articles = {a["id"]: a for a in store.data["articles"]}
    events = {e["id"]: e for e in store.data["events"]}
    names = {o["id"]: o["name"] for o in OUTLETS}
    # 古い予約から読む
    ids = [i for i, _ in sorted(queue.items(), key=lambda x: x[1]) if i in articles and _due(readings.get(i))]
    ids = ids[:MAX_PER_RUN]
    if not ids:
        print("  読者が予約した記事はありません")
        return 0

    material = []
    for i in ids:
        a = articles[i]
        name = names.get(a["outlet_id"], a["outlet_id"])
        text, failure = fetch_requested(a, name)
        if failure:
            readings[i] = {**failure, "read_at": _now()}
            continue
        ev = events.get(a.get("event_id")) or {}
        material.append({"id": i, "outlet": name, "event": ev.get("title_ja", ""),
                         "target": ev.get("target", ""), "article_text": text})

    done = 0
    for start in range(0, len(material), BATCH_SIZE):
        batch = material[start:start + BATCH_SIZE]
        try:
            result = read_requested(batch)
        except AIError as e:
            # 予約は Worker に残っているので、次回また読む
            print(f"  予約された記事の読み込みを中断しました: {e}", file=sys.stderr)
            break
        asked = {m["id"] for m in batch}
        for r in result["articles"]:
            if r["id"] in asked:
                readings[r["id"]] = {"status": "ok", **{k: r[k] for k in ("summary_ja", "angle", "tone", "evidence")},
                                     "read_at": _now()}
                done += 1
    _save(readings)
    print(f"  読者が予約した記事 {len(ids)} 件のうち、本文を読めた記事 {done} 件")
    return done
