"""Duration normalization helpers."""

from __future__ import annotations

import re

_TOKEN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>days?|d|hours?|hrs?|hr|h|minutes?|mins?|min|m|seconds?|secs?|sec|s)",
    re.IGNORECASE,
)

_UNIT_SECONDS = {
    "d": 86400,
    "day": 86400,
    "days": 86400,
    "h": 3600,
    "hr": 3600,
    "hrs": 3600,
    "hour": 3600,
    "hours": 3600,
    "m": 60,
    "min": 60,
    "mins": 60,
    "minute": 60,
    "minutes": 60,
    "s": 1,
    "sec": 1,
    "secs": 1,
    "second": 1,
    "seconds": 1,
}


def parse_duration_seconds(value: str | None) -> int | None:
    """Parse common slicer duration strings into seconds.

    Supports forms such as ``48m 41s``, ``2h 36m 25s``, ``1d 4h 12m 9s``,
    ``40m``, ``95s``, ``01:02:03``, and ``12:34``.
    """

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if ":" in text and not any(ch.isalpha() for ch in text):
        parts = text.split(":")
        if all(part.strip().isdigit() for part in parts):
            numbers = [int(part) for part in parts]
            if len(numbers) == 3:
                hours, minutes, seconds = numbers
                return hours * 3600 + minutes * 60 + seconds
            if len(numbers) == 2:
                minutes, seconds = numbers
                return minutes * 60 + seconds

    total = 0.0
    matched = False
    for match in _TOKEN.finditer(text):
        matched = True
        unit = match.group("unit").lower()
        total += float(match.group("value")) * _UNIT_SECONDS[unit]
    if matched:
        return int(round(total))

    if text.isdigit():
        return int(text)
    return None
