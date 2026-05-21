"""
DynamoDB persistence for s3rv3rl3ss.
Writes CHANGE items for detected diffs and updates current state (LIMIT, NEWS, RUNTIME, PRICING).
"""

import hashlib
import os
from datetime import date

import boto3

TABLE_NAME = os.environ.get("TABLE_NAME", "")
_dynamodb = None
_table = None


def _get_table():
    global _dynamodb, _table
    if not TABLE_NAME:
        return None
    if _table is None:
        _dynamodb = boto3.resource("dynamodb")
        _table = _dynamodb.Table(TABLE_NAME)
    return _table


def _hash4(text):
    return hashlib.md5(text.encode()).hexdigest()[:4]


def write_changes(provider, changes):
    """Write CHANGE items to DynamoDB for detected diffs."""
    table = _get_table()
    if not table or not changes:
        return 0

    today = date.today().isoformat()
    written = 0

    with table.batch_writer() as writer:
        for change in changes:
            svc_id = change.get("service", "unknown")
            h = _hash4(change.get("detail", "") + change.get("type", ""))
            item = {
                "pk": f"{provider}#{svc_id}",
                "sk": f"CHANGE#{change.get('date', today)}#{h}",
                "gsi1pk": f"CHANGE#{provider}",
                "gsi1sk": f"{change.get('date', today)}#{svc_id}",
                "type": change.get("type", ""),
                "detail": change.get("detail", ""),
                "date": change.get("date", today),
            }
            if change.get("url"):
                item["url"] = change["url"]
            writer.put_item(Item=item)
            written += 1

    return written


def update_service_data(provider, services):
    """Update current state in DynamoDB (LIMIT, NEWS, RUNTIME, PRICING)."""
    table = _get_table()
    if not table:
        return 0

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
            h = _hash4(news.get("title", ""))
            item = {
                "pk": pk,
                "sk": f"NEWS#{news.get('date', today)}#{h}",
                "gsi1pk": f"NEWS#{provider}",
                "gsi1sk": f"{news.get('date', today)}#{svc['id']}",
                "title": news.get("title", ""),
                "date": news.get("date", today),
            }
            if news.get("url"):
                item["url"] = news["url"]
            items.append(item)

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

    # Deduplicate by pk+sk (keep last)
    seen = {}
    for item in items:
        key = (item["pk"], item["sk"])
        seen[key] = item
    items = list(seen.values())

    # Write in batches
    written = 0
    with table.batch_writer() as writer:
        for item in items:
            clean = {k: v for k, v in item.items() if v != ""}
            writer.put_item(Item=clean)
            written += 1

    return written
