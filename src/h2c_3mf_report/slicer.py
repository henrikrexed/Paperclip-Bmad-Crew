"""Fakeable slicer command adapter for Bambu Studio / OrcaSlicer."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence, Any

from .profiles import ProfileConfig, profile_evidence

Runner = Callable[[Sequence[str], Path, int | None], Any]


@dataclass
class SlicerRequest:
    input_path: Path
    output_path: Path
    slicer: str
    slicer_path: Path | None
    profile_config: ProfileConfig
    work_dir: Path
    timeout_seconds: int | None = None


@dataclass
class SlicerResult:
    ok: bool
    output_path: Path | None
    command: list[str]
    exit_code: int | None
    stderr_tail: str | None
    error_code: str | None
    message: str | None = None
    profiles: dict[str, Any] | None = None

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "name": self.command[0] if self.command else None,
            "output_path": str(self.output_path) if self.output_path else None,
            "command": self.command,
            "exit_code": self.exit_code,
            "stderr_tail": self.stderr_tail,
            "error_code": self.error_code,
            "message": self.message,
            "profiles": self.profiles,
        }


def run_slicer(request: SlicerRequest, *, runner: Runner | None = None) -> SlicerResult:
    executable = _resolve_executable(request.slicer, request.slicer_path)
    if executable is None:
        return SlicerResult(
            ok=False,
            output_path=None,
            command=[],
            exit_code=None,
            stderr_tail=None,
            error_code="SLICER_NOT_FOUND",
            message="Slicer executable not found; provide --slicer-path or install an approved CLI binary.",
        )

    try:
        profiles = profile_evidence(request.profile_config)
    except Exception as exc:
        return SlicerResult(False, None, [executable], None, None, "CONFIG_ERROR", str(exc), None)

    command = build_command(
        request.slicer,
        executable,
        request.input_path,
        request.output_path,
        request.profile_config,
    )
    request.work_dir.mkdir(parents=True, exist_ok=True)
    runner = runner or _default_runner
    completed = runner(command, request.work_dir, request.timeout_seconds)
    exit_code = getattr(completed, "returncode", None)
    stderr = getattr(completed, "stderr", None)
    stderr_tail = _tail(stderr)
    if exit_code != 0:
        return SlicerResult(False, None, command, exit_code, stderr_tail, "SLICER_FAILED", "Slicer command failed.", profiles)
    if not request.output_path.exists():
        return SlicerResult(False, None, command, exit_code, stderr_tail, "SLICER_FAILED", "Slicer completed but output .gcode.3mf was not created.", profiles)
    return SlicerResult(True, request.output_path, command, exit_code, stderr_tail, None, None, profiles)


def build_command(slicer: str, executable: str, input_path: Path, output_path: Path, config: ProfileConfig) -> list[str]:
    settings = ";".join(str(path) for path in [config.machine_profile, config.process_profile] if path is not None)
    filaments = ";".join(str(path) for path in config.filament_profiles)
    command = [executable]
    if config.bed_type:
        command += ["--curr-bed-type", config.bed_type]
    if settings:
        command += ["--load-settings", settings]
    if filaments:
        command += ["--load-filaments", filaments]
    command += ["--slice", "0", "--debug", "2", "--export-3mf", str(output_path), str(input_path)]
    if slicer not in {"bambu-studio", "orcaslicer"}:
        # Keep command deterministic; validation lives in CLI/config.
        pass
    return command


def _resolve_executable(slicer: str, explicit_path: Path | None) -> str | None:
    if explicit_path is not None:
        return str(explicit_path) if explicit_path.exists() else None
    candidates = [slicer]
    if slicer == "bambu-studio":
        candidates += ["BambuStudio", "bambu-studio"]
    if slicer == "orcaslicer":
        candidates += ["OrcaSlicer", "orca-slicer", "orcaslicer"]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _default_runner(command: Sequence[str], cwd: Path, timeout: int | None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command),
        cwd=str(cwd),
        timeout=timeout,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _tail(value: Any, max_chars: int = 4000) -> str | None:
    if value is None:
        return None
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    return text[-max_chars:] if text else None
