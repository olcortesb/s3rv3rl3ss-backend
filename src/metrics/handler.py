"""
Generates metrics.json with real project infrastructure metrics.
Queries CloudWatch for Lambda stats and calculates costs.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import boto3

s3 = boto3.client("s3")
cw = boto3.client("cloudwatch")
dynamodb = boto3.client("dynamodb")
lambda_client = boto3.client("lambda")

BUCKET = os.environ["BUCKET_NAME"]
TABLE_NAME = os.environ["TABLE_NAME"]
S3_KEY = os.environ.get("S3_KEY", "data/metrics.json")
STACK_PREFIX = "s3rv3rl3ss-backend"

# Lambda pricing (arm64, us-east-1)
PRICE_PER_GB_SECOND = 0.0000133334
PRICE_PER_REQUEST = 0.20 / 1_000_000

# Function names to monitor
FUNCTIONS = [
    "CollectorFunction",
    "GcpCollectorFunction",
    "AzureCollectorFunction",
    "ComparisonsFunction",
    "ChangelogFunction",
    "CommitterFunction",
]


def _get_lambda_metrics(function_prefix, start, end, period):
    """Get invocations, duration, and errors for all functions."""
    metrics = {"invocations": 0, "duration_ms": 0, "errors": 0, "functions": {}}

    # List actual function names
    paginator = lambda_client.get_paginator("list_functions")
    function_names = []
    for page in paginator.paginate():
        for fn in page["Functions"]:
            if STACK_PREFIX in fn["FunctionName"]:
                function_names.append(fn["FunctionName"])

    for fn_name in function_names:
        short_name = fn_name.split("-")[-2] if "-" in fn_name else fn_name

        # Invocations
        resp = cw.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Invocations",
            Dimensions=[{"Name": "FunctionName", "Value": fn_name}],
            StartTime=start,
            EndTime=end,
            Period=period,
            Statistics=["Sum"],
        )
        invocations = sum(dp["Sum"] for dp in resp["Datapoints"])

        # Duration
        resp = cw.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Duration",
            Dimensions=[{"Name": "FunctionName", "Value": fn_name}],
            StartTime=start,
            EndTime=end,
            Period=period,
            Statistics=["Sum", "Average"],
        )
        total_duration = sum(dp["Sum"] for dp in resp["Datapoints"])
        avg_duration = resp["Datapoints"][0]["Average"] if resp["Datapoints"] else 0

        # Errors
        resp = cw.get_metric_statistics(
            Namespace="AWS/Lambda",
            MetricName="Errors",
            Dimensions=[{"Name": "FunctionName", "Value": fn_name}],
            StartTime=start,
            EndTime=end,
            Period=period,
            Statistics=["Sum"],
        )
        errors = sum(dp["Sum"] for dp in resp["Datapoints"])

        metrics["invocations"] += int(invocations)
        metrics["duration_ms"] += total_duration
        metrics["errors"] += int(errors)
        metrics["functions"][short_name] = {
            "invocations": int(invocations),
            "totalDurationMs": round(total_duration),
            "avgDurationMs": round(avg_duration),
            "errors": int(errors),
        }

    return metrics


def _get_dynamo_metrics():
    """Get DynamoDB item count and size."""
    resp = dynamodb.describe_table(TableName=TABLE_NAME)
    table = resp["Table"]
    return {
        "items": table.get("ItemCount", 0),
        "sizeBytes": table.get("TableSizeBytes", 0),
    }


def _get_s3_metrics():
    """Count objects in the data bucket."""
    count = 0
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix="data/"):
        count += page.get("KeyCount", 0)
    return {"objects": count}


def _calculate_cost(metrics_today, metrics_month):
    """Calculate estimated costs based on actual usage."""
    # Lambda cost
    gb_seconds_month = (metrics_month["duration_ms"] / 1000) * (256 / 1024)  # approximate avg memory
    lambda_cost = gb_seconds_month * PRICE_PER_GB_SECOND + metrics_month["invocations"] * PRICE_PER_REQUEST

    # Free tier: 400,000 GB-s + 1M requests
    lambda_free_tier = 400_000
    lambda_effective = max(0, gb_seconds_month - lambda_free_tier) * PRICE_PER_GB_SECOND

    return {
        "monthly": {
            "total": f"${0.40 + lambda_effective:.2f}",
            "lambda": f"${lambda_effective:.4f}" if lambda_effective > 0 else "$0.00 (free tier)",
            "dynamodb": "$0.00 (free tier)",
            "s3": "$0.00 (free tier)",
            "secretsManager": "$0.40",
            "eventbridge": "$0.00 (free tier)",
        },
        "note": "Only Secrets Manager has cost outside free tier",
    }


def lambda_handler(event, context):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Today's metrics (1-day period)
    print("[metrics] Fetching today's Lambda metrics...")
    metrics_today = _get_lambda_metrics(STACK_PREFIX, today_start, now, 86400)

    # Month metrics (30-day period)
    print("[metrics] Fetching month's Lambda metrics...")
    metrics_month = _get_lambda_metrics(STACK_PREFIX, month_start, now, 2592000)

    # DynamoDB
    print("[metrics] Fetching DynamoDB metrics...")
    dynamo = _get_dynamo_metrics()

    # S3
    print("[metrics] Fetching S3 metrics...")
    s3_metrics = _get_s3_metrics()

    # Cost
    cost = _calculate_cost(metrics_today, metrics_month)

    output = {
        "lastUpdated": now.isoformat()[:19] + "Z",
        "today": {
            "invocations": metrics_today["invocations"],
            "totalDurationMs": round(metrics_today["duration_ms"]),
            "errors": metrics_today["errors"],
            "functions": metrics_today["functions"],
        },
        "month": {
            "invocations": metrics_month["invocations"],
            "totalDurationMs": round(metrics_month["duration_ms"]),
            "errors": metrics_month["errors"],
            "functions": metrics_month["functions"],
        },
        "infrastructure": {
            "lambdaFunctions": len(metrics_month["functions"]),
            "architecture": "arm64",
            "runtime": "python3.12",
            "dynamodbItems": dynamo["items"],
            "dynamodbSizeKB": round(dynamo["sizeBytes"] / 1024),
            "s3Objects": s3_metrics["objects"],
        },
        "cost": cost,
    }

    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=json.dumps(output, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    print(f"[metrics] Today: {metrics_today['invocations']} invocations, {metrics_today['errors']} errors")
    print(f"[metrics] Month: {metrics_month['invocations']} invocations")

    return {"statusCode": 200, "body": f"Generated metrics: {metrics_today['invocations']} invocations today"}
