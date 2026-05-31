"""Small normalization helpers for slicer metadata."""

from __future__ import annotations

import re
from typing import Any

_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?")
_HEX = re.compile(r"^[0-9a-fA-F]+$")


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    match = _NUMBER.search(text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def parse_int(value: Any) -> int | None:
    number = parse_float(value)
    if number is None:
        return None
    return int(number)


def parse_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "object", "support"}:
        return True
    if text in {"0", "false", "no", "n", "off", "none"}:
        return False
    return None


def normalize_color(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if "," in text:
        parts = [parse_int(part) for part in text.split(",")]
        if len(parts) >= 3 and all(part is not None and 0 <= part <= 255 for part in parts[:3]):
            return "#" + "".join(f"{part:02X}" for part in parts[:3])

    if text.lower().startswith("0x"):
        text = text[2:]
    if text.startswith("#"):
        text = text[1:]
    text = text.strip()
    if len(text) == 3 and _HEX.match(text):
        text = "".join(ch * 2 for ch in text)
    if len(text) in {6, 8} and _HEX.match(text):
        return "#" + text.upper()
    return str(value).strip() or None


def ordered_unique(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    output: list[Any] = []
    for value in values:
        if value is None:
            continue
        marker = value
        if marker in seen:
            continue
        seen.add(marker)
        output.append(value)
    return output
