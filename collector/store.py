"""保存先: web/data/store.json

収集処理がこのファイルを更新し、GitHub Actions がコミットする。
Next.js はビルド時にこのファイルを読み込んで静的なページを作る。
"""

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent.parent / "web" / "data" / "store.json"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _norm(title):
    return " ".join(title.lower().split())


def _since(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


class Store:
    def __init__(self, path=STORE_PATH):
        self.path = path
        if path.exists():
            self.data = json.loads(path.read_text(encoding="utf-8"))
        else:
            self.data = {"outlets": [], "events": [], "articles": []}

    def upsert_outlets(self, outlets):
        self.data["outlets"] = outlets

    def add_articles(self, articles):
        # 同じ記事が RSS と検索の両方から来ることがあるので、URL と「媒体 + 見出し」の両方で重複を除く
        known = {a["url"] for a in self.data["articles"]}
        known_titles = {(a["outlet_id"], _norm(a["title"])) for a in self.data["articles"]}
        added = []
        for a in articles:
            if a["url"] in known or (a["outlet_id"], _norm(a["title"])) in known_titles:
                continue
            row = {k: v for k, v in a.items() if k != "description"}
            row.update(id=str(uuid.uuid4()), fetched_at=_now(), event_id=None,
                       summary_ja=None, tone=None, processed_at=None, relevant=None)
            self.data["articles"].append(row)
            added.append({**row, "description": a.get("description", "")})
            known.add(a["url"])
            known_titles.add((a["outlet_id"], _norm(a["title"])))
        return added

    def unprocessed_articles(self, limit):
        rows = [a for a in self.data["articles"] if a["processed_at"] is None]
        rows.sort(key=lambda a: a["published_at"])
        return rows[:limit]

    def recent_events(self, days):
        since = _since(days)
        events = []
        for e in self.data["events"]:
            if e["updated_at"] < since:
                continue
            titles = [a["title"] for a in self.data["articles"] if a["event_id"] == e["id"]]
            events.append({**e, "sample_titles": titles[:3]})
        return events

    def create_event(self, title_ja, fact_ja, category, published_at):
        # 出来事の日時は処理した時刻ではなく、記事の配信日時に合わせる
        ev = {"id": str(uuid.uuid4()), "title_ja": title_ja, "fact_ja": fact_ja,
              "category": category, "first_seen": published_at, "updated_at": published_at}
        self.data["events"].append(ev)
        return ev["id"]

    def update_article(self, article_id, fields):
        for a in self.data["articles"]:
            if a["id"] == article_id:
                a.update(fields)
                return

    def touch_event(self, event_id, published_at):
        for e in self.data["events"]:
            if e["id"] == event_id:
                e["updated_at"] = max(e["updated_at"], published_at)
                e["first_seen"] = min(e["first_seen"], published_at)
                return

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        tmp.replace(self.path)
