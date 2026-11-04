import re
import xml.etree.ElementTree as ET
from urllib.request import urlopen

WHATS_NEW_FEED = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
SECURITY_BULLETINS_FEED = "https://aws.amazon.com/security/security-bulletins/rss/feed/"
GCP_BULLETINS_URL = "https://docs.cloud.google.com/support/bulletins"
GCP_INCIDENTS_URL = "https://status.cloud.google.com/incidents.json"
NEWS_LIMIT = 20
SECURITY_LIMIT = 50

_MONTH_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
}


def _parse_rss_date(pub):
    try:
        parts = pub.split()
        months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                  'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
        return f"{parts[3]}-{months.get(parts[2], '01')}-{parts[1].zfill(2)}"
    except Exception:
        return ""


def _fetch_feed(url, keywords, limit, search_description=False):
    items = []
    try:
        with urlopen(url, timeout=10) as resp:
            root = ET.parse(resp).getroot()
        for item in root.iter('item'):
            title = item.findtext('title', '')
            if search_description:
                description = item.findtext('description', '')
                text = (title + " " + description).lower()
            else:
                text = title.lower()
            if keywords and not any(kw.lower() in text for kw in keywords):
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


def fetch_security_news():
    """Fetch AWS Security Bulletins RSS feed."""
    items = []
    try:
        with urlopen(SECURITY_BULLETINS_FEED, timeout=10) as resp:
            root = ET.parse(resp).getroot()
        for item in root.iter('item'):
            title = item.findtext('title', '')
            pub = item.findtext('pubDate', '')
            items.append({
                "date": _parse_rss_date(pub),
                "title": title,
                "url": item.findtext('link', ''),
                "tag": "security",
                "provider": "aws",
            })
            if len(items) >= SECURITY_LIMIT:
                break
    except Exception as e:
        print(f"[security] Error fetching feed: {e}")
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def fetch_gcp_security_bulletins():
    """Scrape GCP Support Security Bulletins page."""
    items = []
    try:
        import urllib.request
        req = urllib.request.Request(GCP_BULLETINS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')

        # Split on <h2 id="gcp-YYYY-NNN"> — each block contains one full bulletin
        blocks = re.split(r'(?=<h2[^>]+id="gcp-\d{4}-\d+")', html)
        seen = set()
        for block in blocks[:SECURITY_LIMIT * 2]:
            bid_m = re.search(r'id="(gcp-(\d{4})-(\d+))"', block)
            if not bid_m:
                continue
            bulletin_id = f"GCP-{bid_m.group(2)}-{bid_m.group(3)}"
            if bulletin_id in seen:
                continue
            seen.add(bulletin_id)

            # Date: <strong>Published:</strong> YYYY-MM-DD
            date_m = re.search(r'Published[^<]*</strong>\s*(\d{4}-\d{2}-\d{2})', block)
            if date_m:
                date_str = date_m.group(1)
            else:
                # fallback: year from bulletin id
                date_str = bid_m.group(2) + '-01-01'

            # Severity: first <td>High|Medium|Low|Critical</td> in the table
            sev_m = re.search(r'<td>\s*(Critical|High|Medium|Low|None)\s*</td>', block, re.IGNORECASE)
            severity = sev_m.group(1).lower() if sev_m else ''

            # CVEs (deduplicated)
            cves = list(dict.fromkeys(re.findall(r'CVE-\d{4}-\d+', block)))

            title = bulletin_id
            if cves:
                title += f" ({', '.join(cves[:3])}{'...' if len(cves) > 3 else ''})"

            items.append({
                "date": date_str,
                "title": title,
                "url": f"https://docs.cloud.google.com/support/bulletins#{bid_m.group(1)}",
                "tag": "security",
                "provider": "gcp",
                "severity": severity,
                "bulletin_id": bulletin_id,
            })
            if len(items) >= SECURITY_LIMIT:
                break
    except Exception as e:
        print(f"[gcp-security] Error scraping bulletins: {e}")
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def fetch_gcp_incidents():
    """Fetch GCP Status incidents (active + recent resolved)."""
    items = []
    try:
        import json
        with urlopen(GCP_INCIDENTS_URL, timeout=10) as resp:
            incidents = json.loads(resp.read().decode('utf-8'))
        for inc in incidents[:SECURITY_LIMIT]:
            begin = inc.get('begin', '')
            date_str = begin[:10] if begin else ''
            impact = inc.get('status_impact', '').replace('_', ' ').title()
            severity = inc.get('severity', '')
            services = ', '.join(
                p.get('title', '') for p in inc.get('affected_products', [])[:3]
            )
            title = inc.get('external_desc', '') or impact
            if services:
                title = f"[{services}] {title}"
            items.append({
                "date": date_str,
                "title": title[:200],
                "url": f"https://status.cloud.google.com/{inc.get('uri', '').lstrip('/')}",
                "tag": "incident",
                "provider": "gcp",
                "severity": severity,
                "status": inc.get('currently_affected', False) and not inc.get('end'),
            })
    except Exception as e:
        print(f"[gcp-incidents] Error fetching incidents: {e}")
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def fetch_news(keywords, blog_feeds=None):
    # 1. What's New feed (filtered by keywords in TITLE only)
    news = _fetch_feed(WHATS_NEW_FEED, keywords, NEWS_LIMIT, search_description=False)

    # 2. Blog feeds (filtered by keywords in title + description)
    if blog_feeds:
        for feed_url in blog_feeds:
            remaining = NEWS_LIMIT - len(news)
            if remaining <= 0:
                break
            blog_items = _fetch_feed(feed_url, keywords, remaining, search_description=True)
            news.extend(blog_items)

    # Deduplicate by title (normalized) and sort by date desc
    seen = set()
    unique = []
    for n in news:
        normalized = ' '.join(n["title"].split())
        if normalized not in seen:
            seen.add(normalized)
            n["title"] = normalized
            unique.append(n)
    unique.sort(key=lambda x: x["date"], reverse=True)

    return unique[:NEWS_LIMIT]
