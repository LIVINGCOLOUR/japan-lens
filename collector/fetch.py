"""RSS から日本関連の記事を集める。

description（リード文）は日本関連かどうかの判定と AI への入力にだけ使い、保存しない。
"""

import calendar
import re
from datetime import datetime, timezone

import feedparser

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
            description = _clean(entry.get("summary"))
            if not JAPAN_PATTERN.search(f"{title} {description}"):
                continue
            found[link] = {
                "outlet_id": outlet["id"],
                "url": link,
                "title": title,
                "published_at": _published(entry).isoformat(),
                "description": description,  # 保存しない。AI 入力用
            }
    return list(found.values()), errors
