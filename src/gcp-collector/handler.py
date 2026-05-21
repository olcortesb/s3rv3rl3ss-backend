import json
import os
from datetime import date

import boto3

from services import SERVICES
from parsers.news import fetch_news
from parsers.pricing import fetch_pricing
from parsers.statistics import build_statistics
from parsers.changelog import build_changelog
from parsers.dynamo import write_changes, update_service_data

s3 = boto3.client('s3')

BUCKET = os.environ['BUCKET_NAME']
S3_KEY = os.environ.get('S3_KEY', 'data/services-gcp.json')
STATISTICS_KEY = os.environ.get('STATISTICS_KEY', 'data/statistics-gcp.json')
CHANGELOG_KEY = os.environ.get('CHANGELOG_KEY', 'data/changelog-gcp.json')


def build_service(svc):
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

    # Static limits
    if svc.get("static_limits"):
        entry["limits"] = svc["static_limits"]

    # Runtimes
    if svc.get("runtimes"):
        entry["runtimes"] = svc["runtimes"]

    # News
    news = fetch_news(svc["id"])
    print(f"[{svc['id']}] Got {len(news)} news")
    if news:
        entry["news"] = news

    # Pricing
    pricing_items = fetch_pricing(svc["id"])
    if pricing_items:
        entry["pricingDetails"] = pricing_items

    return entry


def lambda_handler(event, context):
    services = [build_service(svc) for svc in SERVICES]

    # Read previous data for changelog
    old_services = []
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=S3_KEY)
        old_data = json.loads(resp['Body'].read().decode('utf-8'))
        old_services = old_data.get('services', [])
    except Exception:
        pass

    # Read existing changelog
    existing_changelog = []
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=CHANGELOG_KEY)
        cl_data = json.loads(resp['Body'].read().decode('utf-8'))
        existing_changelog = cl_data.get('changes', [])
    except Exception:
        pass

    # Build changelog
    changelog = build_changelog(old_services, services, existing_changelog)
    new_changes = len(changelog) - len(existing_changelog)
    print(f"[gcp-changelog] {new_changes} new changes detected")

    # Persist to DynamoDB
    if new_changes > 0:
        new_entries = changelog[:new_changes]
        dynamo_written = write_changes("gcp", new_entries)
        print(f"[dynamo] {dynamo_written} changes written")
    update_service_data("gcp", services)
    print(f"[dynamo] service data updated")

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
    s3.put_object(
        Bucket=BUCKET,
        Key=CHANGELOG_KEY,
        Body=json.dumps({"lastUpdated": date.today().isoformat(), "changes": changelog}, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )

    # Write statistics JSON
    stats = build_statistics(services)
    stats["lastUpdated"] = date.today().isoformat()
    print(f"[gcp-statistics] {stats['summary']['totalServices']} services")

    s3.put_object(
        Bucket=BUCKET,
        Key=STATISTICS_KEY,
        Body=json.dumps(stats, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )

    return {"statusCode": 200, "body": f"Wrote {len(services)} GCP services"}
