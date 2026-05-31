"""G-code header parser for Bambu/Orca plate_N.gcode members."""

from __future__ import annotations

import re
from typing import BinaryIO, Any

from .duration import parse_duration_seconds
from .normalizers import parse_float, parse_int

_KV = re.compile(r"^;\s*([^:=]+?)\s*[:=]\s*(.*?)\s*$")
_MARKER = "HEADER_BLOCK_END"


def parse_gcode_header(
    raw: BinaryIO,
    *,
    path: str,
    max_header_lines: int = 3000,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "path": path,
        "header_lines_scanned": 0,
        "header_stop_reason": "eof",
        "unknown_fields": {},
    }

    for line_number, raw_line in enumerate(raw, start=1):
        if line_number > max_header_lines:
            result["header_stop_reason"] = "line_cap"
            break
        result["header_lines_scanned"] = line_number
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if _MARKER in line:
            result["header_stop_reason"] = "marker"
            break
        if not line.startswith(";"):
            continue
        match = _KV.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        _apply_field(result, key, value)

    return result


def _apply_field(result: dict[str, Any], key: str, value: str) -> None:
    normalized = _normalize_key(key)

    if normalized == "model printing time":
        result["model_printing_time"] = value
        result["model_printing_time_seconds"] = parse_duration_seconds(value)
        return
    if normalized in {"total estimated time", "estimated printing time normal mode"}:
        if "total_estimated_time" not in result:
            result["total_estimated_time"] = value
            result["total_estimated_time_seconds"] = parse_duration_seconds(value)
        if normalized == "estimated printing time normal mode":
            result["estimated_printing_time_normal_mode"] = value
            result["estimated_printing_time_normal_mode_seconds"] = parse_duration_seconds(value)
        return
    if normalized == "first layer printing time":
        result["first_layer_printing_time"] = value
        result["first_layer_printing_time_seconds"] = parse_duration_seconds(value)
        return
    if normalized == "total layer number":
        result["total_layer_number"] = parse_int(value)
        return
    if normalized in {"total filament length mm", "filament used mm"}:
        result["total_filament_length_mm"] = parse_float(value)
        return
    if normalized in {"total filament volume cm3", "total filament volume cm 3", "filament used cm3"}:
        result["total_filament_volume_cm3"] = parse_float(value)
        return
    if normalized in {"total filament weight g", "total filament used g", "filament used g"}:
        result["total_filament_weight_g"] = parse_float(value)
        return
    if normalized == "max z height":
        result["max_z_height"] = parse_float(value)
        return
    if normalized == "filament":
        result["filament"] = value
        return

    result["unknown_fields"][key] = value


def _normalize_key(key: str) -> str:
    text = key.strip().lower()
    text = text.replace("^", "")
    text = re.sub(r"[\[\]()/]", " ", text)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
