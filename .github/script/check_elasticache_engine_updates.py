#!/usr/bin/env python3
"""Check CloudFormation ElastiCache EngineVersion values against cfn-lint internal engine data."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import cfnlint

from common import load_template_or_fail, natural_version_key, print_json_result, write_github_output


def cfn_lint_elasticache_engine_versions(engine: str) -> list[str]:
    base = Path(cfnlint.__file__).resolve().parent
    candidate_paths = [
        base
        / "data"
        / "schemas"
        / "extensions"
        / "aws_elasticache_replicationgroup"
        / "engine_version.json",
        # ReplicationGroup updates can be tracked with the same ElastiCache engine dataset
        # when a dedicated schema extension file is not available.
        base
        / "data"
        / "schemas"
        / "extensions"
        / "aws_elasticache_cachecluster"
        / "engine_version.json",
    ]

    data = {}
    for path in candidate_paths:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            break
    if not data:
        return []

    versions: set[str] = set()
    for block in data.get("allOf", []):
        when = block.get("if", {}).get("properties", {})
        target = when.get("Engine", {}).get("const")
        if target != engine:
            continue

        enum_values = (
            block.get("then", {})
            .get("properties", {})
            .get("EngineVersion", {})
            .get("enum", [])
        )
        versions.update(str(v) for v in enum_values)

    return sorted(versions, key=natural_version_key)


def extract_elasticache_resources(template: dict[str, Any]) -> list[dict[str, str]]:
    resources = template.get("Resources", {})
    results: list[dict[str, str]] = []
    for logical_id, resource in resources.items():
        if resource.get("Type") != "AWS::ElastiCache::ReplicationGroup":
            continue

        props = resource.get("Properties", {})
        engine = props.get("Engine")
        engine_version = props.get("EngineVersion")
        if isinstance(engine, str) and isinstance(engine_version, str):
            results.append(
                {
                    "logical_id": logical_id,
                    "engine": engine,
                    "current_version": engine_version,
                }
            )
    return results


def build_issue(updates: list[dict[str, str]], template_path: Path) -> tuple[str, str]:
    first = updates[0]
    title = (
        "chore: ElastiCache engine update available "
        f"({first['logical_id']} {first['current_version']} -> {first['latest_version']})"
    )
    lines = [
        "CloudFormation の ElastiCache エンジンバージョン更新候補が見つかりました。",
        "",
        f"Template: `{template_path}`",
        "",
        "| Logical ID | Engine | Current | Latest (cfn-lint data) |",
        "|---|---|---|---|",
    ]
    for u in updates:
        lines.append(
            f"| `{u['logical_id']}` | `{u['engine']}` | `{u['current_version']}` | `{u['latest_version']}` |"
        )
    lines.append("")
    lines.append(
        "この Issue は `.github/script/check_elasticache_engine_updates.py` により自動生成されました。"
    )
    return title, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="cloudformation.yml")
    parser.add_argument("--github-output", default=os.getenv("GITHUB_OUTPUT"))
    args = parser.parse_args()

    template_path = Path(args.template)
    template = load_template_or_fail(template_path)
    elasticache_resources = extract_elasticache_resources(template)

    updates: list[dict[str, str]] = []
    for resource in elasticache_resources:
        versions = cfn_lint_elasticache_engine_versions(resource["engine"])
        if not versions:
            continue
        latest = versions[-1]
        if natural_version_key(resource["current_version"]) < natural_version_key(latest):
            updates.append({**resource, "latest_version": latest})

    has_update = bool(updates)
    issue_title = ""
    issue_body = ""
    if has_update:
        issue_title, issue_body = build_issue(updates, template_path)

    result = {
        "has_update": has_update,
        "template": str(template_path),
        "updates": updates,
    }
    print_json_result(result)

    if args.github_output:
        write_github_output(
            args.github_output,
            {
                "has_update": "true" if has_update else "false",
                "issue_title": issue_title,
                "issue_body": issue_body,
            },
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
