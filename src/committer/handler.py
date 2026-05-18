import json
import os
import subprocess
import tempfile

import boto3

s3 = boto3.client('s3')
sm = boto3.client('secretsmanager')

BUCKET = os.environ['BUCKET_NAME']
S3_KEY = os.environ['S3_KEY']
CHANGELOG_KEY = os.environ.get('CHANGELOG_KEY', 'data/changelog.json')
STATISTICS_KEY = os.environ.get('STATISTICS_KEY', 'data/statistics.json')
GIT_REPO_URL = os.environ['GIT_REPO_URL']
GIT_SECRET_ARN = os.environ['GIT_SECRET_ARN']
DEST_PATH = os.environ['DEST_PATH']
CHANGELOG_DEST = os.environ.get('CHANGELOG_DEST', 'src/data/changelog.json')
STATISTICS_DEST = os.environ.get('STATISTICS_DEST', 'src/data/statistics.json')
GCP_S3_KEY = os.environ.get('GCP_S3_KEY', 'data/services-gcp.json')
GCP_DEST = os.environ.get('GCP_DEST', 'src/data/services-gcp.json')
GCP_STATS_KEY = os.environ.get('GCP_STATS_KEY', 'data/statistics-gcp.json')
GCP_STATS_DEST = os.environ.get('GCP_STATS_DEST', 'src/data/statistics-gcp.json')
AZURE_S3_KEY = os.environ.get('AZURE_S3_KEY', 'data/services-azure.json')
AZURE_DEST = os.environ.get('AZURE_DEST', 'src/data/services-azure.json')
AZURE_STATS_KEY = os.environ.get('AZURE_STATS_KEY', 'data/statistics-azure.json')
AZURE_STATS_DEST = os.environ.get('AZURE_STATS_DEST', 'src/data/statistics-azure.json')
GCP_CHANGELOG_KEY = os.environ.get('GCP_CHANGELOG_KEY', 'data/changelog-gcp.json')
GCP_CHANGELOG_DEST = os.environ.get('GCP_CHANGELOG_DEST', 'src/data/changelog-gcp.json')
AZURE_CHANGELOG_KEY = os.environ.get('AZURE_CHANGELOG_KEY', 'data/changelog-azure.json')
AZURE_CHANGELOG_DEST = os.environ.get('AZURE_CHANGELOG_DEST', 'src/data/changelog-azure.json')


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

    # Download changelog from S3
    changelog_content = None
    try:
        resp2 = s3.get_object(Bucket=BUCKET, Key=CHANGELOG_KEY)
        changelog_content = resp2['Body'].read().decode('utf-8')
    except Exception:
        pass

    git_bin = '/opt/bin/git'

    with tempfile.TemporaryDirectory() as tmp:
        run([git_bin, 'clone', '--depth', '1', auth_url, tmp])
        run([git_bin, 'config', 'user.email', 's3rv3rl3ss-bot@automated.dev'], cwd=tmp)
        run([git_bin, 'config', 'user.name', 's3rv3rl3ss-bot'], cwd=tmp)

        dest = os.path.join(tmp, DEST_PATH)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        with open(dest, 'w', encoding='utf-8') as f:
            f.write(content)

        # Write changelog if available
        if changelog_content:
            changelog_dest = os.path.join(tmp, CHANGELOG_DEST)
            os.makedirs(os.path.dirname(changelog_dest), exist_ok=True)
            with open(changelog_dest, 'w', encoding='utf-8') as f:
                f.write(changelog_content)

        # Write statistics if available
        stats_content = None
        try:
            resp3 = s3.get_object(Bucket=BUCKET, Key=STATISTICS_KEY)
            stats_content = resp3['Body'].read().decode('utf-8')
        except Exception:
            pass

        if stats_content:
            stats_dest = os.path.join(tmp, STATISTICS_DEST)
            os.makedirs(os.path.dirname(stats_dest), exist_ok=True)
            with open(stats_dest, 'w', encoding='utf-8') as f:
                f.write(stats_content)

        # Write GCP files if available
        for s3_key, dest_path in [(GCP_S3_KEY, GCP_DEST), (GCP_STATS_KEY, GCP_STATS_DEST), (AZURE_S3_KEY, AZURE_DEST), (AZURE_STATS_KEY, AZURE_STATS_DEST), (GCP_CHANGELOG_KEY, GCP_CHANGELOG_DEST), (AZURE_CHANGELOG_KEY, AZURE_CHANGELOG_DEST)]:
            try:
                resp = s3.get_object(Bucket=BUCKET, Key=s3_key)
                gcp_content = resp['Body'].read().decode('utf-8')
                dest_file = os.path.join(tmp, dest_path)
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                with open(dest_file, 'w', encoding='utf-8') as f:
                    f.write(gcp_content)
            except Exception:
                pass

        # Check if there are changes
        diff = run([git_bin, 'diff', '--name-only'], cwd=tmp)
        if not diff:
            return {"statusCode": 200, "body": "No changes to commit"}

        run([git_bin, 'add', DEST_PATH, CHANGELOG_DEST, STATISTICS_DEST, GCP_DEST, GCP_STATS_DEST, AZURE_DEST, AZURE_STATS_DEST, GCP_CHANGELOG_DEST, AZURE_CHANGELOG_DEST], cwd=tmp)
        run([git_bin, 'commit', '-m', 'chore: update services and changelog [automated]'], cwd=tmp)
        run([git_bin, 'push'], cwd=tmp)

    return {"statusCode": 200, "body": "Committed and pushed changes"}
