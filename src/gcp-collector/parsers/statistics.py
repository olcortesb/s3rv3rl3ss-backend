from collections import Counter


def build_statistics(services):
    total_news = 0
    total_runtimes = 0
    active_runtimes = 0
    deprecated_runtimes = 0
    categories = Counter()
    news_counts = {}

    for svc in services:
        categories[svc.get("category", "Other")] += 1

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

    most_news = max(news_counts.items(), key=lambda x: x[1]["count"]) if news_counts else ("", {"name": "", "count": 0})

    return {
        "summary": {
            "totalServices": len(services),
            "totalNews": total_news,
            "totalRuntimes": total_runtimes,
            "activeRuntimes": active_runtimes,
            "deprecatedRuntimes": deprecated_runtimes,
        },
        "topServices": {
            "mostNews": {"id": most_news[0], "name": most_news[1]["name"], "count": most_news[1]["count"]},
        },
        "byCategory": sorted(
            [{"category": cat, "count": count} for cat, count in categories.items()],
            key=lambda x: x["count"],
            reverse=True,
        ),
    }
