#!/usr/bin/env python3
"""Check CloudFormation RDS EngineVersion against cfn-lint internal schema data."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
from dataclasses import dataclass

import cfnlint
from cfnlint.decode import decode


_NUMERIC_VERSION_PATTERN = re.compile(r"^\d+(?:\.\d+){1,3}$")


@dataclass
class CheckResult:
    logical_id: str
    engine: str
    current_version: str
    latest_version: str
    has_update: bool


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether RDS EngineVersion is outdated based on cfn-lint data"
    )
    parser.add_argument("--template", default="cloudformation.yml", help="Path to CloudFormation template")
    parser.add_argument("--logical-id", default="MySQLDB", help="Logical ID of AWS::RDS::DBInstance")
    parser.add_argument("--issue-body", help="Path to write issue markdown body")
    parser.add_argument("--json-output", help="Path to write JSON result")
    return parser.parse_args()


def _version_key(version: str) -> tuple[int, ...] | None:
    if not _NUMERIC_VERSION_PATTERN.fullmatch(version):
        return None
    return tuple(int(part) for part in version.split("."))


def _load_template_db_props(template_path: str, logical_id: str) -> tuple[str, str]:
    template, matches = decode(template_path)
    if matches:
        raise ValueError(f"Template parse warnings/errors: {matches}")

    resources = template.get("Resources", {})
    target = resources.get(logical_id)
    if not target:
        raise ValueError(f"Resource '{logical_id}' was not found in {template_path}")

    if target.get("Type") != "AWS::RDS::DBInstance":
        raise ValueError(f"Resource '{logical_id}' is not AWS::RDS::DBInstance")

    props = target.get("Properties", {})
    engine = str(props.get("Engine", "")).strip()
    version = str(props.get("EngineVersion", "")).strip()

    if not engine or not version:
        raise ValueError(
            f"Resource '{logical_id}' must define both Engine and EngineVersion properties"
        )

    return engine, version


def _load_supported_engine_versions(engine: str) -> list[str]:
    schema_path = (
        pathlib.Path(cfnlint.__file__).parent
        / "data/schemas/extensions/aws_rds_dbinstance/engine_version.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    all_of_rules = schema.get("allOf", [])
    for rule in all_of_rules:
        engine_const = (
            rule.get("if", {})
            .get("properties", {})
            .get("Engine", {})
            .get("const")
        )
        if engine_const != engine:
            continue

        versions = (
            rule.get("then", {})
            .get("properties", {})
            .get("EngineVersion", {})
            .get("enum", [])
        )
        return [str(v) for v in versions]

    raise ValueError(f"No engine versions found in cfn-lint schema for engine '{engine}'")


def _select_latest_numeric_version(versions: list[str]) -> str:
    candidates: list[tuple[tuple[int, ...], str]] = []
    for version in versions:
        key = _version_key(version)
        if key is not None:
            candidates.append((key, version))

    if not candidates:
        raise ValueError("No numeric versions found in cfn-lint schema data")

    candidates.sort(key=lambda item: item[0])
    return candidates[-1][1]


def _render_issue_body(result: CheckResult, template_path: str) -> str:
    return "\n".join(
        [
            "## RDS EngineVersion update detected",
            "",
            f"- Resource Logical ID: `{result.logical_id}`",
            f"- Engine: `{result.engine}`",
            f"- Current EngineVersion in `{template_path}`: `{result.current_version}`",
            f"- Latest EngineVersion from `cfn-lint` data: `{result.latest_version}`",
            "",
            "Please update the CloudFormation template if this upgrade is intended.",
        ]
    )


def main() -> int:
    args = _parse_args()

    engine, current_version = _load_template_db_props(args.template, args.logical_id)
    supported_versions = _load_supported_engine_versions(engine)
    latest_version = _select_latest_numeric_version(supported_versions)

    has_update = _version_key(current_version) is not None and _version_key(latest_version) is not None and _version_key(current_version) < _version_key(latest_version)

    result = CheckResult(
        logical_id=args.logical_id,
        engine=engine,
        current_version=current_version,
        latest_version=latest_version,
        has_update=has_update,
    )

    result_json = {
        "logical_id": result.logical_id,
        "engine": result.engine,
        "current_version": result.current_version,
        "latest_version": result.latest_version,
        "has_update": result.has_update,
    }

    print(json.dumps(result_json, ensure_ascii=False))

    if args.json_output:
        pathlib.Path(args.json_output).write_text(
            json.dumps(result_json, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.issue_body:
        pathlib.Path(args.issue_body).write_text(
            _render_issue_body(result, args.template) + "\n", encoding="utf-8"
        )

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with pathlib.Path(github_output).open("a", encoding="utf-8") as fp:
            fp.write(f"has_update={'true' if result.has_update else 'false'}\n")
            fp.write(f"engine={result.engine}\n")
            fp.write(f"current_version={result.current_version}\n")
            fp.write(f"latest_version={result.latest_version}\n")
            fp.write(f"logical_id={result.logical_id}\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
