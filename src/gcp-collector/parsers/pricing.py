STATIC_PRICING = {
    "cloud-run": [
        {"label": "vCPU", "price": "$0.00002400", "unit": "per vCPU-second", "description": "$0.00002400 per vCPU-second"},
        {"label": "Memory", "price": "$0.00000250", "unit": "per GiB-second", "description": "$0.00000250 per GiB-second"},
        {"label": "Requests", "price": "$0.40", "unit": "per 1M requests", "description": "$0.40 per million requests"},
    ],
    "cloud-run-functions": [
        {"label": "Invocations", "price": "$0.40", "unit": "per 1M invocations", "description": "$0.40 per million invocations"},
        {"label": "Compute (GHz-second)", "price": "$0.0000100", "unit": "per GHz-second", "description": "$0.0000100 per GHz-second"},
        {"label": "Memory", "price": "$0.0000025", "unit": "per GB-second", "description": "$0.0000025 per GB-second"},
    ],
    "firestore": [
        {"label": "Document reads", "price": "$0.036", "unit": "per 100K reads", "description": "$0.036 per 100,000 document reads"},
        {"label": "Document writes", "price": "$0.108", "unit": "per 100K writes", "description": "$0.108 per 100,000 document writes"},
        {"label": "Document deletes", "price": "$0.012", "unit": "per 100K deletes", "description": "$0.012 per 100,000 document deletes"},
        {"label": "Storage", "price": "$0.108", "unit": "per GiB/month", "description": "$0.108 per GiB per month"},
    ],
    "bigquery": [
        {"label": "Queries (on-demand)", "price": "$6.25", "unit": "per TB scanned", "description": "$6.25 per TB of data processed"},
        {"label": "Active storage", "price": "$0.020", "unit": "per GB/month", "description": "$0.020 per GB per month"},
        {"label": "Long-term storage", "price": "$0.010", "unit": "per GB/month", "description": "$0.010 per GB per month"},
        {"label": "Streaming inserts", "price": "$0.010", "unit": "per 200 MB", "description": "$0.010 per 200 MB"},
    ],
    "cloud-pubsub": [
        {"label": "Message delivery", "price": "$40.00", "unit": "per TiB", "description": "$40.00 per TiB of data delivered"},
        {"label": "Seek-related message storage", "price": "$0.27", "unit": "per GiB/month", "description": "$0.27 per GiB per month"},
    ],
    "cloud-tasks": [
        {"label": "Operations", "price": "$0.40", "unit": "per 1M operations", "description": "$0.40 per million operations (first 1M free)"},
    ],
    "cloud-scheduler": [
        {"label": "Jobs", "price": "$0.10", "unit": "per job/month", "description": "$0.10 per job per month (3 free)"},
    ],
    "eventarc": [],
    "cloud-storage": [
        {"label": "Standard storage", "price": "$0.020", "unit": "per GB/month", "description": "$0.020 per GB per month"},
        {"label": "Nearline storage", "price": "$0.010", "unit": "per GB/month", "description": "$0.010 per GB per month"},
        {"label": "Class A operations", "price": "$0.005", "unit": "per 1K ops", "description": "$0.005 per 1,000 operations"},
        {"label": "Class B operations", "price": "$0.0004", "unit": "per 1K ops", "description": "$0.0004 per 1,000 operations"},
    ],
    "workflows": [
        {"label": "Internal steps", "price": "$0.01", "unit": "per 1K steps", "description": "$0.01 per 1,000 internal steps"},
        {"label": "External steps (HTTP)", "price": "$0.025", "unit": "per 1K steps", "description": "$0.025 per 1,000 external steps"},
    ],
    "api-gateway": [
        {"label": "API calls", "price": "$3.00", "unit": "per 1M calls", "description": "$3.00 per million API calls (first 2M free)"},
    ],
    "gke": [
        {"label": "Cluster management (Autopilot)", "price": "$0.00", "unit": "free", "description": "No cluster management fee for Autopilot"},
        {"label": "Cluster management (Standard)", "price": "$0.10", "unit": "per cluster/hour", "description": "$0.10 per cluster per hour"},
        {"label": "Autopilot vCPU", "price": "$0.0445", "unit": "per vCPU/hour", "description": "$0.0445 per vCPU per hour"},
        {"label": "Autopilot Memory", "price": "$0.0049", "unit": "per GB/hour", "description": "$0.0049 per GB per hour"},
    ],
    "cloud-spanner": [
        {"label": "Processing units", "price": "$0.90", "unit": "per PU/hour", "description": "$0.90 per processing unit per hour"},
        {"label": "Storage", "price": "$0.30", "unit": "per GB/month", "description": "$0.30 per GB per month"},
    ],
    "cloud-run-jobs": [
        {"label": "vCPU", "price": "$0.00002400", "unit": "per vCPU-second", "description": "$0.00002400 per vCPU-second"},
        {"label": "Memory", "price": "$0.00000250", "unit": "per GiB-second", "description": "$0.00000250 per GiB-second"},
    ],
    "memorystore": [
        {"label": "Redis (Basic)", "price": "$0.049", "unit": "per GB/hour", "description": "$0.049 per GB per hour"},
        {"label": "Redis (Standard)", "price": "$0.068", "unit": "per GB/hour", "description": "$0.068 per GB per hour"},
    ],
    "secret-manager": [
        {"label": "Active secret versions", "price": "$0.06", "unit": "per version/month", "description": "$0.06 per active secret version per month"},
        {"label": "Access operations", "price": "$0.03", "unit": "per 10K ops", "description": "$0.03 per 10,000 access operations"},
    ],
    "cloud-build": [
        {"label": "Build minutes (default)", "price": "$0.003", "unit": "per build-minute", "description": "$0.003 per build-minute (first 120 min/day free)"},
    ],
    "vertex-ai": [
        {"label": "Gemini 1.5 Flash input", "price": "$0.075", "unit": "per 1M tokens", "description": "$0.075 per million input tokens"},
        {"label": "Gemini 1.5 Flash output", "price": "$0.30", "unit": "per 1M tokens", "description": "$0.30 per million output tokens"},
    ],
}


def fetch_pricing(service_id):
    pricing = STATIC_PRICING.get(service_id)
    if pricing:
        print(f"[{service_id}] Got {len(pricing)} pricing items (static)")
    return pricing
