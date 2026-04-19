import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import date
from urllib.request import urlopen

import boto3

from services import SERVICES

s3 = boto3.client('s3')
sq = boto3.client('service-quotas')

BUCKET = os.environ['BUCKET_NAME']
S3_KEY = os.environ['S3_KEY']

NEWS_FEED_URL = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"
RUNTIMES_URL = "https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.md"
NEWS_LIMIT = 5


def fetch_runtimes():
    try:
        with urlopen(RUNTIMES_URL, timeout=10) as resp:
            content = resp.read().decode('utf-8')
        runtimes = []
        in_table = False
        today = date.today()
        for line in content.split('\n'):
            if '| Name | Identifier |' in line:
                in_table = True
                continue
            if in_table and line.startswith('| ---'):
                continue
            if in_table and line.startswith('|'):
                cols = [c.strip() for c in line.split('|')[1:-1]]
                if len(cols) >= 4:
                    name = cols[0].strip()
                    identifier = cols[1].replace('`', '').strip()
                    eol_str = cols[3].strip()
                    if not name or not identifier:
                        continue
                    # Parse EOL date
                    eol_date = None
                    try:
                        parts = eol_str.replace(',', '').split()
                        months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                                  'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
                        if len(parts) == 3 and parts[0] in months:
                            eol_date = f"{parts[2]}-{months[parts[0]]}-{parts[1].zfill(2)}"
                    except Exception:
                        pass
                    status = 'deprecated' if eol_date and eol_date < today.isoformat() else 'active'
                    entry = {"name": name, "identifier": identifier, "status": status}
                    if eol_date:
                        entry["eol"] = eol_date
                    runtimes.append(entry)
            elif in_table and not line.startswith('|'):
                break
        print(f"[runtimes] Got {len(runtimes)} runtimes from docs")
        return runtimes
    except Exception as e:
        print(f"[runtimes] Error fetching: {e}")
        return None

UNIT_MAP = {
    "None": "", "Count": "",
    "Microsecond": "μs", "Millisecond": "ms", "Second": "s",
    "Minute": "min", "Hour": "h", "Day": "d",
    "Kilobyte": "KB", "Kilobytes": "KB",
    "Megabyte": "MB", "Megabytes": "MB",
    "Gigabyte": "GB", "Gigabytes": "GB",
    "Terabyte": "TB", "Terabytes": "TB",
    "Megabytes/Second": "MB/s", "Gigabytes/Second": "GB/s",
}


def format_value(value, unit):
    if isinstance(value, float) and value == int(value):
        value = int(value)
    suffix = UNIT_MAP.get(unit, unit) if unit else ""
    return f"{value} {suffix}".strip() if suffix else str(value)


def list_quotas(service_code):
    limits = []
    try:
        paginator = sq.get_paginator('list_service_quotas')
        for page in paginator.paginate(ServiceCode=service_code):
            for q in page.get('Quotas', []):
                value = q.get('Value', 'N/A')
                unit = q.get('Unit', '')
                entry = {
                    "name": q['QuotaName'],
                    "value": format_value(value, unit),
                }
                if q.get('Description'):
                    entry["description"] = q['Description']
                if unit and unit != 'None':
                    entry["unit"] = unit
                limits.append(entry)
        if not limits:
            paginator = sq.get_paginator('list_aws_default_service_quotas')
            for page in paginator.paginate(ServiceCode=service_code):
                for q in page.get('Quotas', []):
                    value = q.get('Value', 'N/A')
                    unit = q.get('Unit', '')
                    entry = {
                        "name": q['QuotaName'],
                        "value": format_value(value, unit),
                    }
                    if q.get('Description'):
                        entry["description"] = q['Description']
                    if unit and unit != 'None':
                        entry["unit"] = unit
                    limits.append(entry)
        print(f"[{service_code}] Got {len(limits)} quotas from API")
    except Exception as e:
        print(f"[{service_code}] Error fetching quotas: {e}")
    return limits


def parse_rss_date(pub):
    try:
        parts = pub.split()
        months = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
                  'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
        return f"{parts[3]}-{months.get(parts[2], '01')}"
    except Exception:
        return ""


def fetch_news(keywords):
    try:
        with urlopen(NEWS_FEED_URL, timeout=10) as resp:
            root = ET.parse(resp).getroot()
        news = []
        for item in root.iter('item'):
            title = item.findtext('title', '')
            title_lower = title.lower()
            if any(kw.lower() in title_lower for kw in keywords):
                pub = item.findtext('pubDate', '')
                date_str = parse_rss_date(pub)
                news.append({"date": date_str, "title": title, "url": item.findtext('link', '')})
                if len(news) >= NEWS_LIMIT:
                    break
        return news
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


def build_service(svc, live_runtimes=None):
    entry = {
        "id": svc["id"],
        "enabled": True,
        "name": svc["name"],
        "category": svc["category"],
        "description": svc["description"],
        "useCases": svc["useCases"],
        "pricing": svc["pricing"],
        "url": svc["url"],
        "icon": svc["icon"],
    }

    quotas = list_quotas(svc["service_code"])
    quota_names = {q["name"].lower() for q in quotas}
    static = [l for l in svc.get("static_limits", []) if l["name"].lower() not in quota_names]
    limits = quotas + static
    if limits:
        entry["limits"] = limits

    if svc.get("runtimes"):
        if live_runtimes:
            entry["runtimes"] = live_runtimes
        else:
            entry["runtimes"] = svc["runtimes"]

    if svc.get("news_keywords"):
        news = fetch_news(svc["news_keywords"])
        print(f"[{svc['id']}] Got {len(news)} news")
        if news:
            entry["news"] = news

    return entry


def lambda_handler(event, context):
    # Fetch runtimes once for all services that need it
    live_runtimes = fetch_runtimes()

    services = [build_service(svc, live_runtimes) for svc in SERVICES]

    output = {
        "lastUpdated": date.today().isoformat(),
        "services": services,
    }

    body = json.dumps(output, indent=2, ensure_ascii=False)

    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=body.encode('utf-8'),
        ContentType='application/json',
    )

    return {"statusCode": 200, "body": f"Wrote {len(services)} services to s3://{BUCKET}/{S3_KEY}"}
