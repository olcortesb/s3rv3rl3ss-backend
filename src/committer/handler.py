import json
import os
import subprocess
import tempfile

import boto3

s3 = boto3.client('s3')
sm = boto3.client('secretsmanager')

BUCKET = os.environ['BUCKET_NAME']
S3_KEY = os.environ['S3_KEY']
GIT_REPO_URL = os.environ['GIT_REPO_URL']
GIT_SECRET_ARN = os.environ['GIT_SECRET_ARN']
DEST_PATH = os.environ['DEST_PATH']


def get_git_token():
    resp = sm.get_secret_value(SecretId=GIT_SECRET_ARN)
    secret = json.loads(resp['SecretString'])
    return secret['token']


def run(cmd, cwd=None):
    env = os.environ.copy()
    env['PATH'] = '/opt/bin:' + env.get('PATH', '')
    env['LD_LIBRARY_PATH'] = '/opt/lib:' + env.get('LD_LIBRARY_PATH', '')
    env['GIT_TEMPLATE_DIR'] = '/opt/share/git-core/templates'
    env['GIT_EXEC_PATH'] = '/opt/bin'
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=120, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def lambda_handler(event, context):
    token = get_git_token()

    # Build authenticated URL
    # Supports https://github.com/user/repo.git format
    auth_url = GIT_REPO_URL.replace('https://', f'https://x-access-token:{token}@')

    # Download JSON from S3
    resp = s3.get_object(Bucket=BUCKET, Key=S3_KEY)
    content = resp['Body'].read().decode('utf-8')

    git_bin = '/opt/bin/git'

    with tempfile.TemporaryDirectory() as tmp:
        run([git_bin, 'clone', '--depth', '1', auth_url, tmp])
        run([git_bin, 'config', 'user.email', 's3rv3rl3ss-bot@automated.dev'], cwd=tmp)
        run([git_bin, 'config', 'user.name', 's3rv3rl3ss-bot'], cwd=tmp)

        dest = os.path.join(tmp, DEST_PATH)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        with open(dest, 'w', encoding='utf-8') as f:
            f.write(content)

        # Check if there are changes
        diff = run([git_bin, 'diff', '--name-only'], cwd=tmp)
        if not diff:
            return {"statusCode": 200, "body": "No changes to commit"}

        run([git_bin, 'add', DEST_PATH], cwd=tmp)
        run([git_bin, 'commit', '-m', 'chore: update services-aws.json [automated]'], cwd=tmp)
        run([git_bin, 'push'], cwd=tmp)

    return {"statusCode": 200, "body": "Committed and pushed changes"}
