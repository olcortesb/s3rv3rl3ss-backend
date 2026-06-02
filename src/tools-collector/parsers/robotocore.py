"""Parse RobotoCore services from GitHub README (Native providers markdown table)."""

import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError

URL = "https://raw.githubusercontent.com/robotocore/robotocore/main/README.md"


def fetch_services():
    """Extract service names from RobotoCore README Native providers table."""
    try:
        req = Request(URL, headers={"User-Agent": "s3rv3rl3ss-bot"})
        resp = urlopen(req, timeout=15)
        content = resp.read().decode("utf-8")
        idx = content.find("Native providers")
        if idx == -1:
            return None
        chunk = content[idx:idx + 5000]
        rows = re.findall(r"^\|\s*([^|]+?)\s*\|", chunk, re.MULTILINE)
        services = [
            r.strip()
            for r in rows
            if r.strip() and not r.strip().startswith("-") and r.strip() != "Service"
        ]
        if services:
            print(f"[robotocore] Scraped {len(services)} services")
            return services
    except (HTTPError, Exception) as e:
        print(f"[robotocore] Error scraping services: {e}")
    return None


def parse_health_services(health_data):
    """Extract service names from health endpoint response with type info."""
    if not health_data or "services" not in health_data:
        return None
    services = health_data["services"]
    native = [k for k, v in services.items() if v.get("type") == "native"]
    moto = [k for k, v in services.items() if v.get("type") == "moto"]
    all_services = list(services.keys())
    if all_services:
        print(f"[robotocore] Got {len(all_services)} services from health ({len(native)} native, {len(moto)} moto)")
        return {"services": all_services, "native": native, "moto": moto}
    return None
