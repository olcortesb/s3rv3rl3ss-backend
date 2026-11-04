import xml.etree.ElementTree as ET
from urllib.request import urlopen
import re

NEWS_LIMIT = 10

ATOM_NS = '{http://www.w3.org/2005/Atom}'

# GCP release notes feeds per service
RELEASE_FEEDS = {
    "cloud-run": "https://cloud.google.com/feeds/run-release-notes.xml",
    "cloud-run-functions": "https://cloud.google.com/feeds/functions-release-notes.xml",
    "firestore": "https://cloud.google.com/feeds/cloud-firestore-release-notes.xml",
    "bigquery": "https://cloud.google.com/feeds/bigquery-release-notes.xml",
    "cloud-pubsub": "https://cloud.google.com/feeds/pubsub-release-notes.xml",
    "cloud-tasks": "https://cloud.google.com/feeds/cloud-tasks-release-notes.xml",
    "cloud-scheduler": "https://cloud.google.com/feeds/cloud-scheduler-release-notes.xml",
    "eventarc": "https://cloud.google.com/feeds/eventarc-release-notes.xml",
    "cloud-storage": "https://cloud.google.com/feeds/storage-release-notes.xml",
    "workflows": "https://cloud.google.com/feeds/workflows-release-notes.xml",
    "api-gateway": "https://cloud.google.com/feeds/apigateway-release-notes.xml",
    "gke": "https://cloud.google.com/feeds/kubernetes-engine-release-notes.xml",
    "cloud-spanner": "https://cloud.google.com/feeds/spanner-release-notes.xml",
    "cloud-run-jobs": "https://cloud.google.com/feeds/run-release-notes.xml",
    "memorystore": "https://cloud.google.com/feeds/memorystore-release-notes.xml",
    "secret-manager": "https://cloud.google.com/feeds/secret-manager-release-notes.xml",
    "cloud-build": "https://cloud.google.com/feeds/cloud-build-release-notes.xml",
    "vertex-ai": "https://cloud.google.com/feeds/vertex-ai-release-notes.xml",
    "dataflow": "https://cloud.google.com/feeds/dataflow-release-notes.xml",
    "dataproc-serverless": "https://cloud.google.com/feeds/dataproc-release-notes.xml",
}

# General GCP feed for services without specific feed
GENERAL_FEED = "https://cloud.google.com/feeds/gcp-release-notes.xml"

GCP_BULLETINS_URL = "https://docs.cloud.google.com/support/bulletins"
GCP_INCIDENTS_URL = "https://status.cloud.google.com/incidents.json"
SECURITY_LIMIT = 50

_MONTH_ES = {
    'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
    'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
    'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
}


def _parse_atom_date(updated):
    try:
        return updated[:10]
    except Exception:
        return ""


def _clean_html(text):
    return re.sub(r'<[^>]+>', '', text).strip()[:120]


def fetch_news(service_id):
    feed_url = RELEASE_FEEDS.get(service_id)
    if not feed_url:
        # Fallback to general feed filtered by service name
        feed_url = GENERAL_FEED

    try:
        with urlopen(feed_url, timeout=10) as resp:
            root = ET.parse(resp).getroot()
        news = []

        # If using general feed, filter by service_id keywords
        filter_keywords = None
        if feed_url == GENERAL_FEED:
            filter_keywords = service_id.replace("-", " ").split()

        for entry in root.findall(f'{ATOM_NS}entry'):
            title = entry.findtext(f'{ATOM_NS}title', '')
            updated = entry.findtext(f'{ATOM_NS}updated', '')
            link_el = entry.find(f'{ATOM_NS}link[@rel="alternate"]')
            url = link_el.get('href', '') if link_el is not None else ''
            content = entry.findtext(f'{ATOM_NS}content', '')
            summary = _clean_html(content) if content else title

            # Filter if using general feed
            if filter_keywords:
                text = (title + " " + summary).lower()
                if not any(kw in text for kw in filter_keywords):
                    continue

            news.append({
                "date": _parse_atom_date(updated),
                "title": summary if summary else title,
                "url": url,
            })
            if len(news) >= NEWS_LIMIT:
                break
        return news
    except Exception as e:
        print(f"[gcp-news] Error fetching {feed_url}: {e}")
        return []


def fetch_gcp_security_bulletins():
    """Scrape GCP Support Security Bulletins page."""
    items = []
    try:
        import urllib.request
        req = urllib.request.Request(GCP_BULLETINS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=15) as resp:
            html = resp.read().decode('utf-8', errors='replace')

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

            date_m = re.search(r'Published[^<]*</strong>\s*(\d{4}-\d{2}-\d{2})', block)
            date_str = date_m.group(1) if date_m else bid_m.group(2) + '-01-01'

            sev_m = re.search(r'<td>\s*(Critical|High|Medium|Low|None)\s*</td>', block, re.IGNORECASE)
            severity = sev_m.group(1).lower() if sev_m else ''

            cves = list(dict.fromkeys(re.findall(r'CVE-\d{4}-\d+', block)))
            title = bulletin_id
            if cves:
                title += f" ({', '.join(cves[:3])}{'...' if len(cves) > 3 else ''})"

            desc_m = re.search(r'<td>\s*<p>(.*?)</p>', block, re.DOTALL)
            description = re.sub(r'<[^>]+>', '', desc_m.group(1)).split() if desc_m else []
            description = ' '.join(description[:30]) if description else ''

            items.append({
                "date": date_str,
                "title": title,
                "description": description,
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
    import json
    items = []
    try:
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
