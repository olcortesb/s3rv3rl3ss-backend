import json
import os
from datetime import date

import boto3

from services import SERVICES
from parsers.quotas import list_quotas
from parsers.news import fetch_news
from parsers.runtimes import fetch_runtimes
from parsers.docs_limits import fetch_docs_limits
from parsers.changelog import build_changelog
from parsers.integrations import fetch_integrations
from parsers.pricing import fetch_pricing
from parsers.statistics import build_statistics

s3 = boto3.client('s3')

BUCKET = os.environ['BUCKET_NAME']
S3_KEY = os.environ['S3_KEY']
CHANGELOG_KEY = os.environ.get('CHANGELOG_KEY', 'data/changelog.json')
STATISTICS_KEY = os.environ.get('STATISTICS_KEY', 'data/statistics.json')


def _read_s3_json(key):
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=key)
        return json.loads(resp['Body'].read().decode('utf-8'))
    except Exception:
        return None


def build_service(svc, live_runtimes=None):
    entry = {
        "id": svc["id"],
        "enabled": True,
        "name": svc["name"],
        "category": svc["category"],
        "description": svc["description"],
        "useCases": svc["useCases"],
        "pricing": svc["pricing"],
        "pricingUrl": svc.get("pricingUrl", ""),
        "url": svc["url"],
        "icon": svc["icon"],
    }

    sources_ok = True

    # 1. Quotas from Service Quotas API
    quotas = list_quotas(svc["service_code"])

    # 2. Limits from docs (replaces static_limits)
    docs_limits = None
    if svc.get("docs_limits_url"):
        docs_limits = fetch_docs_limits(svc["docs_limits_url"])

    if docs_limits is not None:
        quota_names = {q["name"].lower() for q in quotas}
        static = [l for l in docs_limits if l["name"].lower() not in quota_names]
        limits = quotas + static
    else:
        sources_ok = False
        quota_names = {q["name"].lower() for q in quotas}
        static = [l for l in svc.get("static_limits", []) if l["name"].lower() not in quota_names]
        limits = quotas + static

    if limits:
        entry["limits"] = limits

    # 3. Runtimes (only for Lambda)
    if svc.get("runtimes"):
        if live_runtimes:
            entry["runtimes"] = live_runtimes
        else:
            sources_ok = False
            entry["runtimes"] = svc["runtimes"]

    # 4. News from RSS
    if svc.get("news_keywords"):
        news = fetch_news(svc["news_keywords"], svc.get("blog_feeds"))
        print(f"[{svc['id']}] Got {len(news)} news")
        if news:
            entry["news"] = news

    entry["dataStatus"] = "ok" if sources_ok else "partial"

    # 5. Integrations from SDK
    if svc.get("integrations_config"):
        all_integrations = []
        for cfg in svc["integrations_config"]:
            items = fetch_integrations(svc["id"], cfg["sdk_client"], cfg["shape_name"])
            if items:
                all_integrations.append({
                    "label": cfg.get("label", "Integrations"),
                    "description": cfg.get("description", ""),
                    "items": items,
                })
        if all_integrations:
            entry["integrations"] = all_integrations

    # 6. Pricing from Price List API
    if svc.get("pricing_code"):
        pricing_items = fetch_pricing(svc["id"], svc["pricing_code"])
        if pricing_items:
            entry["pricingDetails"] = pricing_items

    return entry


def lambda_handler(event, context):
    live_runtimes = fetch_runtimes()

    services = [build_service(svc, live_runtimes) for svc in SERVICES]

    # Build changelog by comparing with previous data
    old_data = _read_s3_json(S3_KEY)
    old_changelog = _read_s3_json(CHANGELOG_KEY)
    old_services = old_data.get("services", []) if old_data else []
    existing = old_changelog.get("changes", []) if old_changelog else []

    changelog = build_changelog(old_services, services, existing)
    new_changes = len(changelog) - len(existing)
    print(f"[changelog] {new_changes} new changes detected")

    # Write services JSON
    output = {
        "lastUpdated": date.today().isoformat(),
        "services": services,
    }

    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=json.dumps(output, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )

    # Write changelog JSON
    changelog_output = {
        "lastUpdated": date.today().isoformat(),
        "changes": changelog,
    }

    s3.put_object(
        Bucket=BUCKET,
        Key=CHANGELOG_KEY,
        Body=json.dumps(changelog_output, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )

    # Write statistics JSON
    stats = build_statistics(services)
    stats["lastUpdated"] = date.today().isoformat()
    print(f"[statistics] {stats['summary']['totalServices']} services, {stats['summary']['totalQuotas']} quotas")

    s3.put_object(
        Bucket=BUCKET,
        Key=STATISTICS_KEY,
        Body=json.dumps(stats, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )

    return {"statusCode": 200, "body": f"Wrote {len(services)} services, {new_changes} new changes"}
