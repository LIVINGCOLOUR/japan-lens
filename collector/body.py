"""記事の本文を取得する（論調判定の材料にだけ使い、保存も表示もしない）。

対象は outlets.py で read_body=True の媒体だけ。取得のたびに robots.txt を確認し、
許可されていない URL は読まない。サイトの負担にならないよう1件ごとに間を空ける。
"""

import html
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

# 媒体ごとの本文の取り出し方
_EXTRACTORS = {
    "cna": re.compile(r'<div class="text-long"[^>]*>(.*?)</div>', re.S),
}


def _allowed(url):
    host = urlparse(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser(f"https://{host}/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = None  # robots.txt を確認できなければ読まない
        _robots[host] = rp
    rp = _robots[host]
    return rp is not None and all(rp.can_fetch(agent, url) for agent in ROBOT_AGENTS)


def fetch_body(article):
    """本文を返す。対象外・拒否・取得失敗のときは空文字。"""
    outlet_id, url = article["outlet_id"], article["url"]
    if outlet_id not in _READ_BODY or outlet_id not in _EXTRACTORS:
        return ""
    if "news.google.com" in url or not _allowed(url):
        return ""
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=20
        ).read().decode("utf-8", "ignore")
    except Exception:
        return ""
    finally:
        time.sleep(PAUSE_SECONDS)
    paras = []
    for block in _EXTRACTORS[outlet_id].findall(raw):
        for p in re.findall(r"<p[^>]*>(.*?)</p>", block, re.S):
            text = html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
            if len(text) > 40:
                paras.append(text)
    return "\n".join(paras)[:MAX_CHARS]
