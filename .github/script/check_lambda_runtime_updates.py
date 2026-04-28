#!/usr/bin/env python3
"""Check CloudFormation Lambda Runtime values against cfn-lint provider schema data."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from cfnlint.decode import cfn_yaml
from cfnlint.schema.manager import ProviderSchemaManager


def natural_version_key(value: str) -> list[Any]:
    parts = re.findall(r"\d+|[A-Za-z]+", str(value))
    key: list[Any] = []
    for p in parts:
        key.append((0, int(p)) if p.isdigit() else (1, p.lower()))
    return key


def runtime_family_and_version(runtime: str) -> tuple[str, str]:
    if runtime.startswith("provided.al"):
        return "provided.al", runtime.removeprefix("provided.al")

    patterns = ["python", "nodejs", "java", "dotnetcore", "dotnet", "ruby"]
    for prefix in patterns:
        if runtime.startswith(prefix):
            return prefix, runtime.removeprefix(prefix)

    return runtime, ""


def cfn_lint_lambda_runtimes(region: str = "us-east-1") -> list[str]:
    manager = ProviderSchemaManager()
    schema = manager.get_resource_schema(region, "AWS::Lambda::Function")
    runtimes = schema.schema.get("properties", {}).get("Runtime", {}).get("enum", [])
    return sorted((str(r) for r in runtimes), key=natural_version_key)


def latest_runtime_for_family(current_runtime: str, runtimes: list[str]) -> str | None:
    family, _ = runtime_family_and_version(current_runtime)

    family_runtimes = [r for r in runtimes if runtime_family_and_version(r)[0] == family]
    if not family_runtimes:
        return None

    return sorted(
        family_runtimes,
        key=lambda r: natural_version_key(runtime_family_and_version(r)[1]),
    )[-1]


def extract_lambda_resources(template: dict[str, Any]) -> list[dict[str, str]]:
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


def write_github_output(path: str, outputs: dict[str, str]) -> None:
    with open(path, "a", encoding="utf-8") as fp:
        for key, value in outputs.items():
            fp.write(f"{key}<<EOF\n{value}\nEOF\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="cloudformation.yml")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--github-output", default=os.getenv("GITHUB_OUTPUT"))
    args = parser.parse_args()

    template_path = Path(args.template)
    template = cfn_yaml.load(str(template_path))
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
    print(json.dumps(result, ensure_ascii=False, indent=2))

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
