import json
import os
from datetime import date, datetime, timezone

import boto3

from services import SERVICES
from parsers.news import fetch_news
from parsers.pricing import fetch_pricing
from parsers.statistics import build_statistics
from parsers.changelog import build_changelog
from parsers.dynamo import write_changes, update_service_data

s3 = boto3.client('s3')
cf = boto3.client('cloudfront')

BUCKET = os.environ['BUCKET_NAME']
S3_KEY = os.environ.get('S3_KEY', 'data/services-stackit.json')
STATISTICS_KEY = os.environ.get('STATISTICS_KEY', 'data/statistics-stackit.json')
CHANGELOG_KEY = os.environ.get('CHANGELOG_KEY', 'data/changelog-stackit.json')
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID', '')


def _invalidate(paths):
    if not CLOUDFRONT_DISTRIBUTION_ID:
        return
    try:
        cf.create_invalidation(
            DistributionId=CLOUDFRONT_DISTRIBUTION_ID,
            InvalidationBatch={'Paths': {'Quantity': len(paths), 'Items': paths}, 'CallerReference': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}
        )
        print(f"[cloudfront] invalidation created")
    except Exception as e:
        print(f"[cloudfront] invalidation failed: {e}")


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
        "calculatorUrl": svc.get("calculatorUrl", ""),
        "url": svc["url"],
        "icon": svc["icon"],
    }

    if svc.get("static_limits"):
        entry["limits"] = svc["static_limits"]

    if svc.get("runtimes"):
        entry["runtimes"] = svc["runtimes"]

    news = fetch_news(svc["id"])
    if news:
        entry["news"] = news
    print(f"[{svc['id']}] Got {len(news)} news")

    pricing_items = fetch_pricing(svc["id"])
    if pricing_items:
        entry["pricingDetails"] = pricing_items

    return entry


def lambda_handler(event, context):
    services = [build_service(svc) for svc in SERVICES]

    old_services = []
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=S3_KEY)
        old_data = json.loads(resp['Body'].read().decode('utf-8'))
        old_services = old_data.get('services', [])
    except Exception:
        pass

    existing_changelog = []
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=CHANGELOG_KEY)
        cl_data = json.loads(resp['Body'].read().decode('utf-8'))
        existing_changelog = cl_data.get('changes', [])
    except Exception:
        pass

    changelog = build_changelog(old_services, services, existing_changelog)
    new_changes = len(changelog) - len(existing_changelog)
    print(f"[stackit-changelog] {new_changes} new changes detected")

    if new_changes > 0:
        new_entries = changelog[:new_changes]
        dynamo_written = write_changes("stackit", new_entries)
        print(f"[dynamo] {dynamo_written} changes written")
    update_service_data("stackit", services)
    print(f"[dynamo] service data updated")

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

    s3.put_object(
        Bucket=BUCKET,
        Key=CHANGELOG_KEY,
        Body=json.dumps({"lastUpdated": date.today().isoformat(), "changes": changelog}, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )

    stats = build_statistics(services)
    stats["lastUpdated"] = date.today().isoformat()
    print(f"[stackit-statistics] {stats['summary']['totalServices']} services")

    s3.put_object(
        Bucket=BUCKET,
        Key=STATISTICS_KEY,
        Body=json.dumps(stats, indent=2, ensure_ascii=False).encode('utf-8'),
        ContentType='application/json',
    )

    _invalidate(['/data/services-stackit.json', '/data/changelog-stackit.json', '/data/statistics-stackit.json'])
    return {"statusCode": 200, "body": f"Wrote {len(services)} STACKIT services"}
