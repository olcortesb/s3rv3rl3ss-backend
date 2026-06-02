"""Parse MiniStack services from GitHub README (bold service names in tables)."""

import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError

URL = "https://raw.githubusercontent.com/ministackorg/ministack/main/README.md"

# Sub-features of CloudFormation, not standalone services
EXCLUDE = {
    "Stack Operations", "Change Sets", "Exports", "Template Formats",
    "Intrinsic Functions", "Pseudo-Parameters", "Parameters",
    "Conditions", "Rollback", "Async Status",
}


def fetch_services():
    """Extract bold service names from Supported Services tables in README."""
    try:
        req = Request(URL, headers={"User-Agent": "s3rv3rl3ss-bot"})
        resp = urlopen(req, timeout=15)
        content = resp.read().decode("utf-8")
        idx = content.find("## Supported Services")
        if idx == -1:
            return None
        end = content.find("\n## ", idx + 10)
        section = content[idx:end] if end != -1 else content[idx:]
        rows = re.findall(r'^\|\s*\*\*([^*]+)\*\*', section, re.MULTILINE)
        services = [r.strip() for r in rows if r.strip() and r.strip() not in EXCLUDE]
        if services:
            print(f"[ministack] Scraped {len(services)} services from README")
            return services
    except (HTTPError, Exception) as e:
        print(f"[ministack] Error scraping services: {e}")
    return None
