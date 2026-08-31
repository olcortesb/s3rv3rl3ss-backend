"""
ReinventFunction — generates reinvent.json from DynamoDB CHANGE items.
Schedule: cron(0 */2 * * ? *) — every 2h, with date-based skip logic:
  - Jan–Oct:        skip
  - Nov 1–29:       execute only at 07:00 and 19:00 UTC
  - Nov 30–Dec 4:   execute every run (event week)
  - Dec 5–7:        execute only at 07:00 UTC
  - Dec 8+:         skip
"""

import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import boto3
from boto3.dynamodb.conditions import Key

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
cf = boto3.client("cloudfront")

BUCKET = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ["TABLE_NAME"]
S3_KEY = os.environ.get("S3_KEY", "data/reinvent.json")
CLOUDFRONT_DISTRIBUTION_ID = os.environ.get("CLOUDFRONT_DISTRIBUTION_ID", "")

REINVENT = {
    "active_from": date(2026, 11, 1),
    "event_start": date(2026, 11, 30),
    "event_end":   date(2026, 12, 4),
    "active_to":   date(2026, 12, 7),
}

REINVENT_KEYWORDS = ["re:invent", "reinvent", "re:invent 2026"]

MAX_DAYS = 180
TOP_SERVICES = 10
RECENT_NEWS_LIMIT = 20
TREND_WINDOW_DAYS = 30


def _should_run():
    now = datetime.now(timezone.utc)
    today = now.date()
    hour = now.hour

    if today < REINVENT["active_from"] or today > REINVENT["active_to"]:
        return False, "skip: out of season"

    if REINVENT["event_start"] <= today <= REINVENT["event_end"]:
        return True, "event week"

    if today > REINVENT["event_end"]:
        # Dec 5-7: only 07:00 UTC
        if hour != 7:
            return False, f"skip: post-event off-hour ({hour}h)"
        return True, "post-event"

    # Nov 1-29: only 07:00 and 19:00 UTC
    if hour not in (7, 19):
        return False, f"skip: pre-event off-hour ({hour}h)"
    return True, "pre-event"


def _query_changes(table, cutoff):
    changes = []
    kwargs = {
        "IndexName": "gsi1",
        "KeyConditionExpression": Key("gsi1pk").eq("CHANGE#aws") & Key("gsi1sk").gte(cutoff),
        "ScanIndexForward": False,
    }
    while True:
        resp = table.query(**kwargs)
        changes.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return changes


def _get_service_names(table):
    """Read SERVICE items to get display names."""
    names = {}
    kwargs = {
        "IndexName": "gsi1",
        "KeyConditionExpression": Key("gsi1pk").eq("SERVICE#aws"),
    }
    while True:
        resp = table.query(**kwargs)
        for item in resp.get("Items", []):
            svc_id = item["pk"].split("#", 1)[-1]
            names[svc_id] = item.get("name", svc_id)
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return names


def _is_reinvent_item(item):
    title = item.get("detail", "").lower()
    return any(kw in title for kw in REINVENT_KEYWORDS)


def _build_activity_timeline(changes):
    """Weekly buckets of change counts over the 180-day window."""
    weekly = defaultdict(int)
    for item in changes:
        d = item.get("date", "")
        if not d:
            continue
        try:
            dt = date.fromisoformat(d)
            # Monday of that week
            week_start = (dt - timedelta(days=dt.weekday())).isoformat()
            weekly[week_start] += 1
        except ValueError:
            continue

    running_total = 0
    timeline = []
    for week in sorted(weekly):
        running_total += weekly[week]
        timeline.append({"week": week, "changes": weekly[week], "total": running_total})
    return timeline


def _build_top_services(changes, service_names):
    counts = defaultdict(int)
    for item in changes:
        svc = item["pk"].split("#", 1)[-1]
        counts[svc] += 1

    total = sum(counts.values()) or 1
    cutoff_30 = (date.today() - timedelta(days=TREND_WINDOW_DAYS)).isoformat()
    cutoff_60 = (date.today() - timedelta(days=TREND_WINDOW_DAYS * 2)).isoformat()

    recent = defaultdict(int)
    prev = defaultdict(int)
    for item in changes:
        svc = item["pk"].split("#", 1)[-1]
        d = item.get("date", "")
        if d >= cutoff_30:
            recent[svc] += 1
        elif d >= cutoff_60:
            prev[svc] += 1

    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:TOP_SERVICES]
    result = []
    for svc, count in top:
        r, p = recent.get(svc, 0), prev.get(svc, 0)
        trend = "up" if r > p else ("down" if r < p else "stable")
        result.append({
            "service": svc,
            "name": service_names.get(svc, svc),
            "changes": count,
            "percentage": round(count * 100 / total),
            "trend": trend,
        })
    return result


def _build_hot_services(changes, service_names):
    """Services with the most changes in the last 30 days."""
    cutoff = (date.today() - timedelta(days=TREND_WINDOW_DAYS)).isoformat()
    recent = defaultdict(int)
    for item in changes:
        if item.get("date", "") >= cutoff:
            svc = item["pk"].split("#", 1)[-1]
            recent[svc] += 1

    hot = sorted(recent.items(), key=lambda x: x[1], reverse=True)[:5]
    return [
        {"service": svc, "name": service_names.get(svc, svc), "recentChanges": count}
        for svc, count in hot
    ]


def _build_changes_by_type(changes):
    counts = defaultdict(int)
    for item in changes:
        counts[item.get("type", "unknown")] += 1
    return dict(counts)


def _build_recent_news(changes):
    news = [
        {
            "date": item.get("date", ""),
            "service": item["pk"].split("#", 1)[-1],
            "title": item.get("detail", ""),
            "url": item.get("url", ""),
            "reinvent": _is_reinvent_item(item),
        }
        for item in changes
        if item.get("type") == "new_news" and item.get("url")
    ]
    news.sort(key=lambda x: x["date"], reverse=True)
    return news[:RECENT_NEWS_LIMIT]


def _invalidate():
    if not CLOUDFRONT_DISTRIBUTION_ID:
        return
    try:
        cf.create_invalidation(
            DistributionId=CLOUDFRONT_DISTRIBUTION_ID,
            InvalidationBatch={
                "Paths": {"Quantity": 1, "Items": ["/data/reinvent.json"]},
                "CallerReference": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            },
        )
        print("[cloudfront] invalidation created")
    except Exception as e:
        print(f"[cloudfront] invalidation failed: {e}")


def lambda_handler(event, context):
    force = event.get("force", False)
    should_run, reason = _should_run()
    if not should_run and not force:
        print(f"[reinvent] {reason}")
        return {"statusCode": 200, "body": reason}

    print(f"[reinvent] running — {reason}")

    table = dynamodb.Table(TABLE_NAME)
    cutoff = (date.today() - timedelta(days=MAX_DAYS)).isoformat()

    changes = _query_changes(table, cutoff)
    service_names = _get_service_names(table)
    print(f"[reinvent] {len(changes)} CHANGE items, {len(service_names)} services")

    today = date.today()
    event_start = REINVENT["event_start"]
    days_until = (event_start - today).days

    output = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "countdown": {
            "eventStart": event_start.isoformat(),
            "daysUntil": max(0, days_until),
        },
        "activityTimeline": _build_activity_timeline(changes),
        "topServices": _build_top_services(changes, service_names),
        "hotServices": _build_hot_services(changes, service_names),
        "changesByType": _build_changes_by_type(changes),
        "recentNews": _build_recent_news(changes),
    }

    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=json.dumps(output, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"[reinvent] wrote {S3_KEY} — {len(changes)} changes, {len(output['recentNews'])} news")

    _invalidate()
    return {"statusCode": 200, "body": f"ok — {len(changes)} changes"}
