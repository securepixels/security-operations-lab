#!/usr/bin/env python3
"""
Alert Analyzer — Query and analyze Wazuh alerts from the Indexer API.

Supports filtering by severity, time range, agent, and MITRE ATT&CK technique.
Generates summary reports for triage workflows.

Usage:
    python3 alert_analyzer.py --min-level 10 --hours 24
    python3 alert_analyzer.py --agent win10-endpoint --mitre T1059.001
    python3 alert_analyzer.py --summary --hours 48 --output report.json
"""

import argparse
import json
import sys
import urllib3
from collections import Counter
from datetime import datetime, timedelta, timezone

import requests

# Suppress self-signed cert warnings for the lab
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Wazuh Indexer connection defaults
INDEXER_URL = "https://192.168.56.10:9200"
INDEXER_USER = "admin"
INDEXER_PASS = "CHANGEME"  # Update after installation
INDEX_PATTERN = "wazuh-alerts-*"


def query_alerts(
    min_level: int = 0,
    hours: int = 24,
    agent_name: str = None,
    mitre_id: str = None,
    max_results: int = 500,
) -> list:
    """Query Wazuh Indexer for alerts matching the given filters."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)

    # Build the Elasticsearch query
    must_clauses = [
        {"range": {"timestamp": {"gte": start.isoformat(), "lte": now.isoformat()}}},
        {"range": {"rule.level": {"gte": min_level}}},
    ]

    if agent_name:
        must_clauses.append({"match": {"agent.name": agent_name}})

    if mitre_id:
        must_clauses.append({"match": {"rule.mitre.id": mitre_id}})

    query = {
        "size": max_results,
        "sort": [{"timestamp": {"order": "desc"}}],
        "query": {"bool": {"must": must_clauses}},
    }

    try:
        response = requests.post(
            f"{INDEXER_URL}/{INDEX_PATTERN}/_search",
            json=query,
            auth=(INDEXER_USER, INDEXER_PASS),
            verify=False,
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error querying Wazuh Indexer: {e}", file=sys.stderr)
        sys.exit(1)

    data = response.json()
    hits = data.get("hits", {}).get("hits", [])
    return [hit["_source"] for hit in hits]


def format_alert(alert: dict) -> str:
    """Format a single alert for console output."""
    rule = alert.get("rule", {})
    agent = alert.get("agent", {})
    timestamp = alert.get("timestamp", "unknown")
    mitre = rule.get("mitre", {}).get("id", [])

    level = rule.get("level", 0)
    if level >= 12:
        severity_icon = "[CRIT]"
    elif level >= 10:
        severity_icon = "[HIGH]"
    elif level >= 7:
        severity_icon = "[MED] "
    else:
        severity_icon = "[LOW] "

    mitre_str = ", ".join(mitre) if isinstance(mitre, list) else str(mitre)

    return (
        f"{severity_icon} [{timestamp}] "
        f"Rule {rule.get('id', '?')} (Level {level}) — "
        f"{rule.get('description', 'No description')} | "
        f"Agent: {agent.get('name', 'unknown')} | "
        f"MITRE: {mitre_str or 'N/A'}"
    )


def generate_summary(alerts: list) -> dict:
    """Generate a triage summary from a list of alerts."""
    if not alerts:
        return {"total": 0, "message": "No alerts found for the given filters."}

    level_counts = Counter()
    agent_counts = Counter()
    rule_counts = Counter()
    mitre_counts = Counter()

    for alert in alerts:
        rule = alert.get("rule", {})
        agent = alert.get("agent", {})

        level = rule.get("level", 0)
        if level >= 12:
            level_counts["critical"] += 1
        elif level >= 10:
            level_counts["high"] += 1
        elif level >= 7:
            level_counts["medium"] += 1
        else:
            level_counts["low"] += 1

        agent_counts[agent.get("name", "unknown")] += 1
        rule_counts[rule.get("description", "Unknown rule")] += 1

        mitre_ids = rule.get("mitre", {}).get("id", [])
        if isinstance(mitre_ids, list):
            for mid in mitre_ids:
                mitre_counts[mid] += 1

    return {
        "time_range_hours": None,  # Filled by caller
        "total_alerts": len(alerts),
        "severity_breakdown": dict(level_counts),
        "top_rules": dict(rule_counts.most_common(10)),
        "alerts_by_agent": dict(agent_counts),
        "mitre_techniques": dict(mitre_counts.most_common(10)),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze Wazuh alerts")
    parser.add_argument("--min-level", type=int, default=5, help="Minimum rule level (default: 5)")
    parser.add_argument("--hours", type=int, default=24, help="Look-back window in hours (default: 24)")
    parser.add_argument("--agent", help="Filter by agent name")
    parser.add_argument("--mitre", help="Filter by MITRE ATT&CK technique ID")
    parser.add_argument("--max-results", type=int, default=500, help="Max alerts to retrieve")
    parser.add_argument("--summary", action="store_true", help="Show summary report instead of individual alerts")
    parser.add_argument("--output", help="Write report to JSON file")
    parser.add_argument("--indexer-url", default=INDEXER_URL, help="Wazuh Indexer URL")
    parser.add_argument("--indexer-user", default=INDEXER_USER)
    parser.add_argument("--indexer-pass", default=INDEXER_PASS)
    args = parser.parse_args()

    # Override connection settings if provided
    global INDEXER_URL, INDEXER_USER, INDEXER_PASS
    INDEXER_URL = args.indexer_url
    INDEXER_USER = args.indexer_user
    INDEXER_PASS = args.indexer_pass

    print(f"Querying alerts (level >= {args.min_level}, last {args.hours}h)...")
    if args.agent:
        print(f"  Agent filter: {args.agent}")
    if args.mitre:
        print(f"  MITRE filter: {args.mitre}")

    alerts = query_alerts(
        min_level=args.min_level,
        hours=args.hours,
        agent_name=args.agent,
        mitre_id=args.mitre,
        max_results=args.max_results,
    )

    print(f"Retrieved {len(alerts)} alerts.\n")

    if args.summary:
        summary = generate_summary(alerts)
        summary["time_range_hours"] = args.hours

        print("=" * 60)
        print(f"ALERT SUMMARY — Last {args.hours} hours")
        print("=" * 60)
        print(f"Total Alerts: {summary['total_alerts']}")
        print(f"\nSeverity Breakdown:")
        for sev, count in sorted(summary.get("severity_breakdown", {}).items()):
            print(f"  {sev.upper():>10}: {count}")
        print(f"\nTop Rules:")
        for rule, count in summary.get("top_rules", {}).items():
            print(f"  [{count:>3}x] {rule}")
        print(f"\nAlerts by Agent:")
        for agent, count in summary.get("alerts_by_agent", {}).items():
            print(f"  {agent}: {count}")
        print(f"\nMITRE ATT&CK Techniques:")
        for tech, count in summary.get("mitre_techniques", {}).items():
            print(f"  {tech}: {count}")

        if args.output:
            with open(args.output, "w") as f:
                json.dump(summary, f, indent=2)
            print(f"\nReport saved to {args.output}")
    else:
        for alert in alerts:
            print(format_alert(alert))


if __name__ == "__main__":
    main()
