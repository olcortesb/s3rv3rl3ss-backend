import json
import boto3

pricing = boto3.client('pricing', region_name='us-east-1')

# Filters per service to get only the core serverless pricing
# Each filter is: (usagetype_contains, description_contains, label)
PRICING_FILTERS = {
    "lambda": [
        ("Lambda-Provisioned-GB-Second-ARM", None, "Compute (Provisioned, ARM)"),
    ],
    "dynamodb": [
        ("WriteRequestUnits", "write request units", "Write Requests (on-demand)"),
        ("ReadRequestUnits", "read request units", "Read Requests (on-demand)"),
        ("TimedStorage", "storage used beyond", "Storage (Standard)"),
    ],
    "sqs": [],
    "api-gateway": [
        ("ApiGatewayRequest", "first 333", "REST API Requests"),
        ("ApiGatewayHttpApiRequest", "first 300", "HTTP API Requests"),
        ("ApiGatewayMessage", "first 1 billion", "WebSocket Messages"),
    ],
    "s3": [
        ("TimedStorage-SIA-ByteHrs", None, "Storage (Infrequent Access)"),
        ("Requests-XZ-Tier1", None, "PUT/COPY/POST/LIST (Express One Zone)"),
        ("Requests-XZ-Tier2", None, "GET Requests (Express One Zone)"),
        ("Monitoring-Automation-INT", None, "Intelligent-Tiering Monitoring"),
    ],
    "appsync": [
        ("GraphQLInvocation", None, "Query & Mutation"),
        ("GraphQLNotification", None, "Real-time Updates"),
        ("EventAPI-Operation", None, "Event API Operations"),
        ("EventAPI-ConnectionDuration", None, "Event API Connection"),
    ],
    "eventbridge": [],
    "sns": [
        ("DeliveryAttempts-HTTP", "HTTP", "HTTP/HTTPS Notifications"),
        ("DeliveryAttempts-SMTP", "Email", "Email Notifications"),
    ],
    "cognito": [
        ("CognitoEssentialsMAU", "tier 1", "Essentials (per MAU)"),
        ("CUPM2MTokenRequestsFull", "tier 1", "M2M Token Requests"),
    ],
    "step-functions": [],
    "fargate": [],
    "aurora-serverless": [],
    "kinesis": [],
    "bedrock": [],
    "secrets-manager": [],
}

# Static pricing for services where the API doesn't return standard prices
STATIC_PRICING = {
    "lambda": [
        {"label": "Requests", "price": "$0.20", "unit": "per 1M requests", "description": "$0.20 per 1 million requests"},
        {"label": "Compute (x86)", "price": "$0.0000166667", "unit": "per GB-second", "description": "$0.0000166667 per GB-second"},
        {"label": "Compute (ARM)", "price": "$0.0000133334", "unit": "per GB-second", "description": "$0.0000133334 per GB-second"},
    ],
    "sqs": [
        {"label": "Standard Queue", "price": "$0.40", "unit": "per 1M requests", "description": "$0.40 per million requests (first 1 billion)"},
        {"label": "FIFO Queue", "price": "$0.50", "unit": "per 1M requests", "description": "$0.50 per million requests (first 1 billion)"},
    ],
    "eventbridge": [
        {"label": "Custom Events", "price": "$1.00", "unit": "per 1M events", "description": "$1.00 per million custom events published"},
        {"label": "Schema Discovery", "price": "$0.10", "unit": "per 1M events", "description": "$0.10 per million events ingested for schema discovery"},
    ],
    "kinesis": [
        {"label": "On-Demand Write", "price": "$0.08", "unit": "per GB", "description": "$0.08 per GB of data written"},
        {"label": "On-Demand Read", "price": "$0.04", "unit": "per GB", "description": "$0.04 per GB of data read"},
        {"label": "Provisioned Shard", "price": "$0.015", "unit": "per shard/hour", "description": "$0.015 per shard hour"},
    ],
    "bedrock": [
        {"label": "Claude 3.5 Sonnet Input", "price": "$0.003", "unit": "per 1K tokens", "description": "$0.003 per 1,000 input tokens"},
        {"label": "Claude 3.5 Sonnet Output", "price": "$0.015", "unit": "per 1K tokens", "description": "$0.015 per 1,000 output tokens"},
        {"label": "Titan Text Lite Input", "price": "$0.0003", "unit": "per 1K tokens", "description": "$0.0003 per 1,000 input tokens"},
    ],
    "secrets-manager": [
        {"label": "Secret Storage", "price": "$0.40", "unit": "per secret/month", "description": "$0.40 per secret per month"},
        {"label": "API Calls", "price": "$0.05", "unit": "per 10K calls", "description": "$0.05 per 10,000 API calls"},
    ],
    "step-functions": [
        {"label": "Standard Workflows", "price": "$0.025", "unit": "per 1K transitions", "description": "$0.025 per 1,000 state transitions"},
        {"label": "Express Workflows", "price": "$1.00", "unit": "per 1M requests", "description": "$1.00 per million requests"},
    ],
    "fargate": [
        {"label": "vCPU", "price": "$0.04048", "unit": "per vCPU/hour", "description": "$0.04048 per vCPU per hour"},
        {"label": "Memory", "price": "$0.004445", "unit": "per GB/hour", "description": "$0.004445 per GB per hour"},
        {"label": "Ephemeral Storage", "price": "$0.000111", "unit": "per GB/hour", "description": "$0.000111 per GB per hour (above 20 GB)"},
    ],
    "ecs": [
        {"label": "vCPU", "price": "$0.04048", "unit": "per vCPU/hour", "description": "$0.04048 per vCPU per hour (Fargate)"},
        {"label": "Memory", "price": "$0.004445", "unit": "per GB/hour", "description": "$0.004445 per GB per hour (Fargate)"},
        {"label": "Ephemeral Storage", "price": "$0.000111", "unit": "per GB/hour", "description": "$0.000111 per GB per hour above 20 GB (Fargate)"},
    ],
}


UNIT_FRIENDLY = {
    "Lambda-GB-Second": "per GB-second",
    "ReplicatedWriteRequestUnits": "per write request",
    "ReadRequestUnits": "per read request",
    "GB-Mo": "per GB/month",
    "GB-Month": "per GB/month",
    "Requests": "per request",
    "Messages": "per message",
    "Notifications": "per notification",
    "Operation": "per operation",
    "Minute": "per minute",
    "Objects": "per object",
    "CognitoUserPoolsMAU": "per MAU",
    "CognitoUserPools-M2MTokens": "per token",
    "Hours": "per hour",
}


def fetch_pricing(service_id, pricing_code, region="US East (N. Virginia)"):
    filters = PRICING_FILTERS.get(service_id, [])

    # If no API filters, use static pricing
    if not filters:
        static = STATIC_PRICING.get(service_id)
        if static:
            print(f"[{service_id}] Got {len(static)} pricing items (static)")
            return static
        return None

    try:
        response = pricing.get_products(
            ServiceCode=pricing_code,
            Filters=[
                {'Type': 'TERM_MATCH', 'Field': 'location', 'Value': region},
            ],
            MaxResults=100
        )

        all_prices = []
        for item in response['PriceList']:
            data = json.loads(item)
            attrs = data.get('product', {}).get('attributes', {})
            usagetype = attrs.get('usagetype', '')

            terms = data.get('terms', {}).get('OnDemand', {})
            for term_val in terms.values():
                for dim_val in term_val.get('priceDimensions', {}).values():
                    price_usd = dim_val.get('pricePerUnit', {}).get('USD', '0')
                    if price_usd == '0.0000000000' or price_usd == '0':
                        continue
                    all_prices.append({
                        'usagetype': usagetype,
                        'description': dim_val.get('description', ''),
                        'price': price_usd,
                        'unit': dim_val.get('unit', ''),
                    })

        result = []
        seen_labels = set()
        for usagetype_match, desc_match, label in filters:
            if label in seen_labels:
                continue
            for p in all_prices:
                ut_ok = usagetype_match.lower() in p['usagetype'].lower()
                desc_ok = desc_match.lower() in p['description'].lower() if desc_match else True
                if ut_ok and desc_ok:
                    price_val = f"${float(p['price']):.10f}".rstrip('0').rstrip('.')
                    unit = UNIT_FRIENDLY.get(p['unit'], p['unit'])
                    result.append({
                        "label": label,
                        "price": price_val,
                        "unit": unit,
                        "description": p['description'],
                    })
                    seen_labels.add(label)
                    break

        # Merge with static pricing if API returned partial results
        static = STATIC_PRICING.get(service_id, [])
        static_labels = {r["label"] for r in result}
        for s in static:
            if s["label"] not in static_labels:
                result.append(s)

        print(f"[{service_id}] Got {len(result)} pricing items")
        return result if result else None
    except Exception as e:
        print(f"[{service_id}] Error fetching pricing: {e}")
        static = STATIC_PRICING.get(service_id)
        if static:
            return static
        return None
