#!/usr/bin/env python3
"""Resolve BMAD workflow customization for Paperclip projects.

Merges, in order:
1. <skill-root>/customize.toml
2. <project-root>/_bmad/custom/<skill-name>.toml
3. <project-root>/_bmad/custom/<skill-name>.user.toml

Merge rules match BMAD guidance: scalars override, dicts merge recursively, arrays append.
Prints the requested top-level key as JSON for agent consumption.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any


def merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = merge(merged[key], value) if key in merged else value
        return merged
    if isinstance(base, list) and isinstance(override, list):
        return [*base, *override]
    return override


def load_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill", required=True, help="Installed skill directory containing customize.toml")
    parser.add_argument("--key", required=True, help="Top-level TOML key to emit, for example workflow")
    args = parser.parse_args()

    project_root = Path.cwd()
    skill_root = Path(args.skill).expanduser().resolve()
    skill_name = skill_root.name

    sources = [
        skill_root / "customize.toml",
        project_root / "_bmad" / "custom" / f"{skill_name}.toml",
        project_root / "_bmad" / "custom" / f"{skill_name}.user.toml",
    ]

    data: dict[str, Any] = {}
    for source in sources:
        data = merge(data, load_toml(source))

    print(json.dumps(data.get(args.key, {}), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
