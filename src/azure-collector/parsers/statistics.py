from collections import Counter


def build_statistics(services):
    total_runtimes = 0
    active_runtimes = 0
    deprecated_runtimes = 0
    categories = Counter()

    for svc in services:
        categories[svc.get("category", "Other")] += 1
        runtimes = svc.get("runtimes", [])
        total_runtimes += len(runtimes)
        for rt in runtimes:
            if rt.get("status") == "deprecated":
                deprecated_runtimes += 1
            else:
                active_runtimes += 1

    return {
        "summary": {
            "totalServices": len(services),
            "totalRuntimes": total_runtimes,
            "activeRuntimes": active_runtimes,
            "deprecatedRuntimes": deprecated_runtimes,
        },
        "byCategory": sorted(
            [{"category": cat, "count": count} for cat, count in categories.items()],
            key=lambda x: x["count"],
            reverse=True,
        ),
    }
