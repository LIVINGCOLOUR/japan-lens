"""RSS から日本関連の記事を集める。

description（リード文）は日本関連かどうかの判定と AI への入力にだけ使う。
公開用の store.json には入れず、再判定のために collector/state/leads.json に2週間だけ置く。
"""

import calendar
import re
from datetime import datetime, timedelta, timezone

import feedparser

# フィードには数か月前の記事が残っていることがあるので、古いものは取り込まない
MAX_AGE = timedelta(days=3)

USER_AGENT = "JapanLensBot/0.1 (+https://github.com/; headline aggregator)"

# 見出しかリード文にこれらが含まれる記事を候補にする。取りこぼしより拾いすぎを優先し、
# 無関係な記事は AI の段階で relevant=false にする。
JAPAN_PATTERN = re.compile(
    r"\b("
    r"Japan|Japanese|Tokyo|Osaka|Kyoto|Okinawa|Hokkaido|Fukushima|Hiroshima|Nagasaki|Yokohama|"
    r"Bank of Japan|BOJ|yen|Nikkei|Takaichi|Ishiba|Kishida|LDP|Senkaku|"
    r"Toyota|Sony|Nintendo|SoftBank|Honda|Nissan|Hitachi|Panasonic|Mitsubishi|Uniqlo|"
    r"Fast Retailing|Seven & i|Nippon Steel"
    r")\b",
    re.IGNORECASE,
)

_TAG = re.compile(r"<[^>]+>")

# URL や見出しから記事の種類を見分ける。オピニオンは論調が出やすいので判定の手がかりにする
OPINION_URL = re.compile(r"/(opinion|opinions|commentary|editorial|editorials)/", re.IGNORECASE)
OPINION_TITLE = re.compile(r"^(opinion|analysis|commentary|editorial)\s*[:|]", re.IGNORECASE)


def article_kind(url, title):
    if OPINION_URL.search(url) or OPINION_TITLE.search(title):
        return "opinion"
    return "news"


def _clean(text):
    return _TAG.sub("", text or "").strip()


def _published(entry):
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime.fromtimestamp(calendar.timegm(parsed), tz=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_outlet(outlet):
    """1媒体ぶんの日本関連記事を返す。同じ URL が複数フィードにあれば1件にまとめる。"""
    found = {}
    errors = []
    oldest = datetime.now(timezone.utc) - MAX_AGE
    for url in outlet["feeds"]:
        feed = feedparser.parse(url, agent=USER_AGENT)
        if feed.bozo and not feed.entries:
            errors.append(f"{url}: {feed.bozo_exception}")
            continue
        for entry in feed.entries:
            link = entry.get("link")
            title = _clean(entry.get("title"))
            if not link or not title:
                continue
            published = _published(entry)
            if published < oldest:
                continue
            description = _clean(entry.get("summary"))
            if not JAPAN_PATTERN.search(f"{title} {description}"):
                continue
            found[link] = {
                "outlet_id": outlet["id"],
                "url": link,
                "title": title,
                "published_at": published.isoformat(),
                "kind": article_kind(link, title),
                "description": description,  # store.json には入れない。AI 入力用
                "tags": [t.term for t in entry.get("tags", []) if t.get("term")][:8],  # 同上
            }
    return list(found.values()), errors
