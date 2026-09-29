"""記事の本文を取得する（論調判定の材料にだけ使い、保存も表示もしない）。

対象は outlets.py で read_body=True の媒体だけ。取得のたびに robots.txt を確認し、
許可されていない URL は読まない。サイトの負担にならないよう1件ごとに間を空ける。
"""

import html
import json
import re
import time
import urllib.request
import urllib.robotparser
from urllib.parse import urlparse

from outlets import OUTLETS

USER_AGENT = "JapanLensBot/0.1 (overseas-coverage comparison site; reads article text only to classify tone)"
# robots.txt の確認では、Claude として読んでよいかも見る
ROBOT_AGENTS = [USER_AGENT, "Claude-User", "ClaudeBot"]
MAX_CHARS = 6000
PAUSE_SECONDS = 1.0

_READ_BODY = {o["id"] for o in OUTLETS if o.get("read_body")}
_robots = {}

# 本文の取り出し方。多くのサイトは構造化データ（JSON-LD の articleBody）か
# itemprop="articleBody" を持っているので、まずそれを使い、なければ媒体ごとの目印を使う
_SITE_BLOCKS = {
    "cna": re.compile(r'<div class="text-long"[^>]*>(.*?)</div>', re.S),
}


def _text(fragment):
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def _paragraphs(fragment):
    return [t for t in (_text(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", fragment, re.S)) if len(t) > 30]


def _from_json_ld(raw):
    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', raw, re.S):
        try:
            stack = [json.loads(block.strip())]
        except ValueError:
            continue
        while stack:
            x = stack.pop()
            if isinstance(x, list):
                stack.extend(x)
            elif isinstance(x, dict):
                body = x.get("articleBody")
                if isinstance(body, str) and len(body) > 200:
                    return html.unescape(body).strip()
                stack.extend(x.values())
    return ""


def _from_itemprop(raw):
    i = raw.find('itemprop="articleBody"')
    if i < 0:
        return ""
    end = raw.find("</article>", i)
    return "\n".join(_paragraphs(raw[i: end if end > 0 else i + 30000]))


def _extract(outlet_id, raw):
    if outlet_id in _SITE_BLOCKS:
        paras = [p for block in _SITE_BLOCKS[outlet_id].findall(raw) for p in _paragraphs(block)]
        if paras:
            return "\n".join(paras)
    return _from_json_ld(raw) or _from_itemprop(raw)


def _allowed(url):
    host = urlparse(url).netloc
    if host not in _robots:
        # 標準の rp.read() は Python の既定の名乗りで取りに行き、403 だと全拒否扱いになるので自前で取る
        rp = urllib.robotparser.RobotFileParser()
        try:
            text = urllib.request.urlopen(
                urllib.request.Request(f"https://{host}/robots.txt", headers={"User-Agent": USER_AGENT}),
                timeout=20,
            ).read().decode("utf-8", "ignore")
            rp.parse(text.splitlines())
        except Exception:
            rp = None  # robots.txt を確認できなければ読まない
        _robots[host] = rp
    rp = _robots[host]
    return rp is not None and all(rp.can_fetch(agent, url) for agent in ROBOT_AGENTS)


def fetch_body(article):
    """本文を返す。対象外・拒否・取得失敗のときは空文字。"""
    outlet_id, url = article["outlet_id"], article["url"]
    if outlet_id not in _READ_BODY:
        return ""
    if "news.google.com" in url or not _allowed(url):
        return ""
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=20
        ).read().decode("utf-8", "ignore")
    except Exception:
        return ""  # 403 などで断られたら読まない（回避しない）
    finally:
        time.sleep(PAUSE_SECONDS)
    return _extract(outlet_id, raw)[:MAX_CHARS]
