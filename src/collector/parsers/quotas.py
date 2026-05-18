import boto3

sq = boto3.client('service-quotas')

UNIT_MAP = {
    "None": "", "Count": "",
    "Microsecond": "μs", "Millisecond": "ms", "Second": "s",
    "Minute": "min", "Hour": "h", "Day": "d",
    "Kilobyte": "KB", "Kilobytes": "KB",
    "Megabyte": "MB", "Megabytes": "MB",
    "Gigabyte": "GB", "Gigabytes": "GB",
    "Terabyte": "TB", "Terabytes": "TB",
    "Megabytes/Second": "MB/s", "Gigabytes/Second": "GB/s",
}


def _format_value(value, unit):
    if isinstance(value, float) and value == int(value):
        value = int(value)
    suffix = UNIT_MAP.get(unit, unit) if unit else ""
    return f"{value} {suffix}".strip() if suffix else str(value)


def _fetch_quotas(service_code, api_method):
    limits = []
    paginator = sq.get_paginator(api_method)
    for page in paginator.paginate(ServiceCode=service_code):
        for q in page.get('Quotas', []):
            value = q.get('Value', 'N/A')
            unit = q.get('Unit', '')
            entry = {
                "name": q['QuotaName'],
                "value": _format_value(value, unit),
            }
            if q.get('Description'):
                entry["description"] = q['Description']
            if unit and unit != 'None':
                entry["unit"] = unit
            entry["adjustable"] = q.get('Adjustable', False)
            limits.append(entry)
    return limits


def list_quotas(service_code):
    try:
        limits = _fetch_quotas(service_code, 'list_service_quotas')
        if not limits:
            limits = _fetch_quotas(service_code, 'list_aws_default_service_quotas')
        print(f"[{service_code}] Got {len(limits)} quotas from API")
        return limits
    except Exception as e:
        print(f"[{service_code}] Error fetching quotas: {e}")
        return []
