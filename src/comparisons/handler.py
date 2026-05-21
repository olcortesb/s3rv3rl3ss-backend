import json
import os

import boto3

from categories import CATEGORIES

s3 = boto3.client("s3")

BUCKET = os.environ["BUCKET_NAME"]
S3_KEY = os.environ.get("S3_KEY", "data/comparisons.json")


def _read_s3_json(key):
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=key)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        print(f"[comparisons] Error reading {key}: {e}")
        return {"services": []}


def _get_service(data, service_id):
    if not service_id:
        return None
    return next((s for s in data.get("services", []) if s["id"] == service_id), None)


def _verify_limit(svc, field_name):
    if not svc or not field_name or not svc.get("limits"):
        return None
    return next((l for l in svc["limits"] if l["name"] == field_name), None)


def _verify_pricing(svc, field_name):
    if not svc or not field_name or not svc.get("pricingDetails"):
        return None
    return next((p for p in svc["pricingDetails"] if p["label"] == field_name), None)


def build_comparisons(providers_data):
    output_categories = []
    warnings = 0

    for cat in CATEGORIES:
        # Get services for this category
        services = {}
        for provider in ["aws", "gcp", "azure"]:
            sid = cat["services"].get(provider)
            services[provider] = _get_service(providers_data[provider], sid)

        # Verify limits
        verified_limits = []
        for row in cat.get("limits", []):
            verified_row = {"label": row["label"]}
            for provider in ["aws", "gcp", "azure"]:
                field = row.get(provider)
                static_key = f"{provider}_static"
                if field:
                    match = _verify_limit(services[provider], field)
                    if match:
                        verified_row[provider] = field
                    else:
                        warnings += 1
                        verified_row[provider] = None
                elif row.get(static_key):
                    verified_row[provider] = None
                    verified_row[f"{provider}_value"] = row[static_key]
                else:
                    verified_row[provider] = None
            if row.get("unit"):
                verified_row["unit"] = row["unit"]
            verified_limits.append(verified_row)

        # Verify pricing
        verified_pricing = []
        for row in cat.get("pricing", []):
            verified_row = {"label": row["label"]}
            for provider in ["aws", "gcp", "azure"]:
                field = row.get(provider)
                static_key = f"{provider}_static"
                if field:
                    match = _verify_pricing(services[provider], field)
                    if match:
                        verified_row[provider] = field
                    else:
                        warnings += 1
                        verified_row[provider] = None
                        if row.get(static_key):
                            verified_row[f"{provider}_value"] = row[static_key]
                elif row.get(static_key):
                    verified_row[provider] = None
                    verified_row[f"{provider}_value"] = row[static_key]
                else:
                    verified_row[provider] = None
            verified_pricing.append(verified_row)

        output_categories.append({
            "id": cat["id"],
            "name": cat["name"],
            "icon": cat["icon"],
            "services": cat["services"],
            "limitsUrls": cat.get("limitsUrls", {}),
            "limits": verified_limits,
            "pricing": verified_pricing,
        })

    return {"categories": output_categories}, warnings


def lambda_handler(event, context):
    # Read all 3 provider JSONs from S3
    providers_data = {
        "aws": _read_s3_json("data/services-aws.json"),
        "gcp": _read_s3_json("data/services-gcp.json"),
        "azure": _read_s3_json("data/services-azure.json"),
    }

    result, warnings = build_comparisons(providers_data)
    print(f"[comparisons] {len(result['categories'])} categories, {warnings} warnings")

    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=json.dumps(result, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    return {"statusCode": 200, "body": f"Generated comparisons with {len(result['categories'])} categories"}
