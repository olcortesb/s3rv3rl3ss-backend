"""Parse AWS Emulator services from health endpoint.

AWS Emulator serves HTTPS on 127.0.0.1:9297 (self-signed cert).
No standard health endpoint is documented yet — returns None to fall back
to the static service list in tools.json until a Docker image is available.
"""


def parse_health_services(health_data):
    return None
