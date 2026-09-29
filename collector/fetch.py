"""RSS から日本関連の記事を集める。

description（リード文）は日本関連かどうかの判定と AI への入力にだけ使う。
公開用の store.json には入れず、再判定のために collector/state/leads.json に2週間だけ置く。
"""

import calendar
import re
import socket
from datetime import datetime, timedelta, timezone

import html
import time
import urllib.parse
import urllib.request

import feedparser

# feedparser には時間制限の指定がないので、応答が止まったフィードで全体が止まらないようにする
socket.setdefaulttimeout(30)

# フィードには数か月前の記事が残っていることがあるので、古いものは取り込まない
MAX_AGE = timedelta(days=3)

USER_AGENT = "JapanLensBot/0.1 (+https://github.com/; headline aggregator)"

# 見出しかリード文にこれらが含まれる記事を候補にする。取りこぼしより拾いすぎを優先し、
# 無関係な記事は AI の段階で relevant=false にする。
JAPAN_PATTERN = re.compile(
    r"\b("
    r"Japan|Japanese|Japaner\w*|japanisch\w*|Tokyo|Tokio|Osaka|Kyoto|Okinawa|Hiroshima|Nagasaki|Yokohama|"
    r"Bank of Japan|BOJ|yen|Nikkei|Topix|JGBs?|Keidanren|"
    # 首相・閣僚・日銀総裁・主な政治家（見出しには名字だけで出ることが多い）
    r"Takaichi|Ishiba|Kishida|Motegi|Koizumi|Kihara|Katayama|Akazawa|Iwaya|Ueda|Koja|LDP|Komeito|"
    # 防衛・安全保障
    r"Self-Defen[cs]e Forces?|JSDF|SDF|Yonaguni|Ishigaki|"
    # 領土・歴史（中国・韓国・ロシア側の呼び方も含める）
    r"Senkaku|Diaoyu|Takeshima|Dokdo|Northern Territories|Kuril\w*|Ryukyu|Yasukuni|Nanjing Massacre|comfort women|"
    r"Fukushima|treated water|"
    # 地名（東京以外）
    r"Nagoya|Fukuoka|Sapporo|Kumamoto|Kyushu|Hokkaido|"
    r"Toyota|Sony|Nintendo|SoftBank|Honda|Nissan|Hitachi|Panasonic|Mitsubishi|Uniqlo|"
    r"Fast Retailing|Seven & i|Nippon Steel"
    r")\b"
    # 韓国語は語のすぐ後に助詞が付くので語の区切りを条件にしない（「日」は韓国紙で日本の略として使われる）
    r"|일본|도쿄|엔화|다카이치|이시바|기시다|자민당|닛케이|한일|일제강점|일제시대|독도|위안부|강제징용|후쿠시마|욱일기|日",
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


def _parse_news_sitemap(url):
    """Google News 形式のサイトマップを RSS と同じ形のエントリーにする（RSS がない媒体用）。"""
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=30
        ).read().decode("utf-8", "ignore")
    except Exception as e:
        return [], str(e)
    entries = []
    for block in re.findall(r"<url>(.*?)</url>", raw, re.S):
        loc = re.search(r"<loc>(.*?)</loc>", block)
        title = re.search(r"<news:title>(.*?)</news:title>", block, re.S)
        date = re.search(r"<news:publication_date>(.*?)</news:publication_date>", block)
        if not (loc and title and date):
            continue
        keywords = re.search(r"<news:keywords>(.*?)</news:keywords>", block, re.S)
        published = datetime.fromisoformat(date.group(1).strip().replace("Z", "+00:00"))
        entries.append({
            "link": html.unescape(loc.group(1).strip()),
            "title": html.unescape(re.sub(r"<!\[CDATA\[|\]\]>", "", title.group(1))).strip(),
            "summary": "",
            "published": published.astimezone(timezone.utc),
            "tags": [{"term": k.strip()} for k in (keywords.group(1).split(",") if keywords else []) if k.strip()],
        })
    return entries, None


GT_SEARCH = "https://search.globaltimes.cn/SearchCtrl"


def _parse_gt_search(query, pages):
    """Global Times のサイト内検索（新しい順）。サイトマップは直近の数十件しか載らず、
    日本関連の論評を取りこぼすため。search.globaltimes.cn に robots.txt はない（制限なし）。"""
    entries = []
    for page in range(1, pages + 1):
        url = f"{GT_SEARCH}?title={urllib.parse.quote(query)}&orderByTime=yes&page_no={page}"
        try:
            raw = urllib.request.urlopen(
                urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=30
            ).read().decode("utf-8", "ignore")
        except Exception as e:
            return entries, str(e)
        for link, title, date in re.findall(
            r'<a href="(https://www\.globaltimes\.cn/page/\d+/\d+\.shtml)"[^>]*><h4>(.*?)</h4></a>.*?<small>\s*(\d{4}/\d{2}/\d{2})',
            raw, re.S,
        ):
            # 検索結果には日付しかないので、北京時間の正午として扱う
            published = datetime.strptime(date + " 12:00 +0800", "%Y/%m/%d %H:%M %z").astimezone(timezone.utc)
            entries.append({"link": link, "title": html.unescape(re.sub(r"<[^>]+>", "", title)).strip(),
                            "summary": "", "published": published, "tags": []})
        time.sleep(1)
    return entries, None


def fetch_outlet(outlet, max_age=MAX_AGE, search_pages=2):
    """1媒体ぶんの日本関連記事を返す。同じ URL が複数フィードにあれば1件にまとめる。"""
    found = {}
    errors = []
    oldest = datetime.now(timezone.utc) - max_age
    for url in outlet["feeds"]:
        if url.startswith("gtsearch:"):
            entries, err = _parse_gt_search(url.split(":", 1)[1], search_pages)
            if err:
                errors.append(f"{url}: {err}")
        elif "sitemap" in url or url.endswith("googlenews.xml") or "latest-articles" in url:
            entries, err = _parse_news_sitemap(url)
            if err:
                errors.append(f"{url}: {err}")
        else:
            try:
                feed = feedparser.parse(url, agent=USER_AGENT)
            except Exception as e:  # 1つのフィードの失敗で全体を止めない
                errors.append(f"{url}: {type(e).__name__}: {e}")
                continue
            if feed.bozo and not feed.entries:
                errors.append(f"{url}: {feed.bozo_exception}")
                continue
            entries = feed.entries
        for entry in entries:
            link = entry.get("link")
            title = _clean(entry.get("title"))
            if not link or not title:
                continue
            published = entry["published"] if isinstance(entry.get("published"), datetime) else _published(entry)
            if published < oldest:
                continue
            description = _clean(entry.get("summary"))
            # 日本の媒体はほぼ全記事が日本の話題なので語で絞らない（AI が掲載対象かを判定する）
            if outlet.get("side") != "japan" and not JAPAN_PATTERN.search(f"{title} {description}"):
                continue
            found[link] = {
                "outlet_id": outlet["id"],
                "url": link,
                "title": title,
                "published_at": published.isoformat(),
                "kind": article_kind(link, title),
                "description": description,  # store.json には入れない。AI 入力用
                "tags": [t.get("term") for t in entry.get("tags", []) if t.get("term")][:8],  # 同上
            }
    return list(found.values()), errors
