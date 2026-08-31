"""
Generates changelog-{provider}.json from DynamoDB CHANGE items.
Runs after all collectors finish. Produces changelogs with URLs.
"""

import json
import os
from datetime import date, timedelta

import boto3

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
cf = boto3.client('cloudfront')

BUCKET = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ["TABLE_NAME"]
MAX_DAYS = 180
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get('CLOUDFRONT_DISTRIBUTION_ID', '')


def _invalidate(paths):
    if not CLOUDFRONT_DISTRIBUTION_ID:
        return
    try:
        cf.create_invalidation(
            DistributionId=CLOUDFRONT_DISTRIBUTION_ID,
            InvalidationBatch={'Paths': {'Quantity': len(paths), 'Items': paths}, 'CallerReference': '-'.join(paths)}
        )
        print(f"[cloudfront] invalidation created")
    except Exception as e:
        print(f"[cloudfront] invalidation failed: {e}")

PROVIDERS = ["aws", "gcp", "azure"]
CHANGELOG_KEYS = {
    "aws": "data/changelog.json",
    "gcp": "data/changelog-gcp.json",
    "azure": "data/changelog-azure.json",
}


def query_changes(table, provider, cutoff_date):
    """Query all CHANGE items for a provider since cutoff_date."""
    changes = []
    kwargs = {
        "IndexName": "gsi1",
        "KeyConditionExpression": boto3.dynamodb.conditions.Key("gsi1pk").eq(f"CHANGE#{provider}") & boto3.dynamodb.conditions.Key("gsi1sk").gte(cutoff_date),
        "ScanIndexForward": False,
    }

    while True:
        resp = table.query(**kwargs)
        changes.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    return changes


def build_changelog(changes):
    """Convert DynamoDB items to changelog JSON format."""
    entries = []
    for item in changes:
        entry = {
            "date": item.get("date", ""),
            "service": item.get("pk", "").split("#", 1)[-1],
            "type": item.get("type", ""),
            "detail": item.get("detail", ""),
        }
        if item.get("url"):
            entry["url"] = item["url"]
        entries.append(entry)

    # Sort by date descending
    entries.sort(key=lambda x: x["date"], reverse=True)
    return entries


def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)
    today = date.today()
    cutoff = (today - timedelta(days=MAX_DAYS)).isoformat()

    results = {}
    for provider in PROVIDERS:
        changes = query_changes(table, provider, cutoff)
        changelog = build_changelog(changes)

        output = {
            "lastUpdated": today.isoformat(),
            "changes": changelog,
        }

        s3.put_object(
            Bucket=BUCKET,
            Key=CHANGELOG_KEYS[provider],
            Body=json.dumps(output, indent=2, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

        with_url = sum(1 for c in changelog if c.get("url"))
        results[provider] = {"total": len(changelog), "with_url": with_url}
        print(f"[{provider}] {len(changelog)} changes ({with_url} with URL)")

    _invalidate(['/data/changelog.json', '/data/changelog-gcp.json', '/data/changelog-azure.json'])
    return {"statusCode": 200, "body": json.dumps(results)}
