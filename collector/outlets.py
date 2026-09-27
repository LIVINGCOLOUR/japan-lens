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
        "lean": None,
    },
]

PUBLIC_FIELDS = ("id", "name", "country_code", "flag", "region", "ownership", "homepage")


def public_outlet(outlet):
    return {k: outlet[k] for k in PUBLIC_FIELDS}
