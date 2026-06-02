"""
Tools Collector: fetches latest version info from GitHub for local dev tools.
Services are scraped from each tool's docs with static fallback.
"""

import json
import os
from datetime import date
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import boto3

from parsers import localstack as localstack_parser
from parsers import ministack as ministack_parser
from parsers import floci as floci_parser
from parsers import robotocore as robotocore_parser
from parsers.normalize import normalize_list, to_display_name

s3 = boto3.client("s3")
codebuild = boto3.client("codebuild")

BUCKET = os.environ["BUCKET_NAME"]
S3_KEY = os.environ.get("S3_KEY", "data/tools.json")
DOCKER_PROJECT = os.environ.get("DOCKER_PROJECT_NAME", "")

# Load static tool definitions
TOOLS = json.loads(Path(__file__).with_name("tools.json").read_text())

# Parser map: tool_id -> parser module
PARSERS = {
    "localstack": localstack_parser,
    "ministack": ministack_parser,
    "floci": floci_parser,
    "robotocore": robotocore_parser,
}


def _github_latest_version(repo):
    """Get latest release tag from GitHub."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = Request(url, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "s3rv3rl3ss-bot",
    })
    try:
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        tag = data.get("tag_name", "")
        return tag.lstrip("v")
    except (HTTPError, Exception) as e:
        print(f"[tools] Error fetching version for {repo}: {e}")
        return None


def _github_stars(repo):
    """Get star count from GitHub."""
    url = f"https://api.github.com/repos/{repo}"
    req = Request(url, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "s3rv3rl3ss-bot",
    })
    try:
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        return data.get("stargazers_count", 0)
    except (HTTPError, Exception):
        return 0


def _start_docker_build():
    """Start CodeBuild project to measure Docker images. Non-blocking."""
    if not DOCKER_PROJECT:
        return
    try:
        codebuild.start_build(projectName=DOCKER_PROJECT)
        print(f"[tools] Started CodeBuild project: {DOCKER_PROJECT}")
    except Exception as e:
        print(f"[tools] Error starting CodeBuild: {e}")


def _get_docker_results():
    """Read previous Docker measurement results from S3."""
    try:
        resp = s3.get_object(Bucket=BUCKET, Key="data/tools-docker.json")
        data = json.loads(resp["Body"].read().decode("utf-8"))
        return {item["id"]: item for item in data}
    except Exception:
        return {}


def lambda_handler(event, context):
    today = date.today().isoformat()
    output_tools = []

    # Start Docker measurements (async, results available next run)
    _start_docker_build()

    # Read previous Docker results if available
    docker_results = _get_docker_results()

    for tool in TOOLS:
        repo = tool["repo"]
        tool_id = tool["id"]
        print(f"[tools] Processing {tool['name']} ({repo})")

        version = _github_latest_version(repo)
        stars = _github_stars(repo)

        # Try scraping services, fallback to static
        parser = PARSERS.get(tool_id)
        scraped_services = parser.fetch_services() if parser else None

        # If Docker health data has services, prefer that (most accurate)
        docker_data = docker_results.get(tool_id, {})
        health_data = docker_data.get("health", {})
        paid_services = tool.get("paidServices", [])
        service_meta = {}

        if health_data and hasattr(parser, "parse_health_services"):
            health_result = parser.parse_health_services(health_data)
            if health_result and isinstance(health_result, dict):
                # Parser returned structured data
                services = health_result.get("services", [])
                paid_services = health_result.get("paid", paid_services)
                if "native" in health_result:
                    service_meta["native"] = health_result["native"]
                    service_meta["moto"] = health_result["moto"]
            elif health_result and isinstance(health_result, list):
                services = health_result
            elif scraped_services:
                services = scraped_services
            else:
                services = tool["services"]
        elif scraped_services:
            services = scraped_services
        else:
            services = tool["services"]

        print(f"[tools] {tool['name']}: {len(services)} services")
        # Store raw count before normalization
        raw_service_count = len(services)
        raw_paid_count = len(paid_services)
        # Normalize service names
        services = normalize_list(services)
        paid_services = normalize_list(paid_services)
        if service_meta:
            if "native" in service_meta:
                service_meta["native"] = normalize_list(service_meta["native"])
                service_meta["moto"] = normalize_list(service_meta["moto"])

        # Merge Docker results if available
        docker_data = docker_results.get(tool_id, {})
        performance = tool.get("performance", {})
        if docker_data:
            performance = {
                "startupTime": f"{docker_data.get('startupMs', 0)}ms",
                "memoryIdle": docker_data.get("memoryIdle", performance.get("memoryIdle", "")),
                "imageSize": docker_data.get("imageSize", performance.get("imageSize", "")),
            }

        entry = {
            "id": tool_id,
            "name": tool["name"],
            "description": tool["description"],
            "url": tool["url"],
            "repoUrl": f"https://github.com/{repo}",
            "version": version or "unknown",
            "stars": stars,
            "technology": tool["technology"],
            "license": tool["license"],
            "price": tool["price"],
            "performance": performance,
            "services": services,
            "serviceCount": raw_service_count,
            "paidServices": paid_services,
            "paidServiceCount": raw_paid_count,
        }
        if service_meta:
            entry["serviceMeta"] = service_meta
        output_tools.append(entry)
        print(f"[tools] {tool['name']}: v{version}, {stars} stars, {len(services)} services")

    # Build display names map for all services
    all_service_ids = set()
    for t in output_tools:
        all_service_ids.update(t["services"])
        all_service_ids.update(t.get("paidServices", []))
    display_names = {sid: to_display_name(sid) for sid in sorted(all_service_ids)}

    output = {
        "lastUpdated": today,
        "tools": output_tools,
        "serviceDisplayNames": display_names,
    }

    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=json.dumps(output, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    return {"statusCode": 200, "body": f"Updated {len(output_tools)} tools"}
