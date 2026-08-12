import feedparser

RELEASE_NOTES_FEED = "https://docs.stackit.cloud/release-notes/feed.xml"
NEWS_LIMIT = 10

NEWS_KEYWORDS = {
    "kubernetes-engine": ["ske", "kubernetes engine", "kubernetes"],
    "object-storage": ["object storage"],
    "postgresql-flex": ["postgresql flex", "postgresql"],
    "mongodb-flex": ["mongodb flex", "mongodb"],
    "mariadb": ["mariadb"],
    "redis": ["redis"],
    "key-value-store": ["key value store", "valkey"],
    "opensearch": ["opensearch"],
    "rabbitmq": ["rabbitmq"],
    "secrets-manager": ["secrets manager"],
    "kms": ["kms", "key management service"],
    "load-balancer": ["application load balancer", "alb", "load balancer"],
    "dns": ["dns"],
    "cdn": ["cdn", "content delivery network"],
    "vpn": ["vpn"],
    "logs": ["logs", "loki"],
    "observability": ["observability", "grafana", "alertmanager"],
    "ai-model-serving": ["ai model serving", "ai model"],
    "container-registry": ["container registry"],
    "server": ["server"],
    "cloud-foundry": ["cloud foundry"],
    "git": ["stackit git"],
    "pipelines": ["pipelines"],
}

_feed_cache = None


def _get_feed():
    global _feed_cache
    if _feed_cache is not None:
        return _feed_cache
    try:
        _feed_cache = feedparser.parse(RELEASE_NOTES_FEED)
        print(f"[stackit-news] Fetched {len(_feed_cache.entries)} entries")
    except Exception as e:
        print(f"[stackit-news] Error fetching feed: {e}")
        _feed_cache = feedparser.FeedParserDict(entries=[])
    return _feed_cache


def _parse_date(entry):
    try:
        t = entry.get("published_parsed")
        if t:
            return f"{t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d}"
    except Exception:
        pass
    pub = entry.get("published", "")
    return pub[:10] if len(pub) >= 10 else ""


def fetch_news(service_id):
    keywords = NEWS_KEYWORDS.get(service_id)
    if not keywords:
        return []

    feed = _get_feed()
    news = []
    seen = set()

    for entry in feed.entries:
        title = entry.get("title", "")
        if any(kw in title.lower() for kw in keywords):
            if title not in seen:
                seen.add(title)
                news.append({
                    "date": _parse_date(entry),
                    "title": title,
                    "url": entry.get("link", ""),
                })
        if len(news) >= NEWS_LIMIT:
            break

    return news
