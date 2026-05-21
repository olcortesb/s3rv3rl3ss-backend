"""
Initial load: Populates DynamoDB with current data from the 3 provider JSONs.
Run once after table creation.

Usage:
    python scripts/load_dynamo.py [--table TABLE_NAME] [--region REGION]
"""

import json
import hashlib
import sys
import argparse
from datetime import date
from pathlib import Path

import boto3

FRONTEND_DATA = Path(__file__).parent.parent.parent / "s3rv3rl3ss" / "src" / "data"

PROVIDERS = {
    "aws": "services-aws.json",
    "gcp": "services-gcp.json",
    "azure": "services-azure.json",
}


def hash4(text):
    return hashlib.md5(text.encode()).hexdigest()[:4]


def build_items(provider, services):
    """Build DynamoDB items from service data."""
    today = date.today().isoformat()
    items = []

    for svc in services:
        pk = f"{provider}#{svc['id']}"

        # SERVICE metadata
        items.append({
            "pk": pk,
            "sk": "SERVICE",
            "gsi1pk": f"SERVICE#{provider}",
            "gsi1sk": f"{svc.get('category', 'Other')}#{svc['id']}",
            "name": svc["name"],
            "category": svc.get("category", "Other"),
            "description": svc.get("description", ""),
            "pricing": svc.get("pricing", ""),
            "pricingUrl": svc.get("pricingUrl", ""),
            "url": svc.get("url", ""),
            "icon": svc.get("icon", ""),
            "date": today,
        })

        # LIMITS
        for limit in svc.get("limits", []):
            items.append({
                "pk": pk,
                "sk": f"LIMIT#{limit['name']}",
                "gsi1pk": f"LIMIT#{provider}",
                "gsi1sk": f"{today}#{svc['id']}",
                "name": limit["name"],
                "value": str(limit.get("value", "")),
                "source": limit.get("source", "api" if limit.get("description") else "static"),
                "date": today,
            })

        # NEWS
        for news in svc.get("news", []):
            h = hash4(news.get("title", ""))
            items.append({
                "pk": pk,
                "sk": f"NEWS#{news.get('date', today)}#{h}",
                "gsi1pk": f"NEWS#{provider}",
                "gsi1sk": f"{news.get('date', today)}#{svc['id']}",
                "title": news.get("title", ""),
                "url": news.get("url", ""),
                "date": news.get("date", today),
            })

        # RUNTIMES
        for rt in svc.get("runtimes", []):
            items.append({
                "pk": pk,
                "sk": f"RUNTIME#{rt['name']}",
                "gsi1pk": f"RUNTIME#{provider}",
                "gsi1sk": f"{rt.get('status', 'active')}#{svc['id']}",
                "name": rt["name"],
                "status": rt.get("status", "active"),
                "eol": rt.get("eol", ""),
                "date": today,
            })

        # PRICING
        for price in svc.get("pricingDetails", []):
            items.append({
                "pk": pk,
                "sk": f"PRICING#{price['label']}",
                "gsi1pk": f"PRICING#{provider}",
                "gsi1sk": f"{today}#{svc['id']}",
                "label": price["label"],
                "price": price.get("price", ""),
                "unit": price.get("unit", ""),
                "date": today,
            })

    return items


def load_changelog(provider, changelog_file):
    """Load existing changelog entries as CHANGE items."""
    items = []
    try:
        with open(changelog_file) as f:
            data = json.load(f)
        for change in data.get("changes", []):
            svc_id = change.get("service", "unknown")
            pk = f"{provider}#{svc_id}"
            h = hash4(change.get("detail", ""))
            items.append({
                "pk": pk,
                "sk": f"CHANGE#{change['date']}#{h}",
                "gsi1pk": f"CHANGE#{provider}",
                "gsi1sk": f"{change['date']}#{svc_id}",
                "type": change.get("type", ""),
                "detail": change.get("detail", ""),
                "url": change.get("url", ""),
                "date": change.get("date", ""),
            })
    except FileNotFoundError:
        pass
    return items


def batch_write(table, items):
    """Write items in batches of 25, deduplicating by pk+sk."""
    # Deduplicate by pk+sk (keep last)
    seen = {}
    for item in items:
        key = (item["pk"], item["sk"])
        seen[key] = item
    items = list(seen.values())

    written = 0
    for i in range(0, len(items), 25):
        batch = items[i:i+25]
        with table.batch_writer() as writer:
            for item in batch:
                clean = {k: v for k, v in item.items() if v != ""}
                writer.put_item(Item=clean)
        written += len(batch)
        if written % 100 == 0:
            print(f"  Written {written}/{len(items)}...")
    return written


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default=None, help="DynamoDB table name")
    parser.add_argument("--region", default="us-east-1")
    args = parser.parse_args()

    # Auto-detect table name from CloudFormation
    if not args.table:
        cf = boto3.client("cloudformation", region_name=args.region)
        try:
            resp = cf.describe_stacks(StackName="s3rv3rl3ss-backend")
            outputs = {o["OutputKey"]: o["OutputValue"] for o in resp["Stacks"][0]["Outputs"]}
            args.table = outputs.get("DataTableName")
        except Exception:
            pass

    if not args.table:
        print("Error: --table required (or deploy stack first)")
        sys.exit(1)

    print(f"Loading data into: {args.table} ({args.region})")

    dynamodb = boto3.resource("dynamodb", region_name=args.region)
    table = dynamodb.Table(args.table)

    total = 0
    for provider, filename in PROVIDERS.items():
        filepath = FRONTEND_DATA / filename
        print(f"\n{'='*50}")
        print(f"Loading {provider} from {filepath}")

        with open(filepath) as f:
            data = json.load(f)

        items = build_items(provider, data["services"])
        print(f"  Services: {len(data['services'])}, Items: {len(items)}")

        written = batch_write(table, items)
        total += written
        print(f"  ✅ {written} items written")

    # Load changelogs
    changelog_map = {
        "aws": FRONTEND_DATA / "changelog.json",
        "gcp": FRONTEND_DATA / "changelog-gcp.json",
        "azure": FRONTEND_DATA / "changelog-azure.json",
    }

    print(f"\n{'='*50}")
    print("Loading changelogs...")
    for provider, filepath in changelog_map.items():
        items = load_changelog(provider, filepath)
        if items:
            written = batch_write(table, items)
            total += written
            print(f"  ✅ {provider}: {written} changelog entries")
        else:
            print(f"  ⚠️  {provider}: no changelog found")

    print(f"\n{'='*50}")
    print(f"✅ Total: {total} items loaded into {args.table}")


if __name__ == "__main__":
    main()
