#!/usr/bin/env python3
"""CloudFormation の RDS EngineVersion を cfn-lint の内部データと照合する。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import cfnlint

from common import load_template_or_fail, natural_version_key, print_json_result, write_github_output


def cfn_lint_rds_engine_versions(engine: str) -> list[str]:
    """指定した RDS エンジンで利用可能なバージョン一覧を cfn-lint データから読み込む。"""
    base = Path(cfnlint.__file__).resolve().parent
    path = base / "data" / "schemas" / "extensions" / "aws_rds_dbinstance" / "engine_version.json"
    data = json.loads(path.read_text(encoding="utf-8"))

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


def extract_rds_resources(template: dict[str, Any]) -> list[dict[str, str]]:
    """RDS DBInstance の Logical ID・Engine・EngineVersion を抽出する。"""
    resources = template.get("Resources", {})
    results: list[dict[str, str]] = []
    for logical_id, resource in resources.items():
        if resource.get("Type") != "AWS::RDS::DBInstance":
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
    """1 件以上の RDS エンジン更新候補を説明する Issue 情報を生成する。"""
    first = updates[0]
    title = (
        f"chore: RDS engine update available ({first['logical_id']} {first['current_version']} -> {first['latest_version']})"
    )
    lines = [
        "CloudFormation の RDS エンジンバージョン更新候補が見つかりました。",
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
    lines.append("この Issue は `.github/script/check_rds_engine_updates.py` により自動生成されました。")
    return title, "\n".join(lines)


def main() -> int:
    """RDS エンジン更新チェック CLI を実行し、構造化結果を出力する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="cloudformation.yml")
    parser.add_argument("--github-output", default=os.getenv("GITHUB_OUTPUT"))
    args = parser.parse_args()

    template_path = Path(args.template)
    template = load_template_or_fail(template_path)
    rds_resources = extract_rds_resources(template)

    updates: list[dict[str, str]] = []
    for r in rds_resources:
        versions = cfn_lint_rds_engine_versions(r["engine"])
        if not versions:
            continue
        latest = versions[-1]
        if natural_version_key(r["current_version"]) < natural_version_key(latest):
            updates.append({**r, "latest_version": latest})

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
