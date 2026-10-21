import boto3
import gzip
import io
import json
import os
from datetime import datetime, timedelta, timezone

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")
cloudfront = boto3.client("cloudfront")

LOGS_BUCKET = os.environ["LOGS_BUCKET"]
DATA_BUCKET = os.environ["DATA_BUCKET"]
TABLE_NAME = os.environ["TABLE_NAME"]
CF_DISTRIBUTION_ID = os.environ["CLOUDFRONT_DISTRIBUTION_ID"]
S3_KEY = os.environ["S3_KEY"]
MAX_FILE_SIZE_MB = int(os.environ.get("MAX_FILE_SIZE_MB", "100"))
CHUNK_SIZE_MB = int(os.environ.get("CHUNK_SIZE_MB", "10"))

BOT_PATTERNS = [
    "bot", "crawler", "spider", "slurp", "bingbot", "googlebot",
    "yandex", "baidu", "duckduck", "semrush", "ahrefs", "mj12bot",
    "curl", "wget", "python-requests", "go-http-client",
]

PK = "SITE#s3rv3rl3ss"


def lambda_handler(event, context):
    target_date = event.get("date") if event else None
    if target_date:
        yesterday = target_date
    else:
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Processing logs for {yesterday}")

    visits = process_logs(yesterday)
    print(f"Visits for {yesterday}: {visits}")

    if visits > 0:
        persist_to_dynamo(yesterday, visits)

    visits_json = build_visits_json(yesterday)
    upload_visits_json(visits_json)
    invalidate_cache()

    return {"date": yesterday, "visits": visits}


def process_logs(date):
    prefix = f"cloudfront/{CF_DISTRIBUTION_ID}.{date}"
    paginator = s3.get_paginator("list_objects_v2")
    total_visits = 0

    for page in paginator.paginate(Bucket=LOGS_BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            size_mb = obj["Size"] / (1024 * 1024)
            if size_mb > MAX_FILE_SIZE_MB:
                print(f"Skipping {obj['Key']} — {size_mb:.1f}MB exceeds {MAX_FILE_SIZE_MB}MB limit")
                continue
            total_visits += count_visits_in_file(obj["Key"])

    return total_visits


def count_visits_in_file(key):
    response = s3.get_object(Bucket=LOGS_BUCKET, Key=key)
    body = response["Body"].read()

    if key.endswith(".gz"):
        body = gzip.decompress(body)

    count = 0
    for line in io.StringIO(body.decode("utf-8")):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if is_bot(line):
            continue
        # CloudFront log format: count only 2xx/3xx status codes
        parts = line.split("\t")
        if len(parts) > 8:
            status = parts[8]
            if status.startswith(("2", "3")):
                count += 1

    return count


def is_bot(line):
    line_lower = line.lower()
    return any(pattern in line_lower for pattern in BOT_PATTERNS)


def persist_to_dynamo(date, visits):
    table = dynamodb.Table(TABLE_NAME)
    year_month = date[:7]  # 2026-10

    table.update_item(
        Key={"pk": PK, "sk": "TOTAL"},
        UpdateExpression="ADD visits :v",
        ExpressionAttributeValues={":v": visits},
    )
    table.update_item(
        Key={"pk": PK, "sk": f"DAY#{date}"},
        UpdateExpression="SET visits = :v, #d = :d",
        ExpressionAttributeNames={"#d": "date"},
        ExpressionAttributeValues={":v": visits, ":d": date},
    )
    table.update_item(
        Key={"pk": PK, "sk": f"MONTH#{year_month}"},
        UpdateExpression="ADD visits :v",
        ExpressionAttributeValues={":v": visits},
    )


def build_visits_json(yesterday):
    table = dynamodb.Table(TABLE_NAME)

    total_item = table.get_item(Key={"pk": PK, "sk": "TOTAL"}).get("Item", {})
    total = int(total_item.get("visits", 0))

    yesterday_item = table.get_item(Key={"pk": PK, "sk": f"DAY#{yesterday}"}).get("Item", {})
    yesterday_visits = int(yesterday_item.get("visits", 0))

    # last 30 days
    history = []
    for i in range(30):
        day = (datetime.now(timezone.utc) - timedelta(days=i + 1)).strftime("%Y-%m-%d")
        item = table.get_item(Key={"pk": PK, "sk": f"DAY#{day}"}).get("Item", {})
        history.append({"date": day, "visits": int(item.get("visits", 0))})

    history.reverse()

    return {
        "total": total,
        "yesterday": yesterday_visits,
        "last_30_days": history,
        "updated_at": yesterday,
    }


def upload_visits_json(data):
    s3.put_object(
        Bucket=DATA_BUCKET,
        Key=S3_KEY,
        Body=json.dumps(data),
        ContentType="application/json",
    )
    print(f"Uploaded {S3_KEY} to {DATA_BUCKET}")


def invalidate_cache():
    cloudfront.create_invalidation(
        DistributionId=CF_DISTRIBUTION_ID,
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/data/visits.json"]},
            "CallerReference": f"visits-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        },
    )
