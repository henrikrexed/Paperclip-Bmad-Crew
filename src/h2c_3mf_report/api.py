"""Public orchestration API for H2C 3MF reports."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

from .archive import ArchiveClassification, classify_archive, open_member_text_lines, read_member_bytes
from .errors import ReportProblem, problem, warning
from .gcode import parse_gcode_header
from .normalizers import ordered_unique
from .profiles import ProfileConfig
from .slice_info import SliceInfo, parse_slice_info
from .slicer import SlicerRequest, run_slicer

SCHEMA_VERSION = "1.0.0"
SCHEMA_NAME = "h2c-3mf-report.v1"
TOOL_VERSION = "0.1.0"


@dataclass
class AnalyzeOptions:
    max_gcode_header_lines: int = 3000
    include_placeholder_filaments: bool = False
    strict: bool = False
    slice_raw: bool = False
    slicer: str = "bambu-studio"
    slicer_path: Path | None = None
    profile_config: ProfileConfig = field(default_factory=ProfileConfig)
    work_dir: Path | None = None
    slicer_timeout_seconds: int | None = None


def analyze_paths(paths: Iterable[str | Path], options: AnalyzeOptions | None = None) -> list[dict[str, Any]]:
    opts = options or AnalyzeOptions()
    return [analyze_path(path, opts) for path in paths]


def analyze_path(path: str | Path, options: AnalyzeOptions | None = None) -> dict[str, Any]:
    opts = options or AnalyzeOptions()
    input_path = Path(path)
    try:
        classification = classify_archive(input_path)
    except ReportProblem as exc:
        return _error_report(input_path, "invalid_archive", [exc.to_dict()])

    if not classification.contains_sliced_gcode:
        if opts.slice_raw:
            return _slice_then_analyze(classification, opts)
        return _classified_error_report(
            classification,
            [problem("UNSLICED_FILE", "This file does not contain sliced G-code. Re-run with --slice and caller-supplied H2C profiles to generate print-time and filament estimates.")],
        )

    return _extract_report(classification, opts)


def _slice_then_analyze(classification: ArchiveClassification, opts: AnalyzeOptions) -> dict[str, Any]:
    work_dir = opts.work_dir or (Path.cwd() / ".h2c-3mf-report-work")
    output_path = work_dir / f"{classification.path.stem}.gcode.3mf"
    request = SlicerRequest(
        input_path=classification.path,
        output_path=output_path,
        slicer=opts.slicer,
        slicer_path=opts.slicer_path,
        profile_config=opts.profile_config,
        work_dir=work_dir,
        timeout_seconds=opts.slicer_timeout_seconds,
    )
    result = run_slicer(request)
    if not result.ok or result.output_path is None:
        code = result.error_code or "SLICER_FAILED"
        return _classified_error_report(classification, [problem(code, result.message or "Slicer failed.", 500 if code == "SLICER_FAILED" else 400)], slicer=result.to_report_dict())
    child_opts = replace(opts, slice_raw=False)
    report = analyze_path(result.output_path, child_opts)
    report["sliced_by_tool"] = True
    report["slicer"] = result.to_report_dict()
    report["source_input"] = report.get("input")
    report["input"] = _input_dict(classification)
    return report


def _extract_report(classification: ArchiveClassification, opts: AnalyzeOptions) -> dict[str, Any]:
    warnings: list[dict[str, str]] = []
    errors: list[dict[str, Any]] = []
    slice_info: SliceInfo | None = None
    gcode_by_plate: dict[int, dict[str, Any]] = {}

    if classification.contains_slice_info and classification.slice_info_member:
        try:
            xml_bytes = read_member_bytes(classification.path, classification.slice_info_member)
            slice_info = parse_slice_info(xml_bytes, include_placeholder_filaments=opts.include_placeholder_filaments)
        except ReportProblem as exc:
            warnings.append(warning(exc.code, exc.message))
    else:
        warnings.append(warning("SLICE_INFO_MISSING", "Metadata/slice_info.config is absent; per-filament material/color usage may be incomplete."))

    if classification.contains_sliced_gcode:
        for plate_index, member in classification.plate_gcode_members.items():
            zf, raw = open_member_text_lines(classification.path, member)
            try:
                gcode_by_plate[plate_index] = parse_gcode_header(
                    raw,
                    path=member,
                    max_header_lines=opts.max_gcode_header_lines,
                )
            finally:
                raw.close()
                zf.close()
    else:
        warnings.append(warning("GCODE_MISSING", "No Metadata/plate_N.gcode member found; print time is unknown."))

    plates = _merge_plates(slice_info, gcode_by_plate, warnings)
    if not plates:
        warnings.append(warning("NO_PLATES_FOUND", "No plate metadata could be extracted."))

    totals = _totals(plates)
    if totals["print_time_seconds"] is None:
        warnings.append(warning("GCODE_TIME_MISSING", "Estimated print time was not found in G-code headers."))

    _add_mismatch_warning(totals, warnings)

    return {
        "schema_version": SCHEMA_VERSION,
        "schema_name": SCHEMA_NAME,
        "tool_version": TOOL_VERSION,
        "status": "error" if errors else "ok",
        "file": classification.filename,
        "input": _input_dict(classification),
        "source_kind": classification.source_kind,
        "contains_sliced_gcode": classification.contains_sliced_gcode,
        "contains_slice_info": classification.contains_slice_info,
        "sliced_by_tool": False,
        "slicer": None,
        "source_files": slice_info.source_files if slice_info else [],
        "totals": totals,
        "plates": plates,
        "warnings": warnings,
        "errors": errors,
    }


def _merge_plates(slice_info: SliceInfo | None, gcode_by_plate: dict[int, dict[str, Any]], warnings: list[dict[str, str]]) -> list[dict[str, Any]]:
    slice_plates = slice_info.plates if slice_info else {}
    indices = sorted(set(slice_plates) | set(gcode_by_plate))
    plates: list[dict[str, Any]] = []
    for index in indices:
        plate_warnings: list[dict[str, str]] = []
        slice_plate = slice_plates.get(index)
        filament_dicts = [filament.to_dict() for filament in slice_plate.filaments] if slice_plate else []
        if slice_info is not None and slice_plate is None:
            plate_warnings.append(warning("PARTIAL_METADATA", f"Plate {index} has G-code but no slice_info plate entry."))
        if slice_info is None:
            plate_warnings.append(warning("SLICE_INFO_MISSING", "Per-filament metadata unavailable for this plate."))
        gcode = gcode_by_plate.get(index)
        if gcode is None:
            plate_warnings.append(warning("GCODE_MISSING", f"Plate {index} has no Metadata/plate_{index}.gcode member."))
        if slice_info is not None and slice_plate is not None and not filament_dicts:
            plate_warnings.append(warning("PARTIAL_METADATA", f"Plate {index} has no filament entries in slice_info.config."))

        total_m = _sum_or_none(item.get("used_m") for item in filament_dicts)
        total_g = _sum_or_none(item.get("used_g") for item in filament_dicts)
        plates.append(
            {
                "plate_index": index,
                "plate_key": f"plate_{index}",
                "colors": ordered_unique([item.get("color") for item in filament_dicts]),
                "filament_types": ordered_unique([item.get("type") for item in filament_dicts]),
                "total_used_m_from_slice_info": total_m,
                "total_used_g_from_slice_info": total_g,
                "filaments": filament_dicts,
                "gcode": gcode,
                "warnings": plate_warnings,
            }
        )
    for plate in plates:
        warnings.extend(plate["warnings"])
    return plates


def _totals(plates: list[dict[str, Any]]) -> dict[str, Any]:
    gcode_weights = [plate.get("gcode", {}).get("total_filament_weight_g") for plate in plates if plate.get("gcode")]
    times = []
    for plate in plates:
        gcode = plate.get("gcode") or {}
        seconds = gcode.get("total_estimated_time_seconds") or gcode.get("model_printing_time_seconds") or gcode.get("estimated_printing_time_normal_mode_seconds")
        times.append(seconds)
    return {
        "plate_count": len(plates),
        "filament_used_g_from_slice_info": _sum_or_none(plate.get("total_used_g_from_slice_info") for plate in plates),
        "filament_used_m_from_slice_info": _sum_or_none(plate.get("total_used_m_from_slice_info") for plate in plates),
        "filament_weight_g_from_gcode": _sum_or_none(gcode_weights),
        "print_time_seconds": _sum_or_none(times),
    }


def _add_mismatch_warning(totals: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    slice_g = totals.get("filament_used_g_from_slice_info")
    gcode_g = totals.get("filament_weight_g_from_gcode")
    if slice_g is None or gcode_g is None:
        return
    tolerance = max(0.05, abs(gcode_g) * 0.02)
    if abs(slice_g - gcode_g) > tolerance:
        warnings.append(warning("FILAMENT_TOTAL_MISMATCH", "slice_info filament grams and G-code total filament weight differ beyond tolerance; both raw totals are preserved."))


def _sum_or_none(values: Iterable[Any]) -> float | int | None:
    usable = [value for value in values if isinstance(value, (int, float))]
    if not usable:
        return None
    total = sum(float(value) for value in usable)
    return round(total, 6)


def _input_dict(classification: ArchiveClassification) -> dict[str, Any]:
    return {
        "path": str(classification.path),
        "filename": classification.filename,
        "sha256": classification.sha256,
        "size_bytes": classification.size_bytes,
    }


def _classified_error_report(classification: ArchiveClassification, errors: list[dict[str, Any]], *, slicer: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "schema_name": SCHEMA_NAME,
        "tool_version": TOOL_VERSION,
        "status": "error",
        "file": classification.filename,
        "input": _input_dict(classification),
        "source_kind": classification.source_kind,
        "contains_sliced_gcode": classification.contains_sliced_gcode,
        "contains_slice_info": classification.contains_slice_info,
        "sliced_by_tool": False,
        "slicer": slicer,
        "source_files": [],
        "totals": {"plate_count": 0, "filament_used_g_from_slice_info": None, "filament_used_m_from_slice_info": None, "filament_weight_g_from_gcode": None, "print_time_seconds": None},
        "plates": [],
        "warnings": [],
        "errors": errors,
    }


def _error_report(path: Path, source_kind: str, errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "schema_name": SCHEMA_NAME,
        "tool_version": TOOL_VERSION,
        "status": "error",
        "file": path.name,
        "input": {"path": str(path), "filename": path.name, "sha256": None, "size_bytes": None},
        "source_kind": source_kind,
        "contains_sliced_gcode": False,
        "contains_slice_info": False,
        "sliced_by_tool": False,
        "slicer": None,
        "source_files": [],
        "totals": {"plate_count": 0, "filament_used_g_from_slice_info": None, "filament_used_m_from_slice_info": None, "filament_weight_g_from_gcode": None, "print_time_seconds": None},
        "plates": [],
        "warnings": [],
        "errors": errors,
    }
