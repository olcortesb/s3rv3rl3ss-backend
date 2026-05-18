import xml.etree.ElementTree as ET
from urllib.request import urlopen
import re

NEWS_LIMIT = 10

ATOM_NS = '{http://www.w3.org/2005/Atom}'

# GCP release notes feeds per service
RELEASE_FEEDS = {
    "cloud-run": "https://cloud.google.com/feeds/run-release-notes.xml",
    "cloud-run-functions": "https://cloud.google.com/feeds/functions-release-notes.xml",
    "firestore": "https://cloud.google.com/feeds/firestore-release-notes.xml",
    "bigquery": "https://cloud.google.com/feeds/bigquery-release-notes.xml",
    "cloud-pubsub": "https://cloud.google.com/feeds/pubsub-release-notes.xml",
    "cloud-tasks": "https://cloud.google.com/feeds/tasks-release-notes.xml",
    "cloud-scheduler": "https://cloud.google.com/feeds/scheduler-release-notes.xml",
    "eventarc": "https://cloud.google.com/feeds/eventarc-release-notes.xml",
    "cloud-storage": "https://cloud.google.com/feeds/storage-release-notes.xml",
    "workflows": "https://cloud.google.com/feeds/workflows-release-notes.xml",
    "api-gateway": "https://cloud.google.com/feeds/api-gateway-release-notes.xml",
    "gke": "https://cloud.google.com/feeds/kubernetes-engine-release-notes.xml",
    "cloud-spanner": "https://cloud.google.com/feeds/spanner-release-notes.xml",
    "cloud-run-jobs": "https://cloud.google.com/feeds/run-release-notes.xml",
    "memorystore": "https://cloud.google.com/feeds/memorystore-release-notes.xml",
    "secret-manager": "https://cloud.google.com/feeds/secret-manager-release-notes.xml",
    "cloud-build": "https://cloud.google.com/feeds/cloud-build-release-notes.xml",
    "vertex-ai": "https://cloud.google.com/feeds/vertex-ai-release-notes.xml",
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
        return []

    try:
        with urlopen(feed_url, timeout=10) as resp:
            root = ET.parse(resp).getroot()
        news = []
        for entry in root.findall(f'{ATOM_NS}entry'):
            title = entry.findtext(f'{ATOM_NS}title', '')
            updated = entry.findtext(f'{ATOM_NS}updated', '')
            link_el = entry.find(f'{ATOM_NS}link[@rel="alternate"]')
            url = link_el.get('href', '') if link_el is not None else ''
            content = entry.findtext(f'{ATOM_NS}content', '')
            summary = _clean_html(content) if content else title

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
