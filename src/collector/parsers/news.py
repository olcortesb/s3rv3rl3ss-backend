import xml.etree.ElementTree as ET
from urllib.request import urlopen

WHATS_NEW_FEED = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
NEWS_LIMIT = 10


def _parse_rss_date(pub):
    try:
        parts = pub.split()
        months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                  'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
        return f"{parts[3]}-{months.get(parts[2], '01')}-{parts[1].zfill(2)}"
    except Exception:
        return ""


def _fetch_feed(url, keywords, limit):
    items = []
    try:
        with urlopen(url, timeout=10) as resp:
            root = ET.parse(resp).getroot()
        for item in root.iter('item'):
            title = item.findtext('title', '')
            if keywords and not any(kw.lower() in title.lower() for kw in keywords):
                continue
            pub = item.findtext('pubDate', '')
            items.append({
                "date": _parse_rss_date(pub),
                "title": title,
                "url": item.findtext('link', ''),
            })
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"[news] Error fetching {url}: {e}")
    return items


def fetch_news(keywords, blog_feeds=None):
    # 1. What's New feed (filtered by keywords)
    news = _fetch_feed(WHATS_NEW_FEED, keywords, NEWS_LIMIT)

    # 2. Blog feeds (filtered by keywords)
    if blog_feeds:
        for feed_url in blog_feeds:
            remaining = NEWS_LIMIT - len(news)
            if remaining <= 0:
                break
            blog_items = _fetch_feed(feed_url, keywords, remaining)
            news.extend(blog_items)

    # Deduplicate by title and sort by date desc
    seen = set()
    unique = []
    for n in news:
        if n["title"] not in seen:
            seen.add(n["title"])
            unique.append(n)
    unique.sort(key=lambda x: x["date"], reverse=True)

    return unique[:NEWS_LIMIT]
