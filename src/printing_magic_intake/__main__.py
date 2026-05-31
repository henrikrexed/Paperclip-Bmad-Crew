"""CLI for ZIP intake manifest and listing-intelligence workflow generation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .intake import build_asset_manifest, run_listing_intelligence_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Build asset manifest v0 or final listing-intelligence record")
    parser.add_argument("--working-root", required=True, help="isolated output root for working copies and manifest")
    parser.add_argument("--intake-id", default=None, help="optional intake correlation id")
    parser.add_argument("--paperclip-issue-id", default=None)
    parser.add_argument("--paperclip-issue-identifier", default=None)
    parser.add_argument("--workflow", action="store_true", help="run full deterministic listing-intelligence workflow")
    parser.add_argument("--db-path", type=Path, default=None, help="SQLite path for final workflow persistence")
    parser.add_argument("zip_paths", nargs="+", help="source ZIP paths; opened read-only")
    args = parser.parse_args()

    if args.workflow:
        result = run_listing_intelligence_workflow(
            [Path(p) for p in args.zip_paths],
            Path(args.working_root),
            db_path=args.db_path,
            intake_id=args.intake_id,
            paperclip_issue_id=args.paperclip_issue_id,
            paperclip_issue_identifier=args.paperclip_issue_identifier,
        )
    else:
        result = build_asset_manifest(
            [Path(p) for p in args.zip_paths],
            Path(args.working_root),
            intake_id=args.intake_id,
            paperclip_issue_id=args.paperclip_issue_id,
            paperclip_issue_identifier=args.paperclip_issue_identifier,
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
