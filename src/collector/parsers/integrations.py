import boto3

FRIENDLY_NAMES = {
    # AppSync
    "AWS_LAMBDA": "AWS Lambda",
    "AMAZON_DYNAMODB": "Amazon DynamoDB",
    "AMAZON_ELASTICSEARCH": "Amazon OpenSearch (legacy)",
    "AMAZON_OPENSEARCH_SERVICE": "Amazon OpenSearch Service",
    "RELATIONAL_DATABASE": "Amazon Aurora Serverless (RDS)",
    "HTTP": "HTTP Endpoints",
    "AMAZON_EVENTBRIDGE": "Amazon EventBridge",
    "AMAZON_BEDROCK_RUNTIME": "Amazon Bedrock",
    "NONE": "Local Resolvers",
    # API Gateway IntegrationType
    "AWS": "AWS Service",
    "AWS_PROXY": "AWS Lambda Proxy",
    "HTTP_PROXY": "HTTP Proxy",
    "MOCK": "Mock",
    # API Gateway EndpointType
    "REGIONAL": "Regional",
    "EDGE": "Edge-Optimized",
    "PRIVATE": "Private",
    # API Gateway AuthorizerType
    "TOKEN": "Token",
    "REQUEST": "Request",
    "COGNITO_USER_POOLS": "Cognito User Pools",
    # Cognito IdentityProviderTypeType
    "SAML": "SAML",
    "Facebook": "Facebook",
    "Google": "Google",
    "LoginWithAmazon": "Login with Amazon",
    "SignInWithApple": "Sign in with Apple",
    "OIDC": "OIDC",
    # DynamoDB StreamViewType
    "NEW_IMAGE": "New Image",
    "OLD_IMAGE": "Old Image",
    "NEW_AND_OLD_IMAGES": "New and Old Images",
    "KEYS_ONLY": "Keys Only",
    # S3 events (simplified)
    "s3:ObjectCreated:*": "Object Created",
    "s3:ObjectRemoved:*": "Object Removed",
    "s3:ObjectRestore:*": "Object Restore",
    "s3:Replication:*": "Replication",
    "s3:LifecycleExpiration:*": "Lifecycle Expiration",
    "s3:LifecycleTransition": "Lifecycle Transition",
    "s3:IntelligentTiering": "Intelligent Tiering",
    "s3:ObjectTagging:*": "Object Tagging",
}

# S3 events: only show top-level wildcard events
S3_EVENT_FILTER = lambda v: v.endswith(":*") or v in ("s3:LifecycleTransition", "s3:IntelligentTiering", "s3:ReducedRedundancyLostObject", "s3:ObjectAcl:Put")

FILTERS = {
    "s3": S3_EVENT_FILTER,
}


def fetch_integrations(service_id, sdk_client_name, shape_name):
    try:
        client = boto3.client(sdk_client_name, region_name='us-east-1')
        service_model = client._service_model
        shape = service_model.shape_for(shape_name)
        filter_fn = FILTERS.get(service_id)
        integrations = []
        for value in shape.enum:
            if filter_fn and not filter_fn(value):
                continue
            integrations.append({
                "id": value,
                "name": FRIENDLY_NAMES.get(value, value.replace("_", " ").title()),
            })
        print(f"[{service_id}] Got {len(integrations)} integrations from SDK")
        return integrations
    except Exception as e:
        print(f"[{service_id}] Error fetching integrations: {e}")
        return None
