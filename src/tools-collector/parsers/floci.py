"""Parse Floci services from floci.io/floci/services/ (sidebar nav links)."""

import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError

URL = "https://floci.io/floci/services/"

EXCLUDE = {"Overview", "Services", "Service Matrix", "Common Setup"}


def fetch_services():
    """Extract service names from Floci docs sidebar navigation."""
    try:
        req = Request(URL, headers={"User-Agent": "s3rv3rl3ss-bot"})
        resp = urlopen(req, timeout=15)
        html = resp.read().decode("utf-8")
        # Service names are in md-ellipsis spans within nav links
        matches = re.findall(
            r'class="md-nav__link"[^>]*>.*?<span[^>]*class="md-ellipsis"[^>]*>\s*(?:<[^>]+>\s*)*([^<]+)',
            html,
            re.DOTALL,
        )
        seen = set()
        services = []
        for name in matches:
            name = name.strip()
            if name and name not in seen and name not in EXCLUDE:
                seen.add(name)
                services.append(name)
        if services:
            print(f"[floci] Scraped {len(services)} services")
            return services
    except (HTTPError, Exception) as e:
        print(f"[floci] Error scraping services: {e}")
    return None
