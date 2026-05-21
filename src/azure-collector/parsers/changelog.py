import json
from datetime import date


def _diff_quotas(old_limits, new_limits):
    changes = []
    old_map = {l["name"]: l["value"] for l in old_limits}
    new_map = {l["name"]: l["value"] for l in new_limits}

    for name, new_val in new_map.items():
        old_val = old_map.get(name)
        if old_val is None:
            changes.append({"type": "quota_added", "detail": f"{name}: {new_val}"})
        elif old_val != new_val:
            changes.append({"type": "quota_changed", "detail": f"{name}: {old_val} → {new_val}"})

    for name in old_map:
        if name not in new_map:
            changes.append({"type": "quota_removed", "detail": f"{name} removed"})

    return changes


def _diff_runtimes(old_rts, new_rts):
    changes = []
    old_map = {r["name"]: r.get("status") for r in old_rts}
    new_map = {r["name"]: r.get("status") for r in new_rts}

    for name, status in new_map.items():
        if name not in old_map:
            changes.append({"type": "new_runtime", "detail": f"{name} added ({status})"})
        elif old_map[name] != status:
            changes.append({"type": "runtime_changed", "detail": f"{name}: {old_map[name]} → {status}"})

    for name in old_map:
        if name not in new_map:
            changes.append({"type": "runtime_removed", "detail": f"{name} removed"})

    return changes


def _diff_news(old_news, new_news):
    old_titles = {n["title"] for n in old_news}
    changes = []
    for n in new_news:
        if n["title"] not in old_titles:
            entry = {"type": "new_news", "detail": n["title"]}
            if n.get("url"):
                entry["url"] = n["url"]
            changes.append(entry)
    return changes


def build_changelog(old_services, new_services, existing_changelog=None, max_days=90):
    today = date.today().isoformat()
    old_map = {s["id"]: s for s in old_services}

    new_changes = []
    for svc in new_services:
        old = old_map.get(svc["id"])
        if not old:
            new_changes.append({"date": today, "service": svc["id"], "type": "service_added", "detail": svc["name"]})
            continue

        changes = []
        changes.extend(_diff_quotas(old.get("limits", []), svc.get("limits", [])))
        changes.extend(_diff_runtimes(old.get("runtimes", []), svc.get("runtimes", [])))
        changes.extend(_diff_news(old.get("news", []), svc.get("news", [])))

        for c in changes:
            new_changes.append({"date": today, "service": svc["id"], **c})

    # Merge with existing changelog
    changelog = existing_changelog or []
    changelog = new_changes + changelog

    # Trim to max_days
    cutoff = date.today().isoformat()[:8]  # YYYY-MM prefix
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=max_days)).isoformat()
    changelog = [c for c in changelog if c["date"] >= cutoff]

    return changelog
