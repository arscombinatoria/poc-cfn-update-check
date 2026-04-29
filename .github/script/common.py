#!/usr/bin/env python3
"""Common helpers for CloudFormation update check scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cfnlint.decode import cfn_yaml


def natural_version_key(value: str) -> list[Any]:
    parts = re.findall(r"\d+|[A-Za-z]+", str(value))
    key: list[Any] = []
    for p in parts:
        key.append((0, int(p)) if p.isdigit() else (1, p.lower()))
    return key


def write_github_output(path: str, outputs: dict[str, str]) -> None:
    with open(path, "a", encoding="utf-8") as fp:
        for key, value in outputs.items():
            fp.write(f"{key}<<EOF\n{value}\nEOF\n")


def print_json_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def load_template_or_fail(template_path: Path) -> dict[str, Any]:
    template = cfn_yaml.load(str(template_path))
    if not isinstance(template, dict):
        raise ValueError(f"Template must be a JSON object at top level: {template_path}")
    return template
