"""Parse Floci services from Docker health endpoint."""


def parse_health_services(health_data):
    """Extract service names from health endpoint response."""
    if not health_data or "services" not in health_data:
        return None
    services = list(health_data["services"].keys())
    if services:
        print(f"[floci] Got {len(services)} services from health endpoint")
        return services
    return None
