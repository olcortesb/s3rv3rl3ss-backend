from collections import Counter


def build_statistics(services):
    total_quotas = 0
    total_limits = 0
    total_news = 0
    total_runtimes = 0
    active_runtimes = 0
    deprecated_runtimes = 0
    categories = Counter()
    quota_counts = {}
    news_counts = {}
    limit_counts = {}

    for svc in services:
        categories[svc.get("category", "Other")] += 1

        limits = svc.get("limits", [])
        api_quotas = [l for l in limits if l.get("description")]
        static = [l for l in limits if not l.get("description")]

        total_quotas += len(api_quotas)
        total_limits += len(static)
        quota_counts[svc["id"]] = {"name": svc["name"], "count": len(api_quotas)}
        limit_counts[svc["id"]] = {"name": svc["name"], "count": len(static)}

        news = svc.get("news", [])
        total_news += len(news)
        news_counts[svc["id"]] = {"name": svc["name"], "count": len(news)}

        runtimes = svc.get("runtimes", [])
        total_runtimes += len(runtimes)
        for rt in runtimes:
            if rt.get("status") == "deprecated":
                deprecated_runtimes += 1
            else:
                active_runtimes += 1

    most_quotas = max(quota_counts.items(), key=lambda x: x[1]["count"])
    most_news = max(news_counts.items(), key=lambda x: x[1]["count"])
    most_limits = max(limit_counts.items(), key=lambda x: x[1]["count"])

    return {
        "summary": {
            "totalServices": len(services),
            "totalQuotas": total_quotas,
            "totalLimits": total_limits,
            "totalNews": total_news,
            "totalRuntimes": total_runtimes,
            "activeRuntimes": active_runtimes,
            "deprecatedRuntimes": deprecated_runtimes,
        },
        "topServices": {
            "mostQuotas": {"id": most_quotas[0], "name": most_quotas[1]["name"], "count": most_quotas[1]["count"]},
            "mostNews": {"id": most_news[0], "name": most_news[1]["name"], "count": most_news[1]["count"]},
            "mostLimits": {"id": most_limits[0], "name": most_limits[1]["name"], "count": most_limits[1]["count"]},
        },
        "byCategory": sorted(
            [{"category": cat, "count": count} for cat, count in categories.items()],
            key=lambda x: x["count"],
            reverse=True,
        ),
    }
