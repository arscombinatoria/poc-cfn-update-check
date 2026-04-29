#!/usr/bin/env python3
"""CloudFormation の Lambda Runtime を cfn-lint のスキーマデータと照合する。"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from cfnlint.schema.manager import ProviderSchemaManager

from common import load_template_or_fail, natural_version_key, print_json_result, write_github_output


def runtime_family_and_version(runtime: str) -> tuple[str, str]:
    """Lambda runtime 文字列をファミリ接頭辞とバージョン接尾辞に分割する。"""
    if runtime.startswith("provided.al"):
        return "provided.al", runtime.removeprefix("provided.al")

    patterns = ["python", "nodejs", "java", "dotnetcore", "dotnet", "ruby"]
    for prefix in patterns:
        if runtime.startswith(prefix):
            return prefix, runtime.removeprefix(prefix)

    return runtime, ""


def cfn_lint_lambda_runtimes(region: str = "us-east-1") -> list[str]:
    """cfn-lint のプロバイダースキーマから並び替え可能な Runtime 一覧を取得する。"""
    manager = ProviderSchemaManager()
    schema = manager.get_resource_schema(region, "AWS::Lambda::Function")
    runtimes = schema.schema.get("properties", {}).get("Runtime", {}).get("enum", [])
    return sorted((str(r) for r in runtimes), key=natural_version_key)


def latest_runtime_for_family(current_runtime: str, runtimes: list[str]) -> str | None:
    """現在の runtime と同じファミリ内で最新の runtime を返す。"""
    family, _ = runtime_family_and_version(current_runtime)

    family_runtimes = [r for r in runtimes if runtime_family_and_version(r)[0] == family]
    if not family_runtimes:
        return None

    return sorted(
        family_runtimes,
        key=lambda r: natural_version_key(runtime_family_and_version(r)[1]),
    )[-1]


def extract_lambda_resources(template: dict[str, Any]) -> list[dict[str, str]]:
    """テンプレートから Lambda の Logical ID と runtime 文字列を抽出する。"""
    resources = template.get("Resources", {})
    results: list[dict[str, str]] = []
    for logical_id, resource in resources.items():
        if resource.get("Type") != "AWS::Lambda::Function":
            continue

        props = resource.get("Properties", {})
        runtime = props.get("Runtime")
        if isinstance(runtime, str):
            results.append(
                {
                    "logical_id": logical_id,
                    "current_runtime": runtime,
                }
            )
    return results


def build_issue(update: dict[str, str], template_path: Path) -> tuple[str, str]:
    """検知した Lambda runtime 更新向けの Issue タイトルと本文を生成する。"""
    title = (
        "chore: Lambda runtime update available "
        f"({update['logical_id']} {update['current_runtime']} -> {update['latest_runtime']})"
    )
    lines = [
        "CloudFormation の Lambda ランタイム更新候補が見つかりました。",
        "",
        f"Template: `{template_path}`",
        "",
        "| Logical ID | Current Runtime | Latest (cfn-lint schema) |",
        "|---|---|---|",
        f"| `{update['logical_id']}` | `{update['current_runtime']}` | `{update['latest_runtime']}` |",
        "",
        "この Issue は `.github/script/check_lambda_runtime_updates.py` により自動生成されました。",
    ]
    return title, "\n".join(lines)


def main() -> int:
    """Lambda runtime 更新チェック CLI を実行し、構造化結果を出力する。"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="cloudformation.yml")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--github-output", default=os.getenv("GITHUB_OUTPUT"))
    args = parser.parse_args()

    template_path = Path(args.template)
    template = load_template_or_fail(template_path)
    lambda_resources = extract_lambda_resources(template)
    runtimes = cfn_lint_lambda_runtimes(args.region)

    updates: list[dict[str, str]] = []
    for resource in lambda_resources:
        latest = latest_runtime_for_family(resource["current_runtime"], runtimes)
        if latest and resource["current_runtime"] != latest:
            updates.append({**resource, "latest_runtime": latest})

    issue_payloads: list[dict[str, str]] = []
    for update in updates:
        title, body = build_issue(update, template_path)
        issue_payloads.append({"title": title, "body": body})

    has_update = bool(issue_payloads)
    result = {
        "has_update": has_update,
        "template": str(template_path),
        "updates": updates,
        "issues": issue_payloads,
    }
    print_json_result(result)

    if args.github_output:
        write_github_output(
            args.github_output,
            {
                "has_update": "true" if has_update else "false",
                "issues": json.dumps(issue_payloads, ensure_ascii=False),
            },
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
