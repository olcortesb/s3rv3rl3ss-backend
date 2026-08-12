import re
import feedparser

BLOG_FEED_URL = "https://azure.microsoft.com/en-us/blog/feed/"
AZURE_WEEKLY_FEED_URL = "https://azureweekly.info/rss.xml"
COSMOSDB_FEED_URL = "https://devblogs.microsoft.com/cosmosdb/feed/"
AZURE_SQL_FEED_URL = "https://devblogs.microsoft.com/azure-sql/feed/"
NEWS_LIMIT = 10

NEWS_KEYWORDS = {
    "azure-functions": ["azure functions", "functions", "serverless"],
    "container-apps": ["container apps", "aca"],
    "cosmos-db": ["cosmos db", "cosmosdb"],
    "service-bus": ["service bus"],
    "event-grid": ["event grid"],
    "event-hubs": ["event hubs", "eventhubs"],
    "logic-apps": ["logic apps"],
    "api-management": ["api management", "apim"],
    "blob-storage": ["blob storage", "azure storage"],
    "queue-storage": ["queue storage"],
    "signalr": ["signalr"],
    "static-web-apps": ["static web apps"],
    "aks": ["aks", "kubernetes", "azure kubernetes"],
    "azure-sql-serverless": ["azure sql", "sql database", "sql serverless"],
    "azure-ai-services": ["azure ai", "cognitive services", "azure openai", "openai"],
    "key-vault": ["key vault", "keyvault"],
    "notification-hubs": ["notification hubs"],
    "durable-functions": ["durable functions"],
    "stream-analytics": ["stream analytics"],
    "data-factory": ["data factory", "adf"],
    "synapse-serverless": ["synapse", "synapse analytics"],
    "communication-services": ["communication services", "acs"],
    "web-pubsub": ["web pubsub", "pubsub"],
    "azure-cdn": ["azure cdn", "content delivery"],
}

# Service-specific feeds
SERVICE_FEEDS = {
    "cosmos-db": COSMOSDB_FEED_URL,
    "azure-sql-serverless": AZURE_SQL_FEED_URL,
}

_feed_cache = {}


def _get_feed(url):
    if url in _feed_cache:
        return _feed_cache[url]
    try:
        feed = feedparser.parse(url)
        print(f"[azure-news] Fetched {len(feed.entries)} entries from {url}")
        _feed_cache[url] = feed
    except Exception as e:
        print(f"[azure-news] Error fetching {url}: {e}")
        _feed_cache[url] = feedparser.FeedParserDict(entries=[])
    return _feed_cache[url]


def _parse_date(entry):
    try:
        t = entry.get("published_parsed")
        if t:
            return f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d}"
    except Exception:
        pass
    pub = entry.get("published", "")
    return pub[:10] if len(pub) >= 10 else ""


def _extract_weekly_links(entry, keywords):
    """Extract individual links from Azure Weekly newsletter HTML summary."""
    results = []
    summary = entry.get("summary", "")
    date = _parse_date(entry)
    for match in re.finditer(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', summary):
        url, title = match.group(1), match.group(2).strip()
        if any(kw in title.lower() for kw in keywords):
            results.append({"date": date, "title": title, "url": url})
    return results


def fetch_news(service_id):
    keywords = NEWS_KEYWORDS.get(service_id)
    if not keywords:
        return []

    news = []
    seen_titles = set()

    def _add(items):
        for item in items:
            if item["title"] not in seen_titles and len(news) < NEWS_LIMIT:
                seen_titles.add(item["title"])
                news.append(item)

    # 1. Service-specific feed (CosmosDB, Azure SQL)
    if service_id in SERVICE_FEEDS:
        feed = _get_feed(SERVICE_FEEDS[service_id])
        _add([{"date": _parse_date(e), "title": e.get("title", ""), "url": e.get("link", "")} for e in feed.entries])

    # 2. Azure Weekly (50 entries, links extracted from HTML summary)
    if len(news) < NEWS_LIMIT:
        weekly = _get_feed(AZURE_WEEKLY_FEED_URL)
        for entry in weekly.entries:
            _add(_extract_weekly_links(entry, keywords))
            if len(news) >= NEWS_LIMIT:
                break

    # 3. Azure Blog (general announcements)
    if len(news) < NEWS_LIMIT:
        blog = _get_feed(BLOG_FEED_URL)
        _add([{"date": _parse_date(e), "title": e.get("title", ""), "url": e.get("link", "")} for e in blog.entries if any(kw in e.get("title", "").lower() for kw in keywords)])

    return news
