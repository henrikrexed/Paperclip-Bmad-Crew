"""Metadata/slice_info.config XML parsing."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any

from .errors import XmlParseReportError
from .normalizers import normalize_color, parse_bool, parse_float, parse_int

_LIST_SPLIT = re.compile(r"[;,|]")


@dataclass
class FilamentInfo:
    id: int | str | None
    type: str | None
    tray_info_idx: str | None
    color: str | None
    used_m: float | None
    used_g: float | None
    group_id: int | None
    nozzle_diameter: float | None
    volume_type: str | None
    used_for_object: bool | None
    used_for_support: bool | None
    nozzle: dict[str, Any] | None = None
    raw_attributes: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "tray_info_idx": self.tray_info_idx,
            "color": self.color,
            "used_m": self.used_m,
            "used_g": self.used_g,
            "group_id": self.group_id,
            "nozzle_diameter": self.nozzle_diameter,
            "volume_type": self.volume_type,
            "used_for_object": self.used_for_object,
            "used_for_support": self.used_for_support,
            "nozzle": self.nozzle,
            "raw_attributes": self.raw_attributes,
        }


@dataclass
class PlateSliceInfo:
    plate_index: int
    filaments: list[FilamentInfo]
    raw_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class SliceInfo:
    plates: dict[int, PlateSliceInfo]
    source_files: list[dict[str, Any]]
    raw_metadata: dict[str, Any]


def parse_slice_info(xml_bytes: bytes, *, include_placeholder_filaments: bool = False) -> SliceInfo:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise XmlParseReportError(str(exc)) from exc

    plates: dict[int, PlateSliceInfo] = {}
    plate_elements = [element for element in root.iter() if _local_name(element.tag) == "plate"]
    for ordinal, plate in enumerate(plate_elements, start=1):
        attrs = _combined_attrs(plate)
        plate_index = _parse_plate_index(attrs, ordinal)
        filaments = _parse_filaments_from_plate(plate, attrs, include_placeholder_filaments)
        plates[plate_index] = PlateSliceInfo(
            plate_index=plate_index,
            filaments=filaments,
            raw_attributes=_unknown_attrs(attrs, {"id", "index", "plate_index", "plate_id", "plate"}),
        )

    return SliceInfo(
        plates=dict(sorted(plates.items())),
        source_files=_parse_source_files(root),
        raw_metadata=_metadata_children(root),
    )


def _parse_plate_index(attrs: dict[str, Any], ordinal: int) -> int:
    for key in ("plate_index", "plate_id", "index", "id", "plate", "key"):
        value = attrs.get(key)
        if value is None:
            continue
        parsed = parse_int(value)
        if parsed is not None:
            return parsed
        match = re.search(r"(\d+)", str(value))
        if match:
            return int(match.group(1))
    return ordinal


def _parse_filaments_from_plate(
    plate: ET.Element, attrs: dict[str, Any], include_placeholder_filaments: bool
) -> list[FilamentInfo]:
    filaments: list[FilamentInfo] = []
    for element in plate.iter():
        if element is plate:
            continue
        if _local_name(element.tag) not in {"filament", "filament_info", "filament_config"}:
            continue
        filament = _filament_from_attrs(_combined_attrs(element), element)
        if not include_placeholder_filaments and str(filament.id) == "255":
            continue
        filaments.append(filament)

    if filaments:
        return filaments

    ids = _split_list(_first(attrs, "filament_ids", "filament_id", "ids", "id"))
    types = _split_list(_first(attrs, "filament_types", "filament_type", "types", "type", "materials"))
    colors = _split_list(_first(attrs, "filament_colors", "filament_colour", "colors", "colours", "color"))
    used_m = _split_list(_first(attrs, "filament_used_m", "used_m", "filament_meters"))
    used_g = _split_list(_first(attrs, "filament_used_g", "used_g", "filament_grams"))
    tray = _split_list(_first(attrs, "tray_info_idx", "tray_info_idxs", "tray_ids"))
    count = max(len(ids), len(types), len(colors), len(used_m), len(used_g), len(tray), 0)
    for index in range(count):
        item_attrs = {
            "id": _at(ids, index),
            "type": _at(types, index),
            "color": _at(colors, index),
            "used_m": _at(used_m, index),
            "used_g": _at(used_g, index),
            "tray_info_idx": _at(tray, index),
        }
        filament = _filament_from_attrs(item_attrs, None)
        if not include_placeholder_filaments and str(filament.id) == "255":
            continue
        filaments.append(filament)
    return filaments


def _filament_from_attrs(attrs: dict[str, Any], element: ET.Element | None) -> FilamentInfo:
    known = {
        "id",
        "filament_id",
        "type",
        "filament_type",
        "material",
        "tray_info_idx",
        "tray_id",
        "color",
        "colour",
        "filament_color",
        "used_m",
        "filament_used_m",
        "used_g",
        "filament_used_g",
        "group_id",
        "nozzle_diameter",
        "volume_type",
        "used_for_object",
        "used_for_support",
        "support",
        "object",
    }
    raw_id = _first(attrs, "id", "filament_id")
    parsed_id = parse_int(raw_id)
    filament_id: int | str | None = parsed_id if parsed_id is not None else raw_id
    nozzle = _parse_nozzle(element) if element is not None else None
    return FilamentInfo(
        id=filament_id,
        type=_clean(_first(attrs, "type", "filament_type", "material")),
        tray_info_idx=_clean(_first(attrs, "tray_info_idx", "tray_id")),
        color=normalize_color(_first(attrs, "color", "colour", "filament_color")),
        used_m=parse_float(_first(attrs, "used_m", "filament_used_m")),
        used_g=parse_float(_first(attrs, "used_g", "filament_used_g")),
        group_id=parse_int(attrs.get("group_id")),
        nozzle_diameter=parse_float(attrs.get("nozzle_diameter")),
        volume_type=_clean(attrs.get("volume_type")),
        used_for_object=parse_bool(_first(attrs, "used_for_object", "object")),
        used_for_support=parse_bool(_first(attrs, "used_for_support", "support")),
        nozzle=nozzle,
        raw_attributes=_unknown_attrs(attrs, known),
    )


def _parse_nozzle(element: ET.Element | None) -> dict[str, Any] | None:
    if element is None:
        return None
    for child in element:
        if _local_name(child.tag) == "nozzle":
            return dict(child.attrib)
    return None


def _parse_source_files(root: ET.Element) -> list[dict[str, Any]]:
    source_files: list[dict[str, Any]] = []
    for element in root.iter():
        if _local_name(element.tag) not in {"source_file", "source", "model", "object"}:
            continue
        attrs = _combined_attrs(element)
        if any(key in attrs for key in ("path", "name", "filename", "source_file", "uuid")):
            source_files.append(dict(attrs))
    return source_files


def _combined_attrs(element: ET.Element) -> dict[str, Any]:
    attrs: dict[str, Any] = {str(key): value for key, value in element.attrib.items()}
    attrs.update(_metadata_children(element))
    return attrs


def _metadata_children(element: ET.Element) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for child in list(element):
        if _local_name(child.tag) != "metadata":
            continue
        key = child.attrib.get("key") or child.attrib.get("name") or child.attrib.get("id")
        if not key:
            continue
        if "value" in child.attrib:
            value: Any = child.attrib["value"]
        elif child.text is not None:
            value = child.text.strip()
        else:
            value = None
        metadata[str(key)] = value
    return metadata


def _unknown_attrs(attrs: dict[str, Any], known: set[str]) -> dict[str, Any]:
    return {key: value for key, value in attrs.items() if key not in known and value is not None}


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def _first(attrs: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in attrs and attrs[key] not in {None, ""}:
            return attrs[key]
    return None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in _LIST_SPLIT.split(str(value)) if part.strip()]


def _at(values: list[str], index: int) -> str | None:
    return values[index] if index < len(values) else None
