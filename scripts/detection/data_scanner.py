#!/usr/bin/env python3
"""
Data Scanner — Sensitive data discovery tool for the Security Operations Lab.

Scans directories for PII, credentials, and compliance-relevant data patterns.
Outputs results as JSON for Wazuh log ingestion and as a human-readable report.

Usage:
    python3 data_scanner.py --path /target/directory --profile configs/opendlp/scan-profiles.yaml
    python3 data_scanner.py --path /target/directory --output /var/log/opendlp/scan-results.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


# Built-in patterns (used when no profile YAML is provided)
DEFAULT_PATTERNS = {
    "SSN": {
        "regex": r"\b\d{3}-\d{2}-\d{4}\b",
        "severity": "critical",
        "description": "Social Security Number",
    },
    "Credit Card": {
        "regex": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "severity": "critical",
        "description": "Credit/debit card number",
    },
    "AWS Access Key": {
        "regex": r"AKIA[0-9A-Z]{16}",
        "severity": "critical",
        "description": "AWS IAM access key ID",
    },
    "Generic Password": {
        "regex": r"(?i)(password|passwd|pwd)\s*[=:]\s*\S+",
        "severity": "high",
        "description": "Plaintext password in configuration",
    },
    "Private Key": {
        "regex": r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----",
        "severity": "critical",
        "description": "Private key file header",
    },
    "Email Address": {
        "regex": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "severity": "medium",
        "description": "Email address",
    },
}

# File extensions to scan (skip binaries, images, archives)
SCANNABLE_EXTENSIONS = {
    ".txt", ".csv", ".json", ".xml", ".yaml", ".yml",
    ".conf", ".cfg", ".ini", ".env", ".log", ".md",
    ".py", ".js", ".sh", ".sql", ".html", ".properties",
}

MAX_FILE_SIZE_MB = 50


def load_profiles(profile_path: str) -> dict:
    """Load scan profiles from a YAML config file."""
    with open(profile_path) as f:
        config = yaml.safe_load(f)

    patterns = {}
    for profile in config.get("profiles", []):
        for pattern in profile.get("patterns", []):
            name = pattern["name"]
            if name not in patterns:
                patterns[name] = {
                    "regex": pattern["regex"],
                    "severity": pattern.get("severity", "medium"),
                    "description": name,
                }
    return patterns


def scan_file(filepath: Path, patterns: dict) -> list:
    """Scan a single file against all patterns. Returns list of findings."""
    findings = []

    if filepath.stat().st_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        return findings

    try:
        content = filepath.read_text(errors="ignore")
    except (PermissionError, OSError):
        return findings

    for line_num, line in enumerate(content.splitlines(), start=1):
        for pattern_name, pattern_info in patterns.items():
            matches = re.finditer(pattern_info["regex"], line)
            for match in matches:
                # Mask the matched value for safe logging
                matched_text = match.group()
                if len(matched_text) > 8:
                    masked = matched_text[:4] + "*" * (len(matched_text) - 8) + matched_text[-4:]
                else:
                    masked = "*" * len(matched_text)

                findings.append({
                    "file": str(filepath),
                    "line": line_num,
                    "pattern": pattern_name,
                    "severity": pattern_info["severity"],
                    "description": pattern_info["description"],
                    "matched_value_masked": masked,
                })

    return findings


def scan_directory(target_path: str, patterns: dict) -> list:
    """Recursively scan a directory for sensitive data."""
    all_findings = []
    target = Path(target_path)

    if not target.exists():
        print(f"Error: path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    for filepath in target.rglob("*"):
        if not filepath.is_file():
            continue
        if filepath.suffix.lower() not in SCANNABLE_EXTENSIONS:
            continue

        findings = scan_file(filepath, patterns)
        all_findings.extend(findings)

    return all_findings


def generate_report(findings: list, target_path: str) -> dict:
    """Generate a structured scan report."""
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "medium")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "scan_metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_path": target_path,
            "total_findings": len(findings),
            "severity_summary": severity_counts,
        },
        "findings": findings,
    }


def write_wazuh_logs(findings: list, output_path: str):
    """Write findings as individual JSON log lines for Wazuh ingestion."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "a") as f:
        for finding in findings:
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "scan_type": "data-discovery",
                "severity": finding["severity"],
                "pattern": finding["pattern"],
                "file": finding["file"],
                "line": finding["line"],
                "description": finding["description"],
            }
            f.write(json.dumps(log_entry) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Scan directories for sensitive data patterns")
    parser.add_argument("--path", required=True, help="Directory to scan")
    parser.add_argument("--profile", help="YAML scan profile (defaults to built-in patterns)")
    parser.add_argument("--output", help="Path for Wazuh-compatible JSON log output")
    parser.add_argument("--report", help="Path to write the full scan report (JSON)")
    args = parser.parse_args()

    # Load patterns
    if args.profile and os.path.exists(args.profile):
        patterns = load_profiles(args.profile)
        print(f"Loaded {len(patterns)} patterns from {args.profile}")
    else:
        patterns = DEFAULT_PATTERNS
        print(f"Using {len(patterns)} built-in patterns")

    # Run the scan
    print(f"Scanning: {args.path}")
    findings = scan_directory(args.path, patterns)

    # Generate report
    report = generate_report(findings, args.path)

    # Console summary
    meta = report["scan_metadata"]
    print(f"\n{'='*50}")
    print(f"Scan Complete — {meta['total_findings']} findings")
    print(f"  Critical: {meta['severity_summary']['critical']}")
    print(f"  High:     {meta['severity_summary']['high']}")
    print(f"  Medium:   {meta['severity_summary']['medium']}")
    print(f"  Low:      {meta['severity_summary']['low']}")
    print(f"{'='*50}\n")

    for finding in findings:
        icon = {"critical": "[!]", "high": "[*]", "medium": "[-]", "low": "[.]"}.get(finding["severity"], "[ ]")
        print(f"  {icon} {finding['pattern']} in {finding['file']}:{finding['line']} — {finding['matched_value_masked']}")

    # Write outputs
    if args.output:
        write_wazuh_logs(findings, args.output)
        print(f"\nWazuh log written to {args.output}")

    if args.report:
        with open(args.report, "w") as f:
            json.dump(report, f, indent=2)
        print(f"Full report written to {args.report}")


if __name__ == "__main__":
    main()
