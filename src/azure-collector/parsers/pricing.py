import requests

PRICING_API = "https://prices.azure.com/api/retail/prices"
DEFAULT_REGION = "eastus"
MAX_ITEMS = 10

# Mapeo de service_id → serviceName en la API de Azure
SERVICE_NAME_MAP = {
    "azure-functions": "Functions",
    "container-apps": "Azure Container Apps",
    "cosmos-db": "Azure Cosmos DB",
    "service-bus": "Service Bus",
    "event-grid": "Event Grid",
    "event-hubs": "Event Hubs",
    "logic-apps": "Logic Apps",
    "api-management": "API Management",
    "blob-storage": "Storage",
    "queue-storage": "Storage",
    "signalr": "SignalR",
    "static-web-apps": "Azure Static Web Apps",
    "aks": "Azure Kubernetes Service",
    "azure-sql-serverless": "SQL Database",
    "azure-ai-services": "Azure AI services",
    "key-vault": "Key Vault",
    "notification-hubs": "Notification Hubs",
}

# Filtros adicionales para servicios que comparten serviceName
SERVICE_FILTERS = {
    "blob-storage": "productName eq 'Blob Storage'",
    "queue-storage": "productName eq 'Queue Storage'",
    "azure-sql-serverless": "contains(skuName, 'Serverless')",
}

# Pricing estático como fallback
STATIC_PRICING = {
    "azure-functions": [
        {"label": "Executions", "price": "$0.20", "unit": "per 1M executions", "description": "$0.20 per million executions"},
        {"label": "Execution Time", "price": "$0.000016", "unit": "per GB-second", "description": "$0.000016 per GB-second"},
    ],
    "container-apps": [
        {"label": "vCPU", "price": "$0.000024", "unit": "per vCPU-second", "description": "$0.000024 per vCPU-second"},
        {"label": "Memory", "price": "$0.000003", "unit": "per GiB-second", "description": "$0.000003 per GiB-second"},
        {"label": "Requests", "price": "$0.40", "unit": "per 1M requests", "description": "$0.40 per million requests"},
    ],
    "cosmos-db": [
        {"label": "RU/s (serverless)", "price": "$0.25", "unit": "per 1M RUs", "description": "$0.25 per million Request Units"},
        {"label": "Storage", "price": "$0.25", "unit": "per GB/month", "description": "$0.25 per GB per month"},
    ],
    "service-bus": [
        {"label": "Operations (Standard)", "price": "$0.05", "unit": "per 1M operations", "description": "$0.05 per million messaging operations"},
    ],
    "event-grid": [
        {"label": "Operations", "price": "$0.60", "unit": "per 1M operations", "description": "$0.60 per million operations"},
    ],
    "event-hubs": [
        {"label": "Throughput unit (Standard)", "price": "$0.015", "unit": "per hour", "description": "$0.015 per throughput unit per hour"},
        {"label": "Ingress events", "price": "$0.028", "unit": "per 1M events", "description": "$0.028 per million events"},
    ],
    "logic-apps": [
        {"label": "Actions (Consumption)", "price": "$0.000125", "unit": "per action", "description": "$0.000125 per action execution"},
    ],
    "api-management": [
        {"label": "API calls (Consumption)", "price": "$3.50", "unit": "per 1M calls", "description": "$3.50 per million API calls"},
    ],
    "blob-storage": [
        {"label": "Hot storage", "price": "$0.018", "unit": "per GB/month", "description": "$0.018 per GB per month"},
    ],
    "queue-storage": [
        {"label": "Operations", "price": "$0.004", "unit": "per 10K ops", "description": "$0.004 per 10,000 operations"},
    ],
    "signalr": [
        {"label": "Unit (Standard)", "price": "$1.61", "unit": "per unit/day", "description": "$1.61 per unit per day"},
    ],
    "static-web-apps": [
        {"label": "Standard plan", "price": "$9.00", "unit": "per app/month", "description": "$9.00 per app per month"},
    ],
    "aks": [
        {"label": "Cluster management (Standard)", "price": "$0.10", "unit": "per cluster/hour", "description": "$0.10 per cluster per hour"},
    ],
    "azure-sql-serverless": [
        {"label": "vCore (General Purpose)", "price": "$0.000145", "unit": "per vCore-second", "description": "$0.000145 per vCore-second"},
    ],
    "azure-ai-services": [
        {"label": "GPT-4o input", "price": "$2.50", "unit": "per 1M tokens", "description": "$2.50 per million input tokens"},
    ],
    "key-vault": [
        {"label": "Secret operations", "price": "$0.03", "unit": "per 10K ops", "description": "$0.03 per 10,000 operations"},
    ],
    "notification-hubs": [
        {"label": "Basic namespace", "price": "$10.00", "unit": "per month", "description": "$10.00 per unit per month"},
    ],
}


def _format_price(price):
    if price == 0:
        return "$0.00"
    if price < 0.0001:
        return f"${price:.8f}"
    if price < 0.01:
        return f"${price:.6f}"
    if price < 1:
        return f"${price:.4f}"
    return f"${price:.2f}"


def _fetch_from_api(service_id):
    service_name = SERVICE_NAME_MAP.get(service_id)
    if not service_name:
        return None

    filter_expr = f"serviceName eq '{service_name}' and armRegionName eq '{DEFAULT_REGION}' and priceType eq 'Consumption'"

    extra_filter = SERVICE_FILTERS.get(service_id)
    if extra_filter:
        filter_expr += f" and {extra_filter}"

    try:
        resp = requests.get(PRICING_API, params={"$filter": filter_expr, "$top": "50"}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("Items", [])

        if not items:
            return None

        # Deduplicar por meterName y tomar los más relevantes
        seen = set()
        pricing = []
        for item in items:
            meter = item.get("meterName", "")
            if meter in seen or not meter:
                continue
            seen.add(meter)

            price_val = item.get("retailPrice", 0)
            unit = item.get("unitOfMeasure", "")

            pricing.append({
                "label": meter,
                "price": _format_price(price_val),
                "unit": f"per {unit}" if unit else "",
                "description": f"{_format_price(price_val)} per {unit} ({item.get('skuName', '')})",
            })

            if len(pricing) >= MAX_ITEMS:
                break

        return pricing if pricing else None
    except Exception as e:
        print(f"[azure-pricing] API error for {service_id}: {e}")
        return None


def fetch_pricing(service_id):
    # Intentar API real primero
    api_pricing = _fetch_from_api(service_id)
    if api_pricing:
        print(f"[{service_id}] Got {len(api_pricing)} pricing items (api)")
        return api_pricing

    # Fallback a estático
    static = STATIC_PRICING.get(service_id)
    if static:
        print(f"[{service_id}] Got {len(static)} pricing items (static fallback)")
    return static
