"""Caller-supplied H2C slicer profile config handling."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigReportError


@dataclass
class ProfileConfig:
    machine_profile: Path | None = None
    process_profile: Path | None = None
    filament_profiles: list[Path] = field(default_factory=list)
    bed_type: str | None = None
    slicer: str | None = None
    slicer_path: Path | None = None

    def require_for_slicing(self) -> None:
        missing: list[str] = []
        if self.machine_profile is None:
            missing.append("machine_profile")
        if self.process_profile is None:
            missing.append("process_profile")
        if not self.filament_profiles:
            missing.append("filament_profiles")
        if missing:
            raise ConfigReportError("Slicing requires caller-supplied H2C profile config: " + ", ".join(missing))


def load_profile_config(path: str | Path) -> ProfileConfig:
    config_path = Path(path)
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigReportError(f"Could not read config file: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigReportError(f"Config file is not valid JSON: {config_path}") from exc

    def _path(key: str) -> Path | None:
        value = payload.get(key)
        if not value:
            return None
        p = Path(value)
        if not p.is_absolute():
            p = (config_path.parent / p).resolve()
        return p

    return ProfileConfig(
        machine_profile=_path("machine_profile"),
        process_profile=_path("process_profile"),
        filament_profiles=[(config_path.parent / item).resolve() if not Path(item).is_absolute() else Path(item) for item in payload.get("filament_profiles", [])],
        bed_type=payload.get("bed_type"),
        slicer=payload.get("slicer"),
        slicer_path=_path("slicer_path"),
    )


def profile_evidence(config: ProfileConfig) -> dict[str, Any]:
    config.require_for_slicing()
    assert config.machine_profile is not None
    assert config.process_profile is not None
    return {
        "machine": _evidence(config.machine_profile),
        "process": _evidence(config.process_profile),
        "filaments": [_evidence(path) for path in config.filament_profiles],
    }


def _evidence(path: Path) -> dict[str, str]:
    if not path.exists() or not path.is_file():
        raise ConfigReportError(f"Profile file does not exist: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return {"basename": path.name, "sha256": digest.hexdigest()}
