#!/usr/bin/env python3
"""Seed DynamoDB and visits.json with CloudFront historical request data."""
import boto3
import json
from datetime import datetime, timezone

PROFILE = "olcb-terraform"
REGION = "us-east-1"
DISTRIBUTION_ID = "E1GBZPA7ONZI4M"
TABLE_NAME = "s3rv3rl3ss-536395113578"
DATA_BUCKET = "s3rv3rl3ss-data-536395113578"
S3_KEY = "data/visits.json"
CF_DISTRIBUTION_ID = "E1GBZPA7ONZI4M"

session = boto3.Session(profile_name=PROFILE, region_name=REGION)
cw = session.client("cloudwatch")
dynamo = session.client("dynamodb")
s3 = session.client("s3")
cf = session.client("cloudfront")

# Fetch 30 days from CloudWatch
resp = cw.get_metric_statistics(
    Namespace="AWS/CloudFront",
    MetricName="Requests",
    Dimensions=[
        {"Name": "DistributionId", "Value": DISTRIBUTION_ID},
        {"Name": "Region", "Value": "Global"},
    ],
    StartTime=datetime(2026, 9, 19, tzinfo=timezone.utc),
    EndTime=datetime(2026, 10, 19, tzinfo=timezone.utc),
    Period=86400,
    Statistics=["Sum"],
)

datapoints = sorted(resp["Datapoints"], key=lambda x: x["Timestamp"])
print(f"Got {len(datapoints)} days of data")

# Write DAY# items to DynamoDB
total = 0
for dp in datapoints:
    date_str = dp["Timestamp"].strftime("%Y-%m-%d")
    visits = int(dp["Sum"])
    total += visits
    month_str = dp["Timestamp"].strftime("%Y-%m")

    dynamo.update_item(
        TableName=TABLE_NAME,
        Key={"pk": {"S": "SITE#s3rv3rl3ss"}, "sk": {"S": f"DAY#{date_str}"}},
        UpdateExpression="ADD visits :v SET #src = :src",
        ExpressionAttributeNames={"#src": "source"},
        ExpressionAttributeValues={":v": {"N": str(visits)}, ":src": {"S": "cloudwatch-seed"}},
    )
    dynamo.update_item(
        TableName=TABLE_NAME,
        Key={"pk": {"S": "SITE#s3rv3rl3ss"}, "sk": {"S": f"MONTH#{month_str}"}},
        UpdateExpression="ADD visits :v",
        ExpressionAttributeValues={":v": {"N": str(visits)}},
    )
    print(f"  {date_str}: {visits}")

# TOTAL
dynamo.update_item(
    TableName=TABLE_NAME,
    Key={"pk": {"S": "SITE#s3rv3rl3ss"}, "sk": {"S": "TOTAL"}},
    UpdateExpression="ADD visits :v",
    ExpressionAttributeValues={":v": {"N": str(total)}},
)
print(f"Total seeded: {total}")

# Build visits.json
last_30 = [
    {"date": dp["Timestamp"].strftime("%Y-%m-%d"), "visits": int(dp["Sum"])}
    for dp in datapoints[-30:]
]
yesterday = last_30[-1]["visits"] if last_30 else 0

payload = {
    "total": total,
    "yesterday": yesterday,
    "last_30_days": last_30,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "source": "cloudwatch-seed",
}

s3.put_object(
    Bucket=DATA_BUCKET,
    Key=S3_KEY,
    Body=json.dumps(payload),
    ContentType="application/json",
)
print(f"Uploaded {S3_KEY}")

cf.create_invalidation(
    DistributionId=CF_DISTRIBUTION_ID,
    InvalidationBatch={
        "Paths": {"Quantity": 1, "Items": ["/data/visits.json"]},
        "CallerReference": f"seed-{int(datetime.now().timestamp())}",
    },
)
print("CloudFront invalidation created")
