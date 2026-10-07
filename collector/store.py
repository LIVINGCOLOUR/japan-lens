"""保存先: web/data/store.json

収集処理がこのファイルを更新し、GitHub Actions がコミットする。
Next.js はビルド時にこのファイルを読み込んで静的なページを作る。
"""

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

STORE_PATH = Path(__file__).resolve().parent.parent / "web" / "data" / "store.json"
# リード文とタグの置き場所。サイトには出さない内部用。判定し直すときの材料として2週間だけ残す
LEADS_PATH = Path(__file__).resolve().parent / "state" / "leads.json"
LEADS_KEEP_DAYS = 14
# 公開用の store.json に入れないフィールド
PRIVATE_FIELDS = ("description", "tags")
# 同じ媒体の見出しがこれ以上似ていて、配信日時が近ければ同じ記事とみなす
DUPLICATE_SIMILARITY = 0.75
DUPLICATE_HOURS = 72


def _now():
    return datetime.now(timezone.utc).isoformat()


def _norm(title):
    return " ".join(title.lower().split())


def _words(title):
    return set(re.findall(r"[a-z0-9]+", title.lower().replace("’", "'")))


def _similar(t1, t2):
    w1, w2 = _words(t1), _words(t2)
    if not w1 or not w2:
        return False
    # 片方の見出しがもう片方を含む（末尾に語句が足されただけ）場合も同じ記事とみなす
    return len(w1 & w2) / min(len(w1), len(w2)) >= DUPLICATE_SIMILARITY


def _hours_apart(iso1, iso2):
    return abs((datetime.fromisoformat(iso1) - datetime.fromisoformat(iso2)).total_seconds()) / 3600


class Leads:
    """記事の URL → リード文・タグ。公開しない。"""

    def __init__(self, path=LEADS_PATH):
        self.path = path
        self.data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def add(self, url, description, tags):
        if description or tags:
            self.data[url] = {"lead": description, "tags": tags, "saved_at": _now()}

    def get(self, url):
        return self.data.get(url, {})

    def save(self):
        since = _since(LEADS_KEEP_DAYS)
        self.data = {k: v for k, v in self.data.items() if v["saved_at"] >= since}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


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

    def find_duplicate(self, article):
        """同じ媒体の、見出しがほぼ同じで配信日時が近い記事を探す。"""
        for b in self.data["articles"]:
            if b["url"] == article["url"]:
                return b
            if (b["outlet_id"] == article["outlet_id"]
                    and _hours_apart(b["published_at"], article["published_at"]) <= DUPLICATE_HOURS
                    and _similar(b["title"], article["title"])):
                return b
        return None

    def add_articles(self, articles, leads=None):
        # 同じ記事が RSS と検索の両方から来たり、見出しが少し変わって再配信されたりするので重複を除く
        added = []
        for a in articles:
            if leads is not None:
                leads.add(a["url"], a.get("description", ""), a.get("tags", []))
            if self.find_duplicate(a):
                continue
            row = {k: v for k, v in a.items() if k not in PRIVATE_FIELDS}
            row.setdefault("kind", "news")
            row.update(id=str(uuid.uuid4()), fetched_at=_now(), event_id=None, summary_ja=None,
                       angle=None, tone=None, evidence=None, processed_at=None, relevant=None)
            self.data["articles"].append(row)
            added.append(row)
        return added

    def articles_of(self, event_id):
        return [a for a in self.data["articles"] if a["event_id"] == event_id and a["relevant"]]

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

    def create_event(self, title_ja, fact_ja, category, target, published_at):
        # 出来事の日時は処理した時刻ではなく、記事の配信日時に合わせる
        ev = {"id": str(uuid.uuid4()), "title_ja": title_ja, "fact_ja": fact_ja,
              "category": category, "target": target, "judged_count": 0,
              "first_seen": published_at, "updated_at": published_at}
        self.data["events"].append(ev)
        return ev["id"]

    def update_article(self, article_id, fields):
        for a in self.data["articles"]:
            if a["id"] == article_id:
                a.update(fields)
                return

    def set_judged(self, event_id, count, fields):
        for e in self.data["events"]:
            if e["id"] == event_id:
                e.update(judged_count=count, **fields)
                return

    def update_event(self, event_id, fields):
        for e in self.data["events"]:
            if e["id"] == event_id:
                e.update(fields)
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
