"""Parse RobotoCore services from Docker health endpoint."""


def parse_health_services(health_data):
    """Extract service names from health endpoint response with type info."""
    if not health_data or "services" not in health_data:
        return None
    services = health_data["services"]
    native = [k for k, v in services.items() if v.get("type") == "native"]
    moto = [k for k, v in services.items() if v.get("type") == "moto"]
    all_services = list(services.keys())
    if all_services:
        print(f"[robotocore] Got {len(all_services)} services from health ({len(native)} native, {len(moto)} moto)")
        return {"services": all_services, "native": native, "moto": moto}
    return None
