"""Command-line interface for h2c-3mf-report."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Sequence

from . import __version__
from .api import AnalyzeOptions, analyze_paths
from .profiles import ProfileConfig, load_profile_config


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # pragma: no cover - argparse integration
        self.print_usage(sys.stderr)
        self.exit(1, f"{self.prog}: error: {message}\n")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0

    if args.output and args.output_dir:
        parser.error("--output and --output-dir are mutually exclusive")
    if args.jsonl and args.output:
        parser.error("--jsonl cannot be combined with --output")
    if args.jsonl and args.output_dir:
        parser.error("--jsonl cannot be combined with --output-dir")

    profile_config = _profile_config_from_args(args)
    options = AnalyzeOptions(
        max_gcode_header_lines=args.max_gcode_header_lines,
        include_placeholder_filaments=args.include_placeholder_filaments,
        strict=args.strict,
        slice_raw=args.slice,
        slicer=args.slicer or profile_config.slicer or "bambu-studio",
        slicer_path=args.slicer_path or profile_config.slicer_path,
        profile_config=profile_config,
        work_dir=args.work_dir,
        slicer_timeout_seconds=args.slicer_timeout_seconds,
    )

    reports = analyze_paths(args.inputs, options)
    _emit_reports(reports, args)
    return _exit_code(reports, strict=args.strict)


def _parser() -> Parser:
    parser = Parser(prog="h2c-3mf-report", description="Extract Bambu/Orca/H2C 3MF metadata as JSON.")
    parser.add_argument("inputs", nargs="+", help="one or more .3mf / .gcode.3mf paths")
    parser.add_argument("--output", type=Path, help="write JSON report to this path")
    parser.add_argument("--output-dir", type=Path, help="write one JSON report per input")
    parser.add_argument("--jsonl", action="store_true", help="emit one JSON object per line")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when warnings are present")
    parser.add_argument("--max-gcode-header-lines", type=int, default=3000)
    parser.add_argument("--include-placeholder-filaments", action="store_true")
    parser.add_argument("--slice", action="store_true", help="slice raw project 3MF before extracting")
    parser.add_argument("--slicer", choices=["bambu-studio", "orcaslicer"], default=None)
    parser.add_argument("--slicer-path", type=Path)
    parser.add_argument("--machine-profile", type=Path)
    parser.add_argument("--process-profile", type=Path)
    parser.add_argument("--filament-profile", action="append", type=Path, default=[])
    parser.add_argument("--bed-type")
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--keep-temp", action="store_true", help="accepted for CLI contract; generated files are kept when --work-dir is explicit")
    parser.add_argument("--config", type=Path, help="caller-supplied JSON config for slicer/profile paths")
    parser.add_argument("--quiet", action="store_true", help="suppress non-JSON logs")
    parser.add_argument("--slicer-timeout-seconds", type=int)
    parser.add_argument("--version", action="store_true")
    return parser


def _profile_config_from_args(args: argparse.Namespace) -> ProfileConfig:
    config = load_profile_config(args.config) if args.config else ProfileConfig()
    if args.machine_profile:
        config.machine_profile = args.machine_profile
    if args.process_profile:
        config.process_profile = args.process_profile
    if args.filament_profile:
        config.filament_profiles = list(args.filament_profile)
    if args.bed_type:
        config.bed_type = args.bed_type
    if args.slicer:
        config.slicer = args.slicer
    if args.slicer_path:
        config.slicer_path = args.slicer_path
    return config


def _emit_reports(reports: list[dict[str, Any]], args: argparse.Namespace) -> None:
    indent = 2 if args.pretty else None
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for report in reports:
            filename = _safe_report_filename(report.get("file") or "report")
            (args.output_dir / filename).write_text(json.dumps(report, indent=indent, sort_keys=args.pretty) + "\n", encoding="utf-8")
        return
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        payload: Any = reports[0] if len(reports) == 1 else reports
        args.output.write_text(json.dumps(payload, indent=indent, sort_keys=args.pretty) + "\n", encoding="utf-8")
        return
    if args.jsonl:
        for report in reports:
            print(json.dumps(report, separators=(",", ":"), sort_keys=False))
        return
    payload = reports[0] if len(reports) == 1 else reports
    print(json.dumps(payload, indent=indent, sort_keys=args.pretty))


def _exit_code(reports: list[dict[str, Any]], *, strict: bool) -> int:
    error_codes = [error.get("code") for report in reports for error in report.get("errors", [])]
    if any(code in {"SLICER_NOT_FOUND", "SLICER_FAILED"} for code in error_codes):
        return 3
    if error_codes:
        return 2
    if strict and any(report.get("warnings") for report in reports):
        return 2
    return 0


def _safe_report_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "report"
    return f"{safe}.json"
