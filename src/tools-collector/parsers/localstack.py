"""Parse LocalStack services from Docker health endpoint."""


def parse_health_services(health_data):
    """All LocalStack services require a paid license (no free tier since 2026)."""
    if not health_data or "services" not in health_data:
        return None
    services = list(health_data["services"].keys())
    if services:
        print(f"[localstack] Got {len(services)} services from health (all paid)")
        return {"services": [], "paid": services}
    return None
