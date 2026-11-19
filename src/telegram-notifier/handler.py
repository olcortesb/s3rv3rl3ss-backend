"""
Telegram Notifier — sends daily changelog and security bulletins to public channels.
Runs at 07:10 UTC, after all collectors and changelog generator finish.

Strategy:
- Reads yesterday's items from changelog-{provider}.json in S3
- Reads yesterday's security bulletins from security.json in S3
- Only sends if there are changes — no message if nothing new
- History is preserved in each channel
"""

import json
import os
import re
import urllib.request
import urllib.error
from datetime import date, timedelta

import boto3

s3 = boto3.client("s3")
secretsmanager = boto3.client("secretsmanager")

BUCKET = os.environ["BUCKET_NAME"]
SECRET_ARN = os.environ["TELEGRAM_SECRET_ARN"]

PROVIDERS = ["aws", "gcp", "azure", "stackit"]
CHANGELOG_KEYS = {
    "aws": "data/changelog.json",
    "gcp": "data/changelog-gcp.json",
    "azure": "data/changelog-azure.json",
    "stackit": "data/changelog-stackit.json",
}
PROVIDER_EMOJI = {"aws": "🟠", "gcp": "🔵", "azure": "🔷", "stackit": "🟢"}
SEVERITY_EMOJI = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}


def _get_secret():
    resp = secretsmanager.get_secret_value(SecretId=SECRET_ARN)
    return json.loads(resp["SecretString"])


def _tg(method, bot_token, payload):
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"[telegram] {method} error: {e.code} {e.reason} — {body}")
        return {"ok": False}
    except Exception as e:
        print(f"[telegram] {method} error: {e}")
        return {"ok": False}


def send_message(bot_token, chat_id, text):
    result = _tg("sendMessage", bot_token, {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    })
    if result.get("ok"):
        return result["result"]["message_id"]
    print(f"[telegram] sendMessage failed: {result}")
    return None


def _read_s3_json(key):
    try:
        resp = s3.get_object(Bucket=BUCKET, Key=key)
        return json.loads(resp["Body"].read().decode("utf-8"))
    except Exception as e:
        print(f"[s3] error reading {key}: {e}")
        return None


def _target_date():
    """Pipeline runs at 07:00 UTC collecting previous day's data."""
    return (date.today() - timedelta(days=1)).isoformat()


def get_changes(provider):
    target = _target_date()
    data = _read_s3_json(CHANGELOG_KEYS[provider])
    if not data:
        return []
    return [c for c in data.get("changes", []) if c.get("date") == target]


def get_security(provider=None):
    target = _target_date()
    data = _read_s3_json("data/security.json")
    if not data:
        return []
    bulletins = [b for b in data.get("bulletins", []) if b.get("date") == target]
    if provider:
        bulletins = [b for b in bulletins if b.get("provider") == provider]
    return bulletins


def _clean(text):
    """Remove HTML tags not supported by Telegram."""
    text = re.sub(r'<br\s*/?>', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'<(?!/?(?:b|i|a|code|pre)(?:\s|>|/))[^>]+>', '', text)
    return text.strip()


def format_changelog_message(provider, changes):
    target = _target_date()
    emoji = PROVIDER_EMOJI.get(provider, "⚪")
    lines = [f"{emoji} <b>{provider.upper()} Changelog — {target}</b>\n"]
    for c in changes:
        service = _clean(c.get("service", ""))
        detail = _clean(c.get("detail", ""))
        change_type = c.get("type", "")
        url = c.get("url", "")
        line = f"• <b>{service}</b>: {detail}"
        if change_type:
            line += f" <i>({change_type})</i>"
        if url:
            line += f'\n  <a href="{url}">↗ details</a>'
        lines.append(line)
    lines.append(f'\n🔗 <a href="https://s3rv3rl3ss.olcortesb.com">s3rv3rl3ss.olcortesb.com</a>')
    return "\n".join(lines)


def format_security_message(bulletin):
    provider = bulletin.get("provider", "").upper()
    tag = bulletin.get("tag", "security")
    severity = bulletin.get("severity", "")
    title = bulletin.get("title", "")
    url = bulletin.get("url", "")
    sev_emoji = SEVERITY_EMOJI.get(severity.lower(), "🔒") if severity else "🔒"
    tag_label = "Incident" if tag == "incident" else "Security"
    text = f'{sev_emoji} <b>[{provider} {tag_label}]</b>'
    if severity:
        text += f' — <i>{severity.upper()}</i>'
    text += f'\n{title}'
    if url:
        text += f'\n<a href="{url}">↗ advisory</a>'
    text += f'\n🔗 <a href="https://s3rv3rl3ss.olcortesb.com">s3rv3rl3ss.olcortesb.com</a>'
    return text


def send_provider_channel(bot_token, chat_id, provider):
    changes = get_changes(provider)
    security = get_security(provider)

    if not changes and not security:
        print(f"[{provider}] no changes, skipping")
        return

    sent = 0
    if changes:
        for i in range(0, len(changes), 15):
            chunk = changes[i:i + 15]
            msg_id = send_message(bot_token, chat_id, format_changelog_message(provider, chunk))
            if msg_id:
                sent += 1

    for bulletin in security[:10]:
        msg_id = send_message(bot_token, chat_id, format_security_message(bulletin))
        if msg_id:
            sent += 1

    print(f"[{provider}] sent {sent} messages ({len(changes)} changes, {len(security)} security)")


def send_security_channel(bot_token, chat_id):
    bulletins = get_security()

    if not bulletins:
        print("[security] no bulletins, skipping")
        return

    sent = 0
    for bulletin in bulletins[:20]:
        msg_id = send_message(bot_token, chat_id, format_security_message(bulletin))
        if msg_id:
            sent += 1

    print(f"[security] sent {sent} messages")


def lambda_handler(event, context):
    secret = _get_secret()
    bot_token = secret["bot_token"]
    channels = secret["channels"]

    results = {}

    for provider in PROVIDERS:
        chat_id = channels.get(provider)
        if not chat_id:
            print(f"[{provider}] no channel configured, skipping")
            continue
        try:
            send_provider_channel(bot_token, chat_id, provider)
            results[provider] = "ok"
        except Exception as e:
            print(f"[{provider}] error: {e}")
            results[provider] = str(e)

    security_chat_id = channels.get("security")
    if security_chat_id:
        try:
            send_security_channel(bot_token, security_chat_id)
            results["security"] = "ok"
        except Exception as e:
            print(f"[security] error: {e}")
            results["security"] = str(e)

    return {"statusCode": 200, "body": json.dumps(results)}
