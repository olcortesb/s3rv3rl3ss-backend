from collections import Counter


def build_statistics(services):
    total_limits = 0
    total_news = 0
    total_runtimes = 0
    active_runtimes = 0
    deprecated_runtimes = 0
    total_pricing = 0
    categories = Counter()
    limits_counts = {}
    news_counts = {}

    for svc in services:
        categories[svc.get("category", "Other")] += 1

        limits = svc.get("limits", [])
        total_limits += len(limits)
        limits_counts[svc["id"]] = {"name": svc["name"], "count": len(limits)}

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

        pricing = svc.get("pricingDetails", [])
        total_pricing += len(pricing)

    top_services = {}
    if limits_counts:
        most_limits = max(limits_counts.items(), key=lambda x: x[1]["count"])
        if most_limits[1]["count"] > 0:
            top_services["mostLimits"] = {"id": most_limits[0], "name": most_limits[1]["name"], "count": most_limits[1]["count"]}
    if news_counts:
        most_news = max(news_counts.items(), key=lambda x: x[1]["count"])
        if most_news[1]["count"] > 0:
            top_services["mostNews"] = {"id": most_news[0], "name": most_news[1]["name"], "count": most_news[1]["count"]}

    return {
        "summary": {
            "totalServices": len(services),
            "totalLimits": total_limits,
            "totalNews": total_news,
            "totalPricing": total_pricing,
            "totalRuntimes": total_runtimes,
            "activeRuntimes": active_runtimes,
            "deprecatedRuntimes": deprecated_runtimes,
        },
        "topServices": top_services,
        "byCategory": sorted(
            [{"category": cat, "count": count} for cat, count in categories.items()],
            key=lambda x: x["count"],
            reverse=True,
        ),
    }
