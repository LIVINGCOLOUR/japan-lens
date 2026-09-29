"""過去の記事をさかのぼって取り込む（1回だけ使う想定）。

RSS には直近数日ぶんしか残っていないので、Google News の検索 RSS を媒体のドメインで絞って使う。
期間を2日ずつに区切って検索する（1回の検索は最大100件のため）。

    python backfill.py --days 14          # 取り込み + AI 処理
    python backfill.py --days 14 --no-ai  # 取り込みだけ

リンクは Google News 経由の URL になる（開くと各媒体の記事に移動する）。
"""

import argparse
import calendar
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote_plus

import feedparser
from dotenv import load_dotenv

from ai import available as ai_available
from fetch import JAPAN_PATTERN, USER_AGENT, article_kind
from main import process, rejudge_events
from outlets import OUTLETS, public_outlet
from store import STORE_PATH, Leads, Store

DOMAINS = {
    "nyt": "nytimes.com",
    "wsj": "wsj.com",
    "bbc": "bbc.com",
    "cna": "channelnewsasia.com",
}
WINDOW_DAYS = 2
PAUSE_SECONDS = 1.5


def _search_url(domain, start, end):
    q = f"Japan site:{domain} after:{start:%Y-%m-%d} before:{end:%Y-%m-%d}"
    return f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"


# Google News の見出しは末尾に " - 媒体名" が付く。媒体内のブランド名が重なることもある
# （例: "... - The Athletic - The New York Times"）
KNOWN_SUFFIXES = ["The New York Times", "The Athletic", "Wirecutter", "The Wall Street Journal", "WSJ",
                  "Barron's", "MarketWatch", "BBC", "BBC News", "CNA", "CNA Lifestyle", "CNA Luxury"]


def _strip_source(title, source):
    suffixes = [source] + KNOWN_SUFFIXES if source else KNOWN_SUFFIXES
    changed = True
    while changed:
        changed = False
        for name in suffixes:
            if title.endswith(f" - {name}"):
                title = title[: -len(name) - 3].rstrip()
                changed = True
    return title


def search_outlet(outlet_id, days):
    domain = DOMAINS[outlet_id]
    today = datetime.now(timezone.utc).date()
    found = {}
    start = today - timedelta(days=days)
    while start <= today:
        end = start + timedelta(days=WINDOW_DAYS)
        feed = feedparser.parse(_search_url(domain, start, end), agent=USER_AGENT)
        for entry in feed.entries:
            source = entry.get("source", {})
            if domain not in source.get("href", ""):
                continue
            title = _strip_source(entry.get("title", "").strip(), source.get("title", ""))
            if not title or not JAPAN_PATTERN.search(title) or not entry.get("published_parsed"):
                continue
            published = datetime.fromtimestamp(calendar.timegm(entry.published_parsed), tz=timezone.utc)
            found[entry.link] = {
                "outlet_id": outlet_id,
                "url": entry.link,
                "title": title,
                "published_at": published.isoformat(),
                "kind": article_kind(entry.link, title),
            }
        start = end
        time.sleep(PAUSE_SECONDS)
    return list(found.values())


def main():
    # 使用停止（2026-09-29）: news.google.com の robots.txt は /rss/ を含むほぼ全パスへの自動アクセスを
    # 禁止しており、Claude も名指しで拒否している。確認漏れのまま過去分の取り込みに使っていた。
    # 過去分が必要なときは、各媒体が自動取得を認めている手段（公式 RSS・サイトマップ・API）で行うこと。
    raise SystemExit("backfill.py は使用停止です（Google News の robots.txt が自動アクセスを禁止しているため）。")
    load_dotenv(Path(__file__).with_name(".env"))
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--no-ai", action="store_true")
    args = parser.parse_args()

    store = Store()
    leads = Leads()
    print(f"保存先: {STORE_PATH}")
    try:
        store.upsert_outlets([public_outlet(o) for o in OUTLETS])
        for outlet in OUTLETS:
            found = search_outlet(outlet["id"], args.days)
            new = store.add_articles(found)
            print(f"  [{outlet['id']}] 見出しに日本関連の語 {len(found)} 件 / 新規 {len(new)} 件")
        store.save()
        if args.no_ai:
            print("  AI 処理はスキップしました (--no-ai)")
        elif not ai_available():
            print("  claude コマンドが見つからないため AI 処理をスキップしました")
        elif process(store, leads):
            rejudge_events(store, leads)
    finally:
        store.save()


if __name__ == "__main__":
    main()
