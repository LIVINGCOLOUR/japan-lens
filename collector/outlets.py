"""掲載媒体の設定。

lean は媒体選定のバランス確認用の内部データで、サイトには出さない。
公開用のデータ（web/data/store.json）には書き出さないこと。
"""

OUTLETS = [
    {
        "id": "nyt",
        "name": "The New York Times",
        "country_code": "US",
        "flag": "🇺🇸",
        "region": "US",
        "ownership": "民間",
        "homepage": "https://www.nytimes.com",
        "feeds": [
            "https://rss.nytimes.com/services/xml/rss/nyt/AsiaPacific.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            # オピニオン（社説・論説）。各社の見方がはっきり出るので論調判定の材料として重要
            "https://rss.nytimes.com/services/xml/rss/nyt/Opinion.xml",
        ],
        "lean": -1,
    },
    {
        "id": "wsj",
        "name": "The Wall Street Journal",
        "country_code": "US",
        "flag": "🇺🇸",
        "region": "US",
        "ownership": "民間",
        "homepage": "https://www.wsj.com",
        # 旧 feeds.a.dj.com は 2025-01 で更新停止。現行は feeds.content.dowjones.io
        "feeds": [
            "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
            "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
            "https://feeds.content.dowjones.io/public/rss/RSSOpinion",
        ],
        "lean": 1,
    },
    {
        "id": "bbc",
        "name": "BBC News",
        "country_code": "GB",
        "flag": "🇬🇧",
        "region": "GB",
        "ownership": "公共放送",
        "homepage": "https://www.bbc.com/news",
        "feeds": [
            "https://feeds.bbci.co.uk/news/world/asia/rss.xml",
            "https://feeds.bbci.co.uk/news/business/rss.xml",
        ],
        "lean": 0,
    },
    {
        "id": "cna",
        "name": "CNA",
        "country_code": "SG",
        "flag": "🇸🇬",
        "region": "SG",
        "ownership": "政府系",
        "homepage": "https://www.channelnewsasia.com",
        "feeds": [
            "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511",
        ],
        # 本文を読んで論調を判定する。robots.txt で AI を拒否していない媒体だけ True にすること
        # （NYT・BBC は Claude を名指しで拒否、WSJ は自動取得を全面拒否しているので False のまま）
        "read_body": True,
        "lean": None,
    },
]

OUTLETS += [
    {
        "id": "koreaherald",
        "name": "The Korea Herald",
        "country_code": "KR",
        "flag": "🇰🇷",
        "region": "KR",
        "ownership": "民間",
        "homepage": "https://www.koreaherald.com",
        "feeds": ["https://www.koreaherald.com/rss/newsAll"],
        "read_body": True,
        "lean": 1,
    },
    {
        "id": "scmp",
        "name": "South China Morning Post",
        "country_code": "HK",
        "flag": "🇭🇰",
        "region": "HK",
        "ownership": "民間",
        "homepage": "https://www.scmp.com",
        "feeds": ["https://www.scmp.com/rss/3/feed", "https://www.scmp.com/rss/91/feed"],
        # robots.txt は Claude を拒否していないが、記事ページは自動取得に 403 を返すので本文は読まない
        "read_body": False,
        "lean": 0,
    },
    {
        "id": "welt",
        "name": "Die Welt",
        "country_code": "DE",
        "flag": "🇩🇪",
        "region": "DE",
        "ownership": "民間",
        "homepage": "https://www.welt.de",
        "feeds": [
            "https://www.welt.de/feeds/section/politik/ausland.rss",
            "https://www.welt.de/feeds/section/wirtschaft.rss",
        ],
        "read_body": True,
        "lean": 1,
    },
    {
        "id": "taz",
        "name": "taz",
        "country_code": "DE",
        "flag": "🇩🇪",
        "region": "DE",
        "ownership": "協同組合",
        "homepage": "https://taz.de",
        "feeds": ["https://taz.de/rss.xml"],
        "read_body": True,
        "lean": -2,
    },
    {
        "id": "tagesschau",
        "name": "tagesschau",
        "country_code": "DE",
        "flag": "🇩🇪",
        "region": "DE",
        "ownership": "公共放送",
        "homepage": "https://www.tagesschau.de",
        "feeds": [
            "https://www.tagesschau.de/ausland/asien/index~rss2.xml",
            "https://www.tagesschau.de/wirtschaft/index~rss2.xml",
        ],
        # robots.txt が ClaudeBot を拒否しているので本文は読まない（見出しで判定）
        "read_body": False,
        "lean": 0,
    },
]

OUTLETS += [
    {
        "id": "globaltimes",
        "name": "Global Times",
        "country_code": "CN",
        "flag": "🇨🇳",
        "region": "CN",
        "ownership": "国営",
        "homepage": "https://www.globaltimes.cn",
        "feeds": ["https://www.globaltimes.cn/rss/outbrain.xml"],
        "read_body": True,
        "lean": None,
    },
    {
        "id": "focustaiwan",
        "name": "Focus Taiwan",
        "country_code": "TW",
        "flag": "🇹🇼",
        "region": "TW",
        "ownership": "政府系",
        "homepage": "https://focustaiwan.tw",
        "feeds": ["https://feeds.feedburner.com/rsscna/engnews/"],
        "read_body": True,
        "lean": None,
    },
    {
        "id": "toi",
        "name": "The Times of India",
        "country_code": "IN",
        "flag": "🇮🇳",
        "region": "IN",
        "ownership": "民間",
        "homepage": "https://timesofindia.indiatimes.com",
        "feeds": [
            "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
            "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        ],
        "read_body": True,
        "lean": 0,
    },
    {
        "id": "chosun",
        "name": "朝鮮日報",
        "country_code": "KR",
        "flag": "🇰🇷",
        "region": "KR",
        "ownership": "民間",
        "homepage": "https://www.chosun.com",
        "feeds": [
            "https://www.chosun.com/arc/outboundfeeds/rss/category/international/?outputType=xml",
            "https://www.chosun.com/arc/outboundfeeds/rss/category/politics/?outputType=xml",
            "https://www.chosun.com/arc/outboundfeeds/rss/category/economy/?outputType=xml",
        ],
        "read_body": True,
        "lean": 2,
    },
    {
        "id": "straitstimes",
        "name": "The Straits Times",
        "country_code": "SG",
        "flag": "🇸🇬",
        "region": "SG",
        "ownership": "民間",
        "homepage": "https://www.straitstimes.com",
        "feeds": [
            "https://www.straitstimes.com/news/asia/rss.xml",
            "https://www.straitstimes.com/news/world/rss.xml",
            "https://www.straitstimes.com/news/opinion/rss.xml",
        ],
        "read_body": True,
        "lean": None,
    },
    {
        "id": "jakartapost",
        "name": "The Jakarta Post",
        "country_code": "ID",
        "flag": "🇮🇩",
        "region": "ID",
        "ownership": "民間",
        "homepage": "https://www.thejakartapost.com",
        # RSS がないので公式のニュース用サイトマップ（直近の記事）を使う
        "feeds": ["https://www.thejakartapost.com/sitemap_news.xml"],
        "read_body": True,
        "lean": 0,
    },
]

PUBLIC_FIELDS = ("id", "name", "country_code", "flag", "region", "ownership", "homepage")


def public_outlet(outlet):
    return {k: outlet[k] for k in PUBLIC_FIELDS}
