"""
Committer using GitHub Contents API.
No git binary needed — uses REST API to create/update files directly.
Each invocation commits a single file that triggered the event.
"""

import base64
import json
import os

import boto3
from urllib.request import urlopen, Request
from urllib.error import HTTPError

s3 = boto3.client("s3")
sm = boto3.client("secretsmanager")

BUCKET = os.environ["BUCKET_NAME"]
GIT_SECRET_ARN = os.environ["GIT_SECRET_ARN"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "olcortesb/s3rv3rl3ss")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

# Mapping: S3 key prefix → frontend repo path prefix
S3_TO_REPO_MAP = "data/"
REPO_PREFIX = "src/data/"


def get_token():
    resp = sm.get_secret_value(SecretId=GIT_SECRET_ARN)
    secret = json.loads(resp["SecretString"])
    return secret["token"]


def github_api(method, path, token, data=None):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "s3rv3rl3ss-bot",
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        resp = urlopen(req, timeout=30)
        return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise RuntimeError(f"GitHub API {method} {path}: {e.code} {error_body}")


def get_file_sha(token, repo_path):
    """Get current SHA of a file (needed for updates)."""
    try:
        result = github_api("GET", f"contents/{repo_path}?ref={GITHUB_BRANCH}", token)
        return result.get("sha")
    except RuntimeError as e:
        if "404" in str(e):
            return None  # File doesn't exist yet
        raise


def commit_file(token, repo_path, content, message):
    """Create or update a file via GitHub Contents API."""
    sha = get_file_sha(token, repo_path)
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": message,
        "content": encoded,
        "branch": GITHUB_BRANCH,
        "committer": {
            "name": "s3rv3rl3ss-bot",
            "email": "s3rv3rl3ss-bot@automated.dev",
        },
    }
    if sha:
        payload["sha"] = sha

    github_api("PUT", f"contents/{repo_path}", token, payload)


def lambda_handler(event, context):
    # Extract S3 key from EventBridge event
    s3_key = None
    if "detail" in event:
        s3_key = event["detail"].get("object", {}).get("key")

    if not s3_key:
        # Fallback: commit all known files
        s3_key = None

    token = get_token()

    if s3_key and s3_key.startswith(S3_TO_REPO_MAP):
        # Single file mode: commit just the file that triggered the event
        filename = s3_key[len(S3_TO_REPO_MAP):]
        repo_path = f"{REPO_PREFIX}{filename}"

        try:
            resp = s3.get_object(Bucket=BUCKET, Key=s3_key)
            content = resp["Body"].read().decode("utf-8")
        except Exception as e:
            return {"statusCode": 500, "body": f"Error reading {s3_key}: {e}"}

        # Check if content actually changed
        sha_before = get_file_sha(token, repo_path)
        if sha_before:
            # Compare content
            existing = github_api("GET", f"contents/{repo_path}?ref={GITHUB_BRANCH}", token)
            existing_content = base64.b64decode(existing["content"]).decode("utf-8")
            if existing_content == content:
                return {"statusCode": 200, "body": f"No changes for {filename}"}

        commit_file(token, repo_path, content, f"chore: update {filename} [automated]")
        return {"statusCode": 200, "body": f"Committed {filename}"}

    else:
        # Batch mode: commit all data/ files from S3
        files_committed = []
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET, Prefix=S3_TO_REPO_MAP):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if not key.endswith(".json"):
                    continue
                filename = key[len(S3_TO_REPO_MAP):]
                repo_path = f"{REPO_PREFIX}{filename}"

                try:
                    resp = s3.get_object(Bucket=BUCKET, Key=key)
                    content = resp["Body"].read().decode("utf-8")

                    # Check if changed
                    existing_sha = get_file_sha(token, repo_path)
                    if existing_sha:
                        existing = github_api("GET", f"contents/{repo_path}?ref={GITHUB_BRANCH}", token)
                        existing_content = base64.b64decode(existing["content"]).decode("utf-8")
                        if existing_content == content:
                            continue

                    commit_file(token, repo_path, content, f"chore: update {filename} [automated]")
                    files_committed.append(filename)
                except Exception as e:
                    print(f"[committer] Error with {key}: {e}")

        return {"statusCode": 200, "body": f"Committed {len(files_committed)} files: {files_committed}"}
