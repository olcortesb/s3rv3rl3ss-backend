import feedparser

BLOG_FEED_URL = "https://azure.microsoft.com/en-us/blog/feed/"
NEWS_LIMIT = 5

# Keywords por servicio para filtrar noticias del blog
NEWS_KEYWORDS = {
    "azure-functions": ["functions", "serverless"],
    "container-apps": ["container apps"],
    "cosmos-db": ["cosmos db", "cosmosdb"],
    "service-bus": ["service bus"],
    "event-grid": ["event grid"],
    "event-hubs": ["event hubs"],
    "logic-apps": ["logic apps"],
    "api-management": ["api management", "apim"],
    "blob-storage": ["blob storage", "azure storage"],
    "queue-storage": ["queue storage"],
    "signalr": ["signalr"],
    "static-web-apps": ["static web apps"],
    "aks": ["aks", "kubernetes"],
    "azure-sql-serverless": ["azure sql", "sql database"],
    "azure-ai-services": ["azure ai", "cognitive services", "azure openai"],
    "key-vault": ["key vault"],
    "notification-hubs": ["notification hubs"],
}

_feed_cache = None


def _get_feed():
    global _feed_cache
    if _feed_cache is not None:
        return _feed_cache
    try:
        _feed_cache = feedparser.parse(BLOG_FEED_URL)
        print(f"[azure-news] Fetched {len(_feed_cache.entries)} blog entries")
    except Exception as e:
        print(f"[azure-news] Error fetching blog feed: {e}")
        _feed_cache = feedparser.FeedParserDict(entries=[])
    return _feed_cache


def _parse_date(entry):
    pub = entry.get("published", "")
    try:
        # feedparser normalizes dates into published_parsed
        t = entry.get("published_parsed")
        if t:
            return f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d}"
    except Exception:
        pass
    return pub[:10] if len(pub) >= 10 else ""


def fetch_news(service_id):
    keywords = NEWS_KEYWORDS.get(service_id)
    if not keywords:
        return []

    feed = _get_feed()
    news = []

    for entry in feed.entries:
        title = entry.get("title", "")
        title_lower = title.lower()
        if any(kw in title_lower for kw in keywords):
            news.append({
                "date": _parse_date(entry),
                "title": title,
                "url": entry.get("link", ""),
            })
            if len(news) >= NEWS_LIMIT:
                break

    return news
