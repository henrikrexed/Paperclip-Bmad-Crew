"""Safe ZIP/3MF archive inspection and classification."""

from __future__ import annotations

import hashlib
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .errors import InvalidArchiveError, UnsafeArchiveEntryError

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
_PLATE_GCODE = re.compile(r"^Metadata/plate_(\d+)\.gcode$")


@dataclass(frozen=True)
class ArchiveMember:
    name: str
    size_bytes: int
    compressed_size_bytes: int


@dataclass(frozen=True)
class ArchiveClassification:
    path: Path
    filename: str
    sha256: str
    size_bytes: int
    source_kind: str
    contains_sliced_gcode: bool
    contains_slice_info: bool
    plate_gcode_members: dict[int, str]
    slice_info_member: str | None
    members: dict[str, ArchiveMember]


def safe_member_path(member_name: str) -> PurePosixPath:
    normalized = member_name.replace("\\", "/")
    if _CONTROL_CHARS.search(normalized):
        raise UnsafeArchiveEntryError("Archive member contains control characters.")
    if normalized.startswith("/") or normalized.startswith("//"):
        raise UnsafeArchiveEntryError("Archive member uses an absolute path.")
    if _WINDOWS_DRIVE.match(normalized):
        raise UnsafeArchiveEntryError("Archive member uses a Windows drive path.")
    path = PurePosixPath(normalized)
    if not path.parts:
        raise UnsafeArchiveEntryError("Archive member path is empty.")
    for part in path.parts:
        if part in {"", ".", ".."}:
            raise UnsafeArchiveEntryError("Archive member uses an unsafe relative path.")
    return path


def classify_archive(path: str | Path) -> ArchiveClassification:
    archive_path = Path(path)
    if not archive_path.exists():
        raise InvalidArchiveError(f"Input file does not exist: {archive_path}")
    if not archive_path.is_file():
        raise InvalidArchiveError(f"Input path is not a file: {archive_path}")

    try:
        size_bytes = archive_path.stat().st_size
        sha256 = _sha256_file(archive_path)
        with zipfile.ZipFile(archive_path, "r") as zf:
            infos = zf.infolist()
    except zipfile.BadZipFile as exc:
        raise InvalidArchiveError("Input is not a readable ZIP/3MF archive.") from exc
    except OSError as exc:
        raise InvalidArchiveError(f"Input archive could not be read: {archive_path}") from exc

    if not infos:
        raise InvalidArchiveError("Input ZIP/3MF archive is empty.")

    members: dict[str, ArchiveMember] = {}
    plate_gcode_members: dict[int, str] = {}
    slice_info_member: str | None = None

    for info in infos:
        if info.is_dir():
            continue
        safe_path = safe_member_path(info.filename).as_posix()
        members[safe_path] = ArchiveMember(safe_path, info.file_size, info.compress_size)
        if safe_path == "Metadata/slice_info.config":
            slice_info_member = safe_path
        match = _PLATE_GCODE.match(safe_path)
        if match:
            plate_gcode_members[int(match.group(1))] = safe_path

    contains_sliced_gcode = bool(plate_gcode_members)
    contains_slice_info = slice_info_member is not None
    source_kind = "sliced_gcode_3mf" if contains_sliced_gcode else "raw_project_3mf"

    return ArchiveClassification(
        path=archive_path,
        filename=archive_path.name,
        sha256=sha256,
        size_bytes=size_bytes,
        source_kind=source_kind,
        contains_sliced_gcode=contains_sliced_gcode,
        contains_slice_info=contains_slice_info,
        plate_gcode_members=dict(sorted(plate_gcode_members.items())),
        slice_info_member=slice_info_member,
        members=members,
    )


def read_member_bytes(path: str | Path, member_name: str, *, max_bytes: int = 10_000_000) -> bytes:
    archive_path = Path(path)
    with zipfile.ZipFile(archive_path, "r") as zf:
        info = zf.getinfo(member_name)
        if info.file_size > max_bytes:
            raise InvalidArchiveError(f"Archive member too large to parse safely: {member_name}")
        return zf.read(info)


def open_member_text_lines(path: str | Path, member_name: str):
    archive_path = Path(path)
    zf = zipfile.ZipFile(archive_path, "r")
    try:
        raw = zf.open(member_name, "r")
    except Exception:
        zf.close()
        raise
    return zf, raw


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
