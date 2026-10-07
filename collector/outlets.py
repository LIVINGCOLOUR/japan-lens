"""掲載媒体の設定。

side: "overseas"（海外の見方として比べる媒体。既定）か "japan"（日本の立場を示す媒体）。
日本側の媒体は論調の分布や「2社以上」の掲載条件には数えず、「日本の立場」をまとめる材料にだけ使う。

lean は媒体選定のバランス確認用の内部データで、サイトには出さない。
公開用のデータ（web/data/store.json）には書き出さないこと。
"""

# ドイツ語の媒体の Google News 検索。本文に「Japan」が出るだけの記事が多いので、見出しに含むものに絞る
DE_QUERY = "(intitle:Japan OR intitle:Japans OR intitle:Tokio OR intitle:japanische OR intitle:japanischen OR intitle:Takaichi)"

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
            "https://www.channelnewsasia.com/api/v1/sitemap-news-feed?_format=xml",
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
        # RSS は約1日分しか残らないので、2日分あるニュース用サイトマップも使う（以下同様）
        "feeds": ["https://www.koreaherald.com/rss/newsAll", "https://www.koreaherald.com/sitemap/latest-articles"],
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
            "https://www.welt.de/sitemaps/newssitemap/newssitemap.xml",
            # 部門別のフィードには日本の記事がほとんど流れないので、Google News のサイト内検索でも拾う（以下同様）
            f"gnews:{DE_QUERY} site:welt.de|de|DE",
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
        "feeds": ["https://taz.de/rss.xml", "https://taz.de/sitemap-google-news.xml", f"gnews:{DE_QUERY} site:taz.de|de|DE"],
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
            f"gnews:{DE_QUERY} site:tagesschau.de|de|DE",
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
        # rss/outbrain.xml は数か月前の記事しか載らないので、公式のニュース用サイトマップを使う
        "feeds": [
            "https://www.globaltimes.cn/sitemap.xml",
            # サイトマップは直近の数十件しか載らないので、サイト内検索（新しい順）でも日本関連を拾う
            "gtsearch:Japan",
            "gtsearch:Japanese",
            "gtsearch:Takaichi",
            "gtsearch:Takaichi's",  # 検索は語単位なので所有格も別に引く
            "gtsearch:Japan's",
            "gtsearch:Tokyo",
            "gtsearch:Okinawa",
            "gtsearch:Ryukyu",  # 中国側は沖縄を「琉球」と書くことが多い
            "gtsearch:Diaoyu",  # 尖閣の中国側の呼び方
            "gtsearch:Yasukuni",
            "gtsearch:militarism",  # 日本の防衛政策を批判する記事でよく使われる
            "gtsearch:Fukushima",
            "gtsearch:SDF",
        ],
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
        "feeds": ["https://feeds.feedburner.com/rsscna/engnews/", "https://focustaiwan.tw/GoogleNewsSitemap_fromRemote_cep2.xml"],
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
            "gnews:Japan site:timesofindia.indiatimes.com|en|IN",
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
            "https://www.straitstimes.com/googlenews.xml",
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

OUTLETS += [
    {
        "id": "cgtn",
        "name": "CGTN",
        "country_code": "CN",
        "flag": "🇨🇳",
        "region": "CN",
        "ownership": "国営",
        "homepage": "https://www.cgtn.com",
        "feeds": ["https://www.cgtn.com/sitemap_latestnews.xml"],
        # 記事ページ（news.cgtn.com）の robots.txt を確認できないので本文は読まない
        "read_body": False,
        "lean": None,
    },
]

OUTLETS += [
    {
        "id": "guardian",
        "name": "The Guardian",
        "country_code": "GB",
        "flag": "🇬🇧",
        "region": "GB",
        "ownership": "民間",
        "homepage": "https://www.theguardian.com",
        # 日本の記事だけを集めたフィード
        "feeds": ["https://www.theguardian.com/world/japan/rss"],
        "read_body": False,
        "lean": -1,
    },
    {
        "id": "sz",
        "name": "Süddeutsche Zeitung",
        "country_code": "DE",
        "flag": "🇩🇪",
        "region": "DE",
        "ownership": "民間",
        "homepage": "https://www.sueddeutsche.de",
        "feeds": [f"gnews:{DE_QUERY} site:sueddeutsche.de|de|DE"],
        "read_body": False,
        "lean": -1,
    },
    {
        "id": "faz",
        "name": "Frankfurter Allgemeine Zeitung",
        "country_code": "DE",
        "flag": "🇩🇪",
        "region": "DE",
        "ownership": "民間",
        "homepage": "https://www.faz.net",
        "feeds": [f"gnews:{DE_QUERY} site:faz.net|de|DE"],
        "read_body": False,
        "lean": 1,
    },
    {
        "id": "abc",
        "name": "ABC News (Australia)",
        "country_code": "AU",
        "flag": "🇦🇺",
        "region": "AU",
        "ownership": "公共放送",
        "homepage": "https://www.abc.net.au/news",
        # 公式の RSS は総合のものしかなく日本の記事がほとんど流れないので、Google News のサイト内検索を使う
        "feeds": ["gnews:Japan site:abc.net.au|en|AU"],
        "read_body": False,
        "lean": 0,
    },
]

OUTLETS += [
    {
        "id": "japantimes",
        "name": "The Japan Times",
        "country_code": "JP",
        "flag": "🇯🇵",
        "region": "JP",
        "ownership": "民間",
        "homepage": "https://www.japantimes.co.jp",
        "feeds": [
            "https://www.japantimes.co.jp/feed/",
            "https://www.japantimes.co.jp/business/feed/",
            "https://www.japantimes.co.jp/opinion/feed/",
        ],
        "side": "japan",
        "read_body": True,
        "lean": -1,
    },
    {
        "id": "japanforward",
        "name": "JAPAN Forward",
        "country_code": "JP",
        "flag": "🇯🇵",
        "region": "JP",
        "ownership": "民間（産経新聞系）",
        "homepage": "https://japan-forward.com",
        "feeds": ["https://japan-forward.com/feed/"],
        "side": "japan",
        "read_body": True,
        "lean": 2,
    },
]

for _o in OUTLETS:
    _o.setdefault("side", "overseas")

PUBLIC_FIELDS = ("id", "name", "country_code", "flag", "region", "ownership", "homepage", "side")
JAPAN_SIDE = {o["id"] for o in OUTLETS if o["side"] == "japan"}
# 国や政府が運営・出資する媒体。政府の見方を伝える材料として載せるが、「海外の見方」の論調の集計と
# 掲載条件では独立した媒体と同じには数えない（同じ国の政府系の媒体はまとめて1つと数える）
GOVERNMENT_OWNERSHIP = ("国営", "政府系")
GOVERNMENT = {o["id"] for o in OUTLETS if o["ownership"] in GOVERNMENT_OWNERSHIP}
COUNTRY = {o["id"]: o["country_code"] for o in OUTLETS}

# 日本の主要媒体。出来事ごとに、これらが報じたかを Google News の検索で確かめる。
# 論調の判定には使わず、見つかった記事の見出しとリンクだけを表示する
JAPAN_MAIN_OUTLETS = [
    {"name": "NHK", "domain": "news.web.nhk"},
    {"name": "朝日新聞", "domain": "asahi.com"},
    {"name": "読売新聞", "domain": "yomiuri.co.jp"},
    {"name": "毎日新聞", "domain": "mainichi.jp"},
    {"name": "産経新聞", "domain": "sankei.com"},
    {"name": "日本経済新聞", "domain": "nikkei.com"},
    {"name": "日本テレビ", "domain": "news.ntv.co.jp"},
    {"name": "TBS", "domain": "newsdig.tbs.co.jp"},
    {"name": "テレビ朝日", "domain": "news.tv-asahi.co.jp"},
    {"name": "フジテレビ", "domain": "fnn.jp"},
]


def public_outlet(outlet):
    return {k: outlet[k] for k in PUBLIC_FIELDS}
