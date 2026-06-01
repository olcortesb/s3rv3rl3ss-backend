"""
Tools Collector: fetches latest version info from GitHub for local dev tools.
Services and performance data are static (from READMEs).
"""

import json
import os
from datetime import date
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import boto3

s3 = boto3.client("s3")

BUCKET = os.environ["BUCKET_NAME"]
S3_KEY = os.environ.get("S3_KEY", "data/tools.json")

TOOLS = [
    {
        "id": "localstack",
        "name": "LocalStack",
        "description": "Cloud service emulator that runs in a single container on your laptop or in your CI environment",
        "url": "https://localstack.cloud/",
        "repo": "localstack/localstack",
        "technology": ["Python", "Docker"],
        "license": "BSL (restricted) / Proprietary (Pro)",
        "price": "Now paid / $35/mo (Pro)",
        "performance": {
            "startupTime": "~15-30s",
            "memoryIdle": "~500MB",
            "imageSize": "~1 GB",
        },
        "services": [
            "S3", "SQS", "SNS", "API Gateway v1", "API Gateway v2", "Route53", "Firehose",
        ],
        "paidServices": [
            "Lambda", "DynamoDB", "IAM", "SSM", "EventBridge", "CloudFormation",
            "KMS", "Kinesis", "Step Functions", "SES", "CloudWatch", "Secrets Manager",
            "ECR", "ECS", "EKS", "Cognito", "EC2", "RDS", "ElastiCache",
            "Glue", "Athena", "AppSync", "CloudFront", "OpenSearch", "WAF",
            "EMR", "EBS", "EFS", "ALB/ELBv2", "Batch",
        ],
    },
    {
        "id": "ministack",
        "name": "MiniStack",
        "description": "Free, open-source AWS emulator. 60+ services on a single Docker container at port 4566. Drop-in LocalStack replacement",
        "url": "https://ministack.org/",
        "repo": "ministackorg/ministack",
        "technology": ["Python", "Docker"],
        "license": "MIT",
        "price": "Free",
        "performance": {
            "startupTime": "~2s",
            "memoryIdle": "~30MB",
            "imageSize": "~250 MB",
        },
        "services": [
            "Lambda", "DynamoDB", "S3", "SQS", "SNS", "API Gateway v1", "API Gateway v2",
            "CloudFormation", "IAM", "KMS", "Kinesis", "EventBridge", "Step Functions",
            "SES", "CloudWatch", "Secrets Manager", "ECR", "ECS", "EKS", "Route53", "SSM",
            "Cognito", "EC2", "RDS", "ElastiCache", "Glue", "Athena", "AppSync",
            "CloudFront", "Firehose", "OpenSearch", "WAF", "CodeBuild", "Batch",
            "EMR", "EBS", "EFS", "ALB/ELBv2",
        ],
        "paidServices": [],
    },
    {
        "id": "floci",
        "name": "Floci",
        "description": "Free, open-source local AWS emulator. 52+ services, real Docker for Lambda/RDS/ECS/EC2. Drop-in LocalStack replacement",
        "url": "https://floci.io/floci/",
        "repo": "floci-io/floci",
        "technology": ["Java", "Docker"],
        "license": "MIT",
        "price": "Free",
        "performance": {
            "startupTime": "~24ms",
            "memoryIdle": "~13MB",
            "imageSize": "~90 MB",
        },
        "services": [
            "Lambda", "DynamoDB", "DynamoDB Streams", "S3", "SQS", "SNS",
            "API Gateway v1", "API Gateway v2", "CloudFormation",
            "IAM", "STS", "KMS", "Kinesis", "EventBridge", "EventBridge Pipes",
            "EventBridge Scheduler", "Step Functions", "SES", "SES v2",
            "CloudWatch", "Secrets Manager", "ECR", "ECS", "EKS", "EC2",
            "Route53", "SSM", "Cognito", "RDS", "ElastiCache", "Glue",
            "Athena", "AppSync", "Firehose", "OpenSearch", "Neptune", "MSK",
            "CodeBuild", "CodeDeploy", "Auto Scaling", "ALB/ELBv2",
            "ACM", "AppConfig", "AWS Backup", "AWS Config",
            "Transfer Family", "Textract", "Bedrock Runtime",
            "Cost Explorer", "Pricing",
        ],
        "paidServices": [],
    },
    {
        "id": "robotocore",
        "name": "RobotoCore",
        "description": "AWS service emulator with focus on high-fidelity API compatibility",
        "url": "https://github.com/robotocore/robotocore",
        "repo": "robotocore/robotocore",
        "technology": ["Go", "Docker"],
        "license": "Apache 2.0",
        "price": "Free",
        "performance": {
            "startupTime": "~3s",
            "memoryIdle": "~50MB",
            "imageSize": "~150 MB",
        },
        "services": [
            "Lambda", "DynamoDB", "S3", "SQS", "SNS", "API Gateway v1",
            "IAM", "KMS", "EventBridge", "CloudWatch",
        ],
        "paidServices": [],
    },
]


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


def lambda_handler(event, context):
    today = date.today().isoformat()
    output_tools = []

    for tool in TOOLS:
        repo = tool["repo"]
        print(f"[tools] Processing {tool['name']} ({repo})")

        version = _github_latest_version(repo)
        stars = _github_stars(repo)

        entry = {
            "id": tool["id"],
            "name": tool["name"],
            "description": tool["description"],
            "url": tool["url"],
            "repoUrl": f"https://github.com/{repo}",
            "version": version or "unknown",
            "stars": stars,
            "technology": tool["technology"],
            "license": tool["license"],
            "price": tool["price"],
            "performance": tool["performance"],
            "services": tool["services"],
            "paidServices": tool["paidServices"],
        }
        output_tools.append(entry)
        print(f"[tools] {tool['name']}: v{version}, {stars} stars")

    output = {
        "lastUpdated": today,
        "tools": output_tools,
    }

    s3.put_object(
        Bucket=BUCKET,
        Key=S3_KEY,
        Body=json.dumps(output, indent=2, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )

    return {"statusCode": 200, "body": f"Updated {len(output_tools)} tools"}
