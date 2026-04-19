# Operations

Technical commands for building, deploying, testing and troubleshooting.

## Build

```bash
# Using the helper script (handles ECR login)
./scripts/build.sh

# Or manually
aws ecr-public get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin public.ecr.aws

sam build
```

## Deploy

```bash
# Using the helper script
./scripts/build.sh deploy

# Or manually
sam deploy --config-file samconfig.local.toml
```

## Test locally

```bash
sam build

# Test Collector (EventBridge event)
sam local invoke CollectorFunction -e events/collector.json

# Test Committer (S3 event)
sam local invoke CommitterFunction -e events/committer.json
```

## Get deployed function names

```bash
aws cloudformation describe-stack-resources \
  --stack-name s3rv3rl3ss-backend \
  --region us-east-1 \
  --query "StackResources[?ResourceType=='AWS::Lambda::Function'].[LogicalResourceId,PhysicalResourceId]" \
  --output table
```

## Invoke Collector Lambda

Triggers the full pipeline: Collector → S3 → Committer → Git push.

```bash
aws lambda invoke \
  --function-name s3rv3rl3ss-backend-CollectorFunction-xxx \
  --payload file://events/collector.json \
  --cli-binary-format raw-in-base64-out \
  --region us-east-1 \
  output.json && cat output.json
```

## Check logs

```bash
# Collector logs
aws logs tail /aws/lambda/s3rv3rl3ss-backend-CollectorFunction-xxx \
  --region us-east-1 --since 5m

# Committer logs
aws logs tail /aws/lambda/s3rv3rl3ss-backend-CommitterFunction-xxx \
  --region us-east-1 --since 5m
```

## Verify S3 output

```bash
# View generated JSON
aws s3 cp s3://s3rv3rl3ss-data-<account-id>/data/services-aws.json - \
  --region us-east-1 | python3 -m json.tool | head -80

# Count quotas per service
aws s3 cp s3://s3rv3rl3ss-data-<account-id>/data/services-aws.json - \
  --region us-east-1 | python3 -c "
import json, sys
data = json.load(sys.stdin)
for svc in data['services']:
    limits = svc.get('limits', [])
    api = len([l for l in limits if 'description' in l])
    static = len(limits) - api
    print(f\"{svc['id']}: {api} API quotas + {static} static = {len(limits)} total\")
"

# Search for a specific quota
aws s3 cp s3://s3rv3rl3ss-data-<account-id>/data/services-aws.json - \
  --region us-east-1 | python3 -m json.tool | grep -A3 "concurrent"
```

## Managing services (services.py)

Services are defined in `src/collector/services.py`. The file has two lists:

- `SERVICES` — active services that will be collected and published
- `DISABLED_SERVICES` — services ready to be enabled

### Enable a service

Move the service block from `DISABLED_SERVICES` to `SERVICES`, then build and deploy:

```bash
# Edit services.py
vim src/collector/services.py

# Verify syntax
python3 -c "
import ast
with open('src/collector/services.py') as f:
    ast.parse(f.read())
print('Syntax OK')
"

# Check which services are active
python3 -c "
from src.collector.services import SERVICES, DISABLED_SERVICES
print('Active:', [s['id'] for s in SERVICES])
print('Disabled:', [s['id'] for s in DISABLED_SERVICES])
"

# Build and deploy
./scripts/build.sh deploy
```

### Service format

Each service entry follows this structure:

```python
{
    "id": "service-id",              # URL-friendly identifier
    "name": "Service Name",          # Display name
    "category": "Category",          # Compute, Database, Integration, etc.
    "service_code": "service-code",  # AWS Service Quotas API code
    "description": "...",            # Short description
    "useCases": ["use1", "use2"],    # List of use cases
    "pricing": "Pay per ...",        # Pricing summary
    "url": "https://aws...",         # AWS product page
    "icon": "emoji",                 # Emoji icon
    "static_limits": [               # Limits not available in Service Quotas API
        {"name": "Limit name", "value": "Limit value"},
    ],
    "runtimes": [                    # Optional, only for Lambda
        {"name": "Python 3.13", "status": "active"},
    ],
}
```

### Find the service_code for a new service

```bash
aws service-quotas list-services \
  --region us-east-1 \
  --query "Services[].[ServiceCode,ServiceName]" \
  --output table | grep -i "service name"
```

### Preview quotas for a service

```bash
aws service-quotas list-service-quotas \
  --service-code lambda \
  --region us-east-1 \
  --query "Quotas[].[QuotaName,Value,Unit]" \
  --output table

# Some services only have default quotas (not applied to account)
aws service-quotas list-aws-default-service-quotas \
  --service-code sqs \
  --region us-east-1 \
  --query "Quotas[].[QuotaName,Value,Unit]" \
  --output table
```

## News feed

The Collector fetches the latest news from the AWS What's New RSS feed and filters by `news_keywords` defined in each service.

```bash
# Preview the RSS feed
curl -sL "https://aws.amazon.com/about-aws/whats-new/recent/feed/" | \
  python3 -c "
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.stdin).getroot()
for item in list(root.iter('item'))[:10]:
    print(item.findtext('title'))
"

# Filter for a specific service
curl -sL "https://aws.amazon.com/about-aws/whats-new/recent/feed/" | \
  python3 -c "
import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.stdin).getroot()
for item in root.iter('item'):
    title = item.findtext('title', '')
    if 'lambda' in title.lower():
        print(f\"{item.findtext('pubDate', '')[:16]}  {title}\")
"

## Update git token

If you need to rotate the GitHub token:

```bash
aws secretsmanager update-secret \
  --secret-id s3rv3rl3ss/git-token \
  --secret-string '{"token": "github_pat_NEW_TOKEN"}' \
  --region us-east-1
```

No redeploy needed — the Lambda reads the secret on each invocation.

## Force Lambda cold start (without redeploy)

If the Lambda is using cached code after a deploy, force a cold start:

```bash
# Collector
aws lambda update-function-configuration \
  --function-name s3rv3rl3ss-backend-CollectorFunction-xxx \
  --environment "Variables={BUCKET_NAME=s3rv3rl3ss-data-<account-id>,S3_KEY=data/services-aws.json,FORCE=$(date +%s)}" \
  --region us-east-1

# Committer
aws lambda update-function-configuration \
  --function-name s3rv3rl3ss-backend-CommitterFunction-xxx \
  --environment "Variables={BUCKET_NAME=s3rv3rl3ss-data-<account-id>,S3_KEY=data/services-aws.json,GIT_REPO_URL=https://github.com/<user>/<repo>.git,GIT_SECRET_ARN=<secret-arn>,DEST_PATH=src/data/services-aws.json,FORCE=$(date +%s)}" \
  --region us-east-1
```

## Delete stack

```bash
# Empty the S3 bucket first
aws s3 rm s3://s3rv3rl3ss-data-<account-id> --recursive --region us-east-1

# Delete the stack
aws cloudformation delete-stack --stack-name s3rv3rl3ss-backend --region us-east-1
```
