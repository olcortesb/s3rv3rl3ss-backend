"""Parse MiniStack services from ministack.org (JSON-LD featureList)."""

import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError

URL = "https://ministack.org/"


def fetch_services():
    """Extract service names from MiniStack JSON-LD featureList."""
    try:
        req = Request(URL, headers={"User-Agent": "s3rv3rl3ss-bot"})
        resp = urlopen(req, timeout=15)
        html = resp.read().decode("utf-8")
        match = re.search(r'"featureList"[^"]*"([^"]+)"', html)
        if match:
            services = [s.strip() for s in match.group(1).split(",") if s.strip()]
            print(f"[ministack] Scraped {len(services)} services")
            return services
    except (HTTPError, Exception) as e:
        print(f"[ministack] Error scraping services: {e}")
    return None
