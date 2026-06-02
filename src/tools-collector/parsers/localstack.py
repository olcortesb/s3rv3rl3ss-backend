"""Parse LocalStack services from docs.localstack.cloud/aws/services/"""

import re
from urllib.request import urlopen, Request
from urllib.error import HTTPError

URL = "https://docs.localstack.cloud/aws/services/"


def fetch_services():
    """Extract service names from LocalStack docs page (service-box-title class)."""
    try:
        req = Request(URL, headers={"User-Agent": "s3rv3rl3ss-bot"})
        resp = urlopen(req, timeout=15)
        html = resp.read().decode("utf-8")
        services = re.findall(r'class="service-box-title">([^<]+)<', html)
        if services:
            print(f"[localstack] Scraped {len(services)} services")
            return services
    except (HTTPError, Exception) as e:
        print(f"[localstack] Error scraping services: {e}")
    return None
