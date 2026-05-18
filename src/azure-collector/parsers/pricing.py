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
        {"label": "Base charge (Standard)", "price": "$0.0135", "unit": "per hour", "description": "$0.0135 per hour (~$9.81/month)"},
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
        {"label": "Standard connectors", "price": "$0.000125", "unit": "per call", "description": "$0.000125 per connector call"},
        {"label": "Enterprise connectors", "price": "$0.001", "unit": "per call", "description": "$0.001 per enterprise connector call"},
    ],
    "api-management": [
        {"label": "API calls (Consumption)", "price": "$3.50", "unit": "per 1M calls", "description": "$3.50 per million API calls"},
    ],
    "blob-storage": [
        {"label": "Hot storage", "price": "$0.018", "unit": "per GB/month", "description": "$0.018 per GB per month"},
        {"label": "Cool storage", "price": "$0.010", "unit": "per GB/month", "description": "$0.010 per GB per month"},
        {"label": "Write operations (Hot)", "price": "$0.055", "unit": "per 10K ops", "description": "$0.055 per 10,000 operations"},
        {"label": "Read operations (Hot)", "price": "$0.0044", "unit": "per 10K ops", "description": "$0.0044 per 10,000 operations"},
    ],
    "queue-storage": [
        {"label": "Operations", "price": "$0.004", "unit": "per 10K ops", "description": "$0.004 per 10,000 operations"},
        {"label": "Storage", "price": "$0.045", "unit": "per GB/month", "description": "$0.045 per GB per month (LRS)"},
    ],
    "signalr": [
        {"label": "Unit (Standard)", "price": "$1.61", "unit": "per unit/day", "description": "$1.61 per unit per day (~$48.97/month)"},
        {"label": "Messages (Serverless)", "price": "$1.00", "unit": "per 1M messages", "description": "$1.00 per million messages"},
    ],
    "static-web-apps": [
        {"label": "Standard plan", "price": "$9.00", "unit": "per app/month", "description": "$9.00 per app per month"},
    ],
    "aks": [
        {"label": "Cluster management (Free tier)", "price": "$0.00", "unit": "free", "description": "Free cluster management"},
        {"label": "Cluster management (Standard)", "price": "$0.10", "unit": "per cluster/hour", "description": "$0.10 per cluster per hour"},
        {"label": "Cluster management (Premium)", "price": "$0.60", "unit": "per cluster/hour", "description": "$0.60 per cluster per hour"},
    ],
    "azure-sql-serverless": [
        {"label": "vCore (General Purpose)", "price": "$0.000145", "unit": "per vCore-second", "description": "$0.000145 per vCore-second"},
        {"label": "Storage", "price": "$0.115", "unit": "per GB/month", "description": "$0.115 per GB per month"},
    ],
    "azure-ai-services": [
        {"label": "GPT-4o input", "price": "$2.50", "unit": "per 1M tokens", "description": "$2.50 per million input tokens"},
        {"label": "GPT-4o output", "price": "$10.00", "unit": "per 1M tokens", "description": "$10.00 per million output tokens"},
    ],
    "key-vault": [
        {"label": "Secret operations", "price": "$0.03", "unit": "per 10K ops", "description": "$0.03 per 10,000 operations"},
        {"label": "Key operations (software)", "price": "$0.03", "unit": "per 10K ops", "description": "$0.03 per 10,000 operations"},
    ],
    "notification-hubs": [
        {"label": "Basic namespace", "price": "$10.00", "unit": "per month", "description": "$10.00 per unit per month"},
        {"label": "Standard namespace", "price": "$200.00", "unit": "per month", "description": "$200.00 per unit per month"},
    ],
}


def fetch_pricing(service_id):
    pricing = STATIC_PRICING.get(service_id)
    if pricing:
        print(f"[{service_id}] Got {len(pricing)} pricing items (static)")
    return pricing
