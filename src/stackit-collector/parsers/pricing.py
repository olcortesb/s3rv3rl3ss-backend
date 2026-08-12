import json
from urllib.request import urlopen

SKUS_API = "https://pim.api.stackit.cloud/v1/skus"

# Map service_id -> product name in the SKUs API
PRODUCT_MAP = {
    "kubernetes-engine": "Kubernetes Engine",
    "object-storage": "Object Storage",
    "postgresql-flex": "PostgreSQL Flex",
    "mongodb-flex": "MongoDB Flex",
    "mariadb": "MariaDB",
    "redis": "Redis",
    "key-value-store": "Key Value Store",
    "opensearch": "OpenSearch",
    "rabbitmq": "RabbitMQ",
    "secrets-manager": "Secrets Manager",
    "kms": "KMS",
    "load-balancer": "Application Load Balancer",
    "dns": "DNS",
    "cdn": "CDN",
    "vpn": "VPN",
    "logs": "Logs",
    "observability": "Observability",
    "ai-model-serving": "AI Model Serving",
    "container-registry": "Container Registry",
    "server": "Server",
    "cloud-foundry": "Cloud Foundry",
    "git": "Git",
    "pipelines": "Pipelines",
}

_skus_cache = None


def _get_skus():
    global _skus_cache
    if _skus_cache is not None:
        return _skus_cache
    try:
        with urlopen(SKUS_API, timeout=10) as resp:
            data = json.loads(resp.read())
        _skus_cache = data.get("services", [])
        print(f"[stackit-pricing] Fetched {len(_skus_cache)} SKUs")
    except Exception as e:
        print(f"[stackit-pricing] Error fetching SKUs: {e}")
        _skus_cache = []
    return _skus_cache


def fetch_pricing(service_id):
    product = PRODUCT_MAP.get(service_id)
    if not product:
        return []

    skus = _get_skus()
    items = []

    for sku in skus:
        if sku.get("product") != product:
            continue
        if sku.get("deprecated") == "Yes":
            continue
        if sku.get("priceListVisibility") != "Yes":
            continue

        price = sku.get("price", "")
        monthly = sku.get("monthlyPrice", "")
        unit = sku.get("unitBilling", "")
        currency = sku.get("currency", "€")

        try:
            price_val = float(price)
            monthly_val = float(monthly)
            items.append({
                "label": sku.get("name", sku.get("title", "")),
                "price": f"{currency}{price_val:.6f}",
                "unit": unit,
                "monthly": f"{currency}{monthly_val:.2f}/mo",
            })
        except (ValueError, TypeError):
            continue

        if len(items) >= 5:
            break

    return items
