"""Safe ZIP intake and asset manifest v0 generation.

Goal 1 constraints:
- preserve source ZIP bytes; never mutate originals
- extract only to isolated working copies
- reject Zip Slip/path traversal and unsafe overwrite paths
- do not invent product facts or H2C print estimates
- emit structured audit events without file contents or raw absolute paths
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import tempfile
import uuid
import zipfile
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator, Iterable

MANIFEST_SCHEMA_VERSION = "0.1"
EVENT_VERSION = 1
SERVICE_NAME = "product-intake"
DEFAULT_ASSET_GROUP = "product-package-default"
H2C_MISSING_REASON = "not_collected_in_intake_v0"
WORKFLOW_SCHEMA_VERSION = "listing-intelligence-workflow.v1"
FINAL_RECORD_SCHEMA_VERSION = "product-intelligence-final.v1"
TECHNICAL_ESTIMATE_SCHEMA_VERSION = "technical-estimate.v1"
POLICY_RESULT_SCHEMA_VERSION = "marketplace-policy-result.v1"
MAX_EXTRACTED_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_EXTRACTED_BYTES = 512 * 1024 * 1024

MEDIA_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
VIDEO_EXTENSIONS = {".webm", ".mp4", ".mov", ".avi", ".mkv"}
MODEL_EXTENSIONS = {".stl", ".3mf", ".obj", ".step", ".stp", ".amf"}
DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".md", ".rtf"}
SUPPORTED_EXTENSIONS = MEDIA_EXTENSIONS | VIDEO_EXTENSIONS | MODEL_EXTENSIONS | DOCUMENT_EXTENSIONS

CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")
SAFE_SEGMENT_CHARS = re.compile(r"[^A-Za-z0-9._ -]+")
RESERVED_WINDOWS_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class IntakeError(Exception):
    """Base error for intake failures."""


class UnsafeZipEntryError(IntakeError):
    """Raised when ZIP member path is unsafe to extract."""


class UnsupportedZipEntryError(IntakeError):
    """Raised when ZIP member type is outside the extraction allow-list."""


class ArchiveSizeLimitError(IntakeError):
    """Raised when ZIP expansion would exceed configured safety limits."""


class PersistenceError(IntakeError):
    """Raised when final workflow persistence fails."""


@dataclass(frozen=True)
class SourcePackage:
    path: Path
    package_role: str
    package_id: str
    source_zip_id: str
    checksum_sha256: str
    size_bytes: int


@dataclass(frozen=True)
class WorkflowEvidencePaths:
    visual_analysis: Path | None = None
    marketplace_copy: Path | None = None
    technical_estimate: Path | None = None


DEFAULT_PROJECT_ROOT = Path(
    "/home/cweber/.paperclip/instances/default/projects/6e564770-9fdc-4fb4-b550-37e41ae47fa1/"
    "c9e9d509-8117-4fd8-9db8-29283e39764f"
)
DEFAULT_WORKFLOW_EVIDENCE = WorkflowEvidencePaths(
    visual_analysis=DEFAULT_PROJECT_ROOT / "work-products/WEB-29/visual-analysis-output.json",
    marketplace_copy=DEFAULT_PROJECT_ROOT / "_default/work-products/WEB-30/marketplace-copy-output.json",
    technical_estimate=DEFAULT_PROJECT_ROOT / "work-products/WEB-31/metadata-extraction-summary.json",
)


def build_asset_manifest(
    source_zip_paths: Iterable[str | Path],
    working_root: str | Path,
    *,
    intake_id: str | None = None,
    paperclip_issue_id: str | None = None,
    paperclip_issue_identifier: str | None = None,
    actor_type: str = "agent",
    actor_id: str | None = None,
    environment: str | None = None,
    extract: bool = True,
) -> dict[str, Any]:
    """Build manifest for source ZIPs and optionally extract safe working copies.

    Args:
        source_zip_paths: original source ZIP paths. These files are opened read-only and never mutated.
        working_root: isolated output root for generated manifest/audit files and extracted copies.
        intake_id: optional correlation id. Generated when absent.
        paperclip_issue_id: optional issue UUID.
        paperclip_issue_identifier: optional human identifier, e.g. WEB-18.
        actor_type: agent|user|system.
        actor_id: raw actor id. Only hashed value is emitted in audit events.
        environment: local/test/staging/prod when known.
        extract: when true, write safe working copies under working_root/extracted.

    Returns:
        JSON-serializable manifest dict. Also writes manifest/audit JSONL under working_root.
    """

    source_paths = [Path(p) for p in source_zip_paths]
    if not source_paths:
        raise IntakeError("at least one source ZIP path is required")

    intake_id = _safe_intake_id(intake_id or _new_id("intake"))
    working_root_path = Path(working_root).resolve()
    working_root_path.mkdir(parents=True, exist_ok=True)
    extraction_root = working_root_path / "extracted" / intake_id
    _ensure_within(working_root_path, extraction_root.resolve())
    if extract:
        extraction_root.mkdir(parents=True, exist_ok=False)

    event_context = {
        "intake_id": intake_id,
        "paperclip_issue_id": paperclip_issue_id,
        "paperclip_issue_identifier": paperclip_issue_identifier,
        "actor_type": actor_type,
        "actor_id_hash": _hash_text(actor_id) if actor_id else None,
        "environment": environment,
    }

    events: list[dict[str, Any]] = []
    packages: list[dict[str, Any]] = []
    assets: list[dict[str, Any]] = []

    source_packages = [_source_package(path) for path in source_paths]
    package_set_id = _package_set_id(source_packages)

    try:
        for source in source_packages:
            packages.append(_package_manifest(source, package_set_id, intake_id))
            events.append(
                _event(
                    "product_intake.package_received",
                    status="received",
                    severity="info",
                    package_set_id=package_set_id,
                    package_id=source.package_id,
                    source_zip_id=source.source_zip_id,
                    package_role=source.package_role,
                    source_zip_name_hash=_hash_text(source.path.name),
                    source_zip_size_bytes=source.size_bytes,
                    source_zip_mime_type="application/zip",
                    source_path_ref=_path_ref(source.path),
                    original_preserved=True,
                    received_at=_now(),
                    **event_context,
                )
            )

            zip_entries = _validate_zip(source.path)
            files = [info for info in zip_entries if not info.is_dir()]
            dirs = [info for info in zip_entries if info.is_dir()]
            unsupported_files = [info for info in files if _extension(info.filename) not in SUPPORTED_EXTENSIONS]
            if unsupported_files:
                raise UnsupportedZipEntryError(
                    f"unsupported ZIP member extension: {_safe_error_message(unsupported_files[0].filename)}"
                )
            events.append(
                _event(
                    "product_intake.zip_validated",
                    status="valid",
                    severity="info",
                    package_set_id=package_set_id,
                    package_id=source.package_id,
                    source_zip_id=source.source_zip_id,
                    zip_entry_count=len(zip_entries),
                    file_entry_count=len(files),
                    directory_entry_count=len(dirs),
                    unsafe_entry_count=0,
                    unsupported_entry_count=0,
                    **event_context,
                )
            )

            working_copy_id = _new_id("wc")
            extracted_count = 0
            normalized_targets: dict[str, int] = {}
            package_extract_root = extraction_root / source.package_id if extract else None
            if package_extract_root:
                package_extract_root.mkdir(parents=True, exist_ok=False)

            with zipfile.ZipFile(source.path, "r") as zf:
                for info in files:
                    safe_rel = _safe_member_path(info.filename)
                    normalized_rel = _dedupe_relative_path(_sanitize_relative_path(safe_rel), normalized_targets)
                    ext = _extension(info.filename)
                    asset_type = _asset_type(ext)
                    working_copy_rel: str | None = None
                    working_copy_id_for_row: str | None = None
                    asset_sha, content = _read_zip_member_for_extract(zf, info, extract=extract)
                    asset_id = f"asset_{asset_sha[:16]}"

                    if extract and package_extract_root is not None:
                        target = (package_extract_root / normalized_rel).resolve()
                        _ensure_within(package_extract_root.resolve(), target)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if target.exists():
                            raise UnsafeZipEntryError(f"refusing to overwrite extracted path: {normalized_rel}")
                        target.write_bytes(content)
                        extracted_count += 1
                        working_copy_rel = _relative_posix(target, working_root_path.resolve())
                        working_copy_id_for_row = working_copy_id

                    row = {
                        "manifest_row_id": _manifest_row_id(
                            intake_id,
                            source.package_id,
                            str(safe_rel),
                            asset_sha,
                        ),
                        "intake_id": intake_id,
                        "package_set_id": package_set_id,
                        "package_id": source.package_id,
                        "source_zip_id": source.source_zip_id,
                        "source_zip_path": _path_ref(source.path),
                        "source_zip_name_hash": _hash_text(source.path.name),
                        "original_filename": PurePosixPath(info.filename).name,
                        "original_relative_path": str(safe_rel),
                        "normalized_relative_path": normalized_rel,
                        "asset_id": asset_id,
                        "asset_type": asset_type,
                        "asset_group": DEFAULT_ASSET_GROUP,
                        "extension": ext,
                        "mime_type": _mime_type(ext),
                        "checksum": f"sha256:{asset_sha}",
                        "size_bytes": info.file_size,
                        "compressed_size_bytes": info.compress_size,
                        "working_copy_path": working_copy_rel,
                        "working_copy_id": working_copy_id_for_row,
                        "original_preserved": True,
                        "audit_correlation_id": intake_id,
                        "unsupported": False,
                        "h2c_estimate_state": "unknown",
                        "h2c_estimate_source": None,
                    }
                    assets.append(row)

            events.append(
                _event(
                    "product_intake.assets_extracted",
                    status="succeeded",
                    severity="info",
                    package_set_id=package_set_id,
                    package_id=source.package_id,
                    source_zip_id=source.source_zip_id,
                    working_copy_id=working_copy_id if extract else None,
                    asset_count=len(files),
                    extracted_asset_count=extracted_count,
                    output_root_ref=_path_ref(extraction_root),
                    original_preserved=True,
                    **event_context,
                )
            )

        assets.sort(key=lambda a: (a["package_id"], a["normalized_relative_path"], a["checksum"]))
        packages.sort(key=lambda p: (p["package_role"], p["original_filename"]))
        groups = _asset_groups(assets)

        manifest: dict[str, Any] = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "intake_id": intake_id,
            "package_set_id": package_set_id,
            "manifest_id": None,
            "manifest_checksum_sha256": None,
            "generated_at": _now(),
            "paperclip_issue_id": paperclip_issue_id,
            "paperclip_issue_identifier": paperclip_issue_identifier,
            "originals_preserved": True,
            "source_mutation_policy": "never_mutate_original_uploads",
            "h2c_estimate_state": "unknown",
            "h2c_estimate_source": None,
            "h2c_missing_reason_code": H2C_MISSING_REASON,
            "packages": packages,
            "assets": assets,
            "asset_groups": groups,
            "audit_events": events,
            "unknowns": {
                "h2c_print_estimate": None,
                "product_listing_copy": None,
                "marketplace_approval": None,
            },
        }
        checksum = _canonical_sha256(manifest)
        manifest["manifest_checksum_sha256"] = f"sha256:{checksum}"
        manifest["manifest_id"] = f"manifest_{checksum[:16]}"

        events.append(
            _event(
                "product_intake.manifest_generated",
                status="succeeded",
                severity="info",
                package_set_id=package_set_id,
                manifest_id=manifest["manifest_id"],
                manifest_checksum_sha256=manifest["manifest_checksum_sha256"],
                package_count=len(packages),
                asset_count=len(assets),
                h2c_estimate_state="unknown",
                **event_context,
            )
        )
        events.append(
            _event(
                "product_intake.h2c_estimate_missing",
                status="missing",
                severity="info",
                package_set_id=package_set_id,
                manifest_id=manifest["manifest_id"],
                manifest_checksum_sha256=manifest["manifest_checksum_sha256"],
                missing_reason_code=H2C_MISSING_REASON,
                h2c_stage_attempted=False,
                h2c_estimate_source=None,
                **event_context,
            )
        )
        manifest["audit_events"] = events

        _write_json(working_root_path / "asset-manifest-v0.json", manifest)
        _write_jsonl(working_root_path / "audit-events.jsonl", events)
        return manifest
    except Exception as exc:
        events.append(
            _event(
                _failure_event_name(exc),
                status="failed",
                severity="error",
                error_code=exc.__class__.__name__,
                error_message=_safe_error_message(str(exc)),
                **event_context,
            )
        )
        if working_root_path.exists():
            _write_jsonl(working_root_path / "audit-events.jsonl", events)
        raise


def run_listing_intelligence_workflow(
    source_zip_paths: Iterable[str | Path],
    working_root: str | Path,
    *,
    db_path: str | Path | None = None,
    intake_id: str | None = None,
    paperclip_issue_id: str | None = None,
    paperclip_issue_identifier: str | None = None,
    actor_type: str = "agent",
    actor_id: str | None = None,
    environment: str | None = None,
    evidence_paths: WorkflowEvidencePaths | None = None,
) -> dict[str, Any]:
    """Run deterministic listing-intelligence aggregation and persist final output atomically."""

    evidence_paths = evidence_paths or DEFAULT_WORKFLOW_EVIDENCE
    working_root_path = Path(working_root).resolve()
    db_path = Path(db_path) if db_path is not None else working_root_path / "listing-intelligence.sqlite3"
    manifest = build_asset_manifest(
        source_zip_paths,
        working_root_path,
        intake_id=intake_id,
        paperclip_issue_id=paperclip_issue_id,
        paperclip_issue_identifier=paperclip_issue_identifier,
        actor_type=actor_type,
        actor_id=actor_id,
        environment=environment,
        extract=True,
    )
    events = list(manifest["audit_events"])
    event_context = {
        "intake_id": manifest["intake_id"],
        "paperclip_issue_id": paperclip_issue_id,
        "paperclip_issue_identifier": paperclip_issue_identifier,
        "actor_type": actor_type,
        "actor_id_hash": _hash_text(actor_id) if actor_id else None,
        "environment": environment,
    }

    try:
        visual = _load_optional_json(evidence_paths.visual_analysis)
        copy = _load_optional_json(evidence_paths.marketplace_copy)
        estimate_source = _load_optional_json(evidence_paths.technical_estimate)
        events.append(_stage_event("listing_intelligence.visual_loaded", "visual_id", visual, **event_context))
        events.append(_stage_event("listing_intelligence.copy_loaded", "copy", copy, **event_context))
        events.append(_stage_event("listing_intelligence.estimate_loaded", "h2c_estimates", estimate_source, **event_context))

        product_identity = _synthesize_product_identity(visual, copy)
        hero_image = _synthesize_hero_image(visual, manifest)
        background = _synthesize_background(visual)
        listing_copy = _synthesize_listing_copy(copy)
        print_estimate = _synthesize_print_estimate(estimate_source, manifest)
        marketplace_policy = _evaluate_marketplace_policy(copy, print_estimate)
        qa_gate = _evaluate_qa_gate(product_identity, hero_image, background, listing_copy, print_estimate, marketplace_policy)

        final_record = _final_record(
            manifest,
            product_identity,
            hero_image,
            background,
            listing_copy,
            print_estimate,
            marketplace_policy,
            qa_gate,
            events,
        )
        final_record["auditTrail"].append(
            _event(
                "listing_intelligence.final_record_generated",
                status="succeeded",
                severity="info",
                finalRecordId=final_record["finalRecordId"],
                readinessVerdict=final_record["readinessVerdict"],
                **event_context,
            )
        )
        final_record["auditTrail"].append(
            _event(
                "listing_intelligence.persistence_started",
                status="started",
                severity="info",
                finalRecordId=final_record["finalRecordId"],
                **event_context,
            )
        )
        _persist_final_record(db_path, final_record)
        final_record["auditTrail"].append(
            _event(
                "listing_intelligence.persistence_committed",
                status="succeeded",
                severity="info",
                finalRecordId=final_record["finalRecordId"],
                persistenceRef=_path_ref(Path(db_path)),
                **event_context,
            )
        )
        _write_json(working_root_path / "product-intelligence-final-v1.json", final_record)
        _write_jsonl(working_root_path / "audit-events.jsonl", final_record["auditTrail"])
        return final_record
    except Exception as exc:
        events.append(
            _event(
                "listing_intelligence.workflow_failed",
                status="failed",
                severity="error",
                error_code=exc.__class__.__name__,
                error_message=_safe_error_message(str(exc)),
                **event_context,
            )
        )
        _write_jsonl(working_root_path / "audit-events.jsonl", events)
        raise


def _source_package(path: Path) -> SourcePackage:
    if not path.exists():
        raise IntakeError(f"source ZIP does not exist: {path}")
    if not path.is_file():
        raise IntakeError(f"source ZIP is not a file: {path}")
    checksum = _sha256_file(path)
    source_zip_id = f"sha256:{checksum}"
    return SourcePackage(
        path=path,
        package_role=_infer_package_role(path),
        package_id=f"zip_{checksum[:16]}",
        source_zip_id=source_zip_id,
        checksum_sha256=source_zip_id,
        size_bytes=path.stat().st_size,
    )


def _package_manifest(source: SourcePackage, package_set_id: str, intake_id: str) -> dict[str, Any]:
    return {
        "intake_id": intake_id,
        "package_set_id": package_set_id,
        "package_id": source.package_id,
        "source_zip_id": source.source_zip_id,
        "package_role": source.package_role,
        "source_zip_path": _path_ref(source.path),
        "source_zip_name_hash": _hash_text(source.path.name),
        "original_filename": source.path.name,
        "mime_type": "application/zip",
        "checksum": source.checksum_sha256,
        "size_bytes": source.size_bytes,
        "original_preserved": True,
        "audit_correlation_id": intake_id,
    }


def _validate_zip(path: Path) -> list[zipfile.ZipInfo]:
    try:
        with zipfile.ZipFile(path, "r") as zf:
            bad = zf.testzip()
            if bad is not None:
                raise IntakeError(f"ZIP failed CRC validation at member: {_safe_error_message(bad)}")
            infos = zf.infolist()
    except zipfile.BadZipFile as exc:
        raise IntakeError("invalid or corrupt ZIP file") from exc
    if not infos:
        raise IntakeError("empty ZIP file")
    total_file_size = 0
    for info in infos:
        _safe_member_path(info.filename)
        if info.is_dir():
            continue
        ext = _extension(info.filename)
        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedZipEntryError(f"unsupported ZIP member extension: {_safe_error_message(info.filename)}")
        if info.file_size > MAX_EXTRACTED_FILE_BYTES:
            raise ArchiveSizeLimitError(f"ZIP member exceeds extraction limit: {_safe_error_message(info.filename)}")
        total_file_size += info.file_size
        if total_file_size > MAX_TOTAL_EXTRACTED_BYTES:
            raise ArchiveSizeLimitError("ZIP archive exceeds total extraction limit")
    return infos


def _read_zip_member_for_extract(
    zf: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    *,
    extract: bool,
) -> tuple[str, bytes]:
    if info.file_size > MAX_EXTRACTED_FILE_BYTES:
        raise ArchiveSizeLimitError(f"ZIP member exceeds extraction limit: {_safe_error_message(info.filename)}")
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0
    with zf.open(info, "r") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            total += len(chunk)
            if total > MAX_EXTRACTED_FILE_BYTES:
                raise ArchiveSizeLimitError(f"ZIP member exceeds extraction limit: {_safe_error_message(info.filename)}")
            digest.update(chunk)
            if extract:
                chunks.append(chunk)
    return digest.hexdigest(), b"".join(chunks)


def _safe_intake_id(value: str) -> str:
    if not value or CONTROL_CHARS.search(value):
        raise UnsafeZipEntryError("intake_id is empty or contains control characters")
    if value in {".", ".."} or "/" in value or "\\" in value or WINDOWS_DRIVE.match(value):
        raise UnsafeZipEntryError("intake_id must be a safe path segment")
    sanitized = SAFE_SEGMENT_CHARS.sub("_", value).strip(" .")
    if sanitized != value or not sanitized:
        raise UnsafeZipEntryError("intake_id contains unsupported characters")
    return value


def _safe_member_path(member_name: str) -> PurePosixPath:
    normalized_name = member_name.replace("\\", "/")
    if CONTROL_CHARS.search(normalized_name):
        raise UnsafeZipEntryError("ZIP member contains control characters")
    if normalized_name.startswith("/") or normalized_name.startswith("//"):
        raise UnsafeZipEntryError("ZIP member uses absolute path")
    if WINDOWS_DRIVE.match(normalized_name):
        raise UnsafeZipEntryError("ZIP member uses Windows drive path")
    path = PurePosixPath(normalized_name)
    if not path.parts or path.name == "":
        return path
    for part in path.parts:
        if part in ("", ".", ".."):
            raise UnsafeZipEntryError("ZIP member uses unsafe relative path")
    return path


def _sanitize_relative_path(path: PurePosixPath) -> str:
    sanitized_parts: list[str] = []
    for part in path.parts:
        sanitized = SAFE_SEGMENT_CHARS.sub("_", part).strip(" .")
        if not sanitized:
            sanitized = "unnamed"
        stem = sanitized.split(".", 1)[0].upper()
        if stem in RESERVED_WINDOWS_NAMES:
            sanitized = f"_{sanitized}"
        sanitized_parts.append(sanitized)
    return "/".join(sanitized_parts)


def _dedupe_relative_path(relative_path: str, seen: dict[str, int]) -> str:
    key = relative_path.casefold()
    count = seen.get(key, 0)
    seen[key] = count + 1
    if count == 0:
        return relative_path
    path = PurePosixPath(relative_path)
    suffix = path.suffix
    stem = path.name[: -len(suffix)] if suffix else path.name
    new_name = f"{stem}__{count + 1}{suffix}"
    return str(path.with_name(new_name))


def _ensure_within(root: Path, target: Path) -> None:
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise UnsafeZipEntryError("extraction target escapes working root") from exc


def _asset_type(extension: str) -> str:
    if extension in MEDIA_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    if extension in MODEL_EXTENSIONS:
        return "model"
    if extension in DOCUMENT_EXTENSIONS:
        return "document"
    return "other_supported" if extension in SUPPORTED_EXTENSIONS else "unsupported"


def _mime_type(extension: str) -> str | None:
    if extension == ".3mf":
        return "model/3mf"
    if extension == ".stl":
        return "model/stl"
    if extension in {".step", ".stp"}:
        return "model/step"
    guessed = mimetypes.types_map.get(extension)
    return guessed


def _extension(filename: str) -> str:
    return PurePosixPath(filename).suffix.lower()


def _infer_package_role(path: Path) -> str:
    name = path.name.lower()
    if "media" in name:
        return "media"
    if any(token in name for token in ("model", "box", "sticker", "pitch")):
        return "model"
    return "unknown"


def _asset_groups(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model_ids = [a["asset_id"] for a in assets if a["asset_type"] == "model"]
    media_doc_ids = [a["asset_id"] for a in assets if a["asset_type"] in {"image", "video", "document"}]
    return [
        {
            "asset_group": DEFAULT_ASSET_GROUP,
            "asset_count": len(assets),
            "model_asset_ids": model_ids,
            "media_asset_ids": media_doc_ids,
            "h2c_estimate_state": "unknown",
            "h2c_estimate_source": None,
        }
    ]


def _load_optional_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _stage_event(event_name: str, stage: str, payload: dict[str, Any] | None, **context: Any) -> dict[str, Any]:
    return _event(
        event_name,
        status="succeeded" if payload is not None else "missing",
        severity="info" if payload is not None else "warning",
        stage=stage,
        schemaVersion=payload.get("schemaVersion") if payload else None,
        evidencePresent=payload is not None,
        **context,
    )


def _synthesize_product_identity(visual: dict[str, Any] | None, copy: dict[str, Any] | None) -> dict[str, Any]:
    visual_identity = (visual or {}).get("productIdentification") or {}
    copy_identity = _copy_payload(copy).get("productIdentity") or {}
    return {
        "workingName": copy_identity.get("workingName") or visual_identity.get("plainEnglishName"),
        "plainEnglishName": visual_identity.get("plainEnglishName") or copy_identity.get("workingName"),
        "productType": visual_identity.get("productType") or copy_identity.get("physicalProductType"),
        "physicalProductType": copy_identity.get("physicalProductType"),
        "targetBuyer": copy_identity.get("targetBuyer") or visual_identity.get("targetBuyer"),
        "likelyUseCase": visual_identity.get("likelyUseCase"),
        "confidence": visual_identity.get("confidence"),
        "evidenceRefs": _evidence_refs("visual", visual_identity.get("evidenceAssets")),
    }


def _synthesize_hero_image(visual: dict[str, Any] | None, manifest: dict[str, Any]) -> dict[str, Any]:
    decision = (visual or {}).get("heroImageDecision") or {}
    selected = decision.get("selectedHero") or {}
    asset = _find_asset_for_filename(manifest, selected.get("filename"))
    return {
        "status": decision.get("status") or "missing",
        "assetId": selected.get("assetId"),
        "filename": selected.get("filename"),
        "manifestAssetId": asset.get("asset_id") if asset else None,
        "score100": selected.get("score100"),
        "conversionRationale": selected.get("conversionRationale"),
        "workingCopyPath": asset.get("working_copy_path") if asset else None,
        "backupImages": decision.get("backupImages") or [],
    }


def _synthesize_background(visual: dict[str, Any] | None) -> dict[str, Any]:
    recommendation = ((visual or {}).get("backgroundRecommendation") or {}).get("recommendedBackground") or {}
    return {
        "colorName": recommendation.get("colorName"),
        "hex": recommendation.get("hex"),
        "confidence": recommendation.get("confidence"),
        "rationale": recommendation.get("rationale"),
    }


def _synthesize_listing_copy(copy: dict[str, Any] | None) -> dict[str, Any]:
    payload = _copy_payload(copy)
    title = _first_by_status(payload.get("titleVariants") or [])
    description = _first_by_status(payload.get("descriptionVariants") or [])
    return {
        "title": title.get("text"),
        "titleVariantId": title.get("id"),
        "description": description.get("text"),
        "descriptionVariantId": description.get("id"),
        "bullets": [item.get("text") for item in payload.get("bullets") or [] if item.get("text")],
        "tags": payload.get("tags") or [],
        "excludedClaims": payload.get("excludedClaims") or [],
        "policyFlags": payload.get("policyFlags") or [],
        "status": "draft_pending_policy_review" if title and description else "missing",
    }


def _synthesize_print_estimate(estimate_source: dict[str, Any] | None, manifest: dict[str, Any]) -> dict[str, Any]:
    conclusion = (estimate_source or {}).get("estimate_conclusion") or {}
    state = conclusion.get("state") or manifest.get("h2c_estimate_state") or "unknown"
    reasons = []
    if state == "requires_h2c_profile":
        reasons.append("missing_h2c_profile")
    elif state in {"unknown", "unavailable"}:
        reasons.append(manifest.get("h2c_missing_reason_code") or "estimate_unavailable")
    return {
        "schemaVersion": TECHNICAL_ESTIMATE_SCHEMA_VERSION,
        "state": state,
        "targetPrinterProfile": {
            "printerFamily": "H2C",
            "profileId": None,
            "profileVersion": None,
            "materialProfileId": None,
        },
        "printTimeMinutes": conclusion.get("print_time_minutes"),
        "filamentGrams": conclusion.get("filament_grams"),
        "materialCost": conclusion.get("material_cost"),
        "currency": None,
        "source": {
            "type": "none" if state == "requires_h2c_profile" else "manifest",
            "evidenceRefs": ["work-products/WEB-31/metadata-extraction-summary.json#estimate_conclusion"],
        },
        "confidence": "none" if conclusion.get("print_time_minutes") is None else "medium",
        "publishable": state == "extracted",
        "humanReviewRequired": bool(conclusion.get("human_review_required")),
        "reasons": reasons,
        "reason": conclusion.get("reason"),
    }


def _evaluate_marketplace_policy(copy: dict[str, Any] | None, print_estimate: dict[str, Any]) -> dict[str, Any]:
    payload = _copy_payload(copy)
    review_reasons = []
    if print_estimate.get("state") != "extracted":
        review_reasons.append("missing_h2c_profile")
    policy_flags = payload.get("policyFlags") or []
    if policy_flags:
        review_reasons.extend(_policy_flag_code(flag) for flag in policy_flags)
    if "licensing_unverified" not in review_reasons:
        review_reasons.append("licensing_unverified")
    review_reasons.append("marketplace_policy_final_approval_required")
    categories = {
        "weapons": {"status": "clear", "severity": "low"},
        "dangerousOrRegulated": {"status": "clear", "severity": "low"},
        "counterfeitOrBranded": {"status": "unknown", "severity": "medium"},
        "adultOrGraphic": {"status": "clear", "severity": "low"},
        "medicalOrHealth": {"status": "clear", "severity": "low"},
        "illegalOrProhibited": {"status": "unknown", "severity": "medium"},
        "childSafetyOrSmallParts": {"status": "unknown", "severity": "medium"},
        "ipOrLicensing": {"status": "unknown", "severity": "medium"},
        "technicalClaims": {"status": "suspected", "severity": "medium"},
    }
    return {
        "schemaVersion": POLICY_RESULT_SCHEMA_VERSION,
        "decision": "human_review",
        "publishable": False,
        "categories": categories,
        "humanReviewRequired": True,
        "reviewReasons": sorted(set(review_reasons)),
        "evidenceRefs": [
            "work-products/WEB-29/visual-analysis-output.json",
            "work-products/WEB-30/marketplace-copy-output.json",
            "work-products/WEB-31/metadata-extraction-summary.json",
        ],
        "redactions": ["no_private_asset_contents_exposed"],
        "reviewerDisposition": None,
    }


def _evaluate_qa_gate(
    product_identity: dict[str, Any],
    hero_image: dict[str, Any],
    background: dict[str, Any],
    listing_copy: dict[str, Any],
    print_estimate: dict[str, Any],
    marketplace_policy: dict[str, Any],
) -> dict[str, Any]:
    checks = {
        "productIdentity": bool(product_identity.get("workingName") and product_identity.get("productType")),
        "heroImage": bool(hero_image.get("assetId") and hero_image.get("workingCopyPath")),
        "background": bool(background.get("colorName")),
        "listingCopy": bool(listing_copy.get("title") and listing_copy.get("description")),
        "printEstimate": print_estimate.get("state") in {"extracted", "requires_h2c_profile", "unavailable", "human_review"},
        "marketplacePolicy": marketplace_policy.get("decision") in {"pass", "human_review", "block"},
    }
    blockers = [name for name, ok in checks.items() if not ok]
    if marketplace_policy.get("publishable") is not True:
        blockers.append("marketplacePolicy.publishable")
    if print_estimate.get("publishable") is not True:
        blockers.append("printEstimate.publishable")
    return {
        "schemaVersion": "listing-qa-gate.v1",
        "status": "human_review" if blockers else "pass",
        "publishable": not blockers,
        "checks": checks,
        "blockers": sorted(set(blockers)),
    }


def _final_record(
    manifest: dict[str, Any],
    product_identity: dict[str, Any],
    hero_image: dict[str, Any],
    background: dict[str, Any],
    listing_copy: dict[str, Any],
    print_estimate: dict[str, Any],
    marketplace_policy: dict[str, Any],
    qa_gate: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    final_record_id = f"final_{hashlib.sha256(manifest['manifest_checksum_sha256'].encode('utf-8')).hexdigest()[:16]}"
    readiness = "ready" if qa_gate["publishable"] else "human_review_required"
    return {
        "schemaVersion": FINAL_RECORD_SCHEMA_VERSION,
        "workflowSchemaVersion": WORKFLOW_SCHEMA_VERSION,
        "finalRecordId": final_record_id,
        "intakeId": manifest["intake_id"],
        "packageSetId": manifest["package_set_id"],
        "manifestId": manifest["manifest_id"],
        "manifestChecksum": manifest["manifest_checksum_sha256"],
        "createdAt": _now(),
        "readinessVerdict": readiness,
        "status": "completed",
        "completedAt": _now(),
        "publishable": qa_gate["publishable"],
        "productIdentity": product_identity,
        "heroImage": hero_image,
        "background": background,
        "listingCopy": listing_copy,
        "printEstimate": print_estimate,
        "marketplacePolicy": marketplace_policy,
        "finalQuality": qa_gate,
        "qaGate": qa_gate,
        "specialistOutputs": _specialist_outputs(product_identity, hero_image, background, listing_copy, print_estimate, marketplace_policy, qa_gate),
        "evidence": _final_evidence_refs(product_identity, marketplace_policy),
        "originalPreservationState": {
            "sourcePackagesPreserved": manifest["originals_preserved"],
            "workingCopiesOnly": True,
            "packages": manifest["packages"],
            "assets": manifest["assets"],
        },
        "assetManifest": {
            "packages": manifest["packages"],
            "assetCount": len(manifest["assets"]),
            "assetGroups": manifest["asset_groups"],
        },
        "auditTrail": events,
    }


def _specialist_outputs(
    product_identity: dict[str, Any],
    hero_image: dict[str, Any],
    background: dict[str, Any],
    listing_copy: dict[str, Any],
    print_estimate: dict[str, Any],
    marketplace_policy: dict[str, Any],
    qa_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        {"decisionType": "visual_identity", "payload": product_identity},
        {"decisionType": "hero_image", "payload": {"heroImage": hero_image, "background": background}},
        {"decisionType": "listing_copy", "payload": listing_copy},
        {"decisionType": "h2c_estimate", "payload": print_estimate},
        {"decisionType": "marketplace_policy", "payload": marketplace_policy},
        {"decisionType": "listing_quality", "payload": qa_gate},
    ]


def _final_evidence_refs(product_identity: dict[str, Any], marketplace_policy: dict[str, Any]) -> list[dict[str, Any]]:
    refs = [{"type": "asset", "ref": ref} for ref in product_identity.get("evidenceRefs", [])]
    refs.extend({"type": "work_product", "ref": ref} for ref in marketplace_policy.get("evidenceRefs", []))
    return refs


def _persist_final_record(db_path: Path, final_record: dict[str, Any]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(final_record, sort_keys=True)
    with _sqlite_connection(db_path) as conn:
        try:
            conn.execute("BEGIN")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_intelligence_records (
                    final_record_id TEXT PRIMARY KEY,
                    intake_id TEXT NOT NULL,
                    package_set_id TEXT NOT NULL,
                    manifest_id TEXT NOT NULL,
                    readiness_verdict TEXT NOT NULL,
                    publishable INTEGER NOT NULL,
                    record_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS product_intelligence_audit_events (
                    event_id TEXT PRIMARY KEY,
                    final_record_id TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    FOREIGN KEY(final_record_id) REFERENCES product_intelligence_records(final_record_id)
                )
                """
            )
            conn.execute(
                """
                INSERT OR REPLACE INTO product_intelligence_records
                (final_record_id, intake_id, package_set_id, manifest_id, readiness_verdict, publishable, record_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    final_record["finalRecordId"],
                    final_record["intakeId"],
                    final_record["packageSetId"],
                    final_record["manifestId"],
                    final_record["readinessVerdict"],
                    1 if final_record["publishable"] else 0,
                    payload,
                    final_record["createdAt"],
                ),
            )
            for event in final_record["auditTrail"]:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO product_intelligence_audit_events
                    (event_id, final_record_id, event_time, event_name, event_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event["event_id"],
                        final_record["finalRecordId"],
                        event["event_time"],
                        event["event_name"],
                        json.dumps(event, sort_keys=True),
                    ),
                )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            raise PersistenceError("failed to persist final product intelligence record") from exc


@contextmanager
def _sqlite_connection(path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def _copy_payload(copy: dict[str, Any] | None) -> dict[str, Any]:
    decisions = (copy or {}).get("decisions") or []
    for decision in decisions:
        if decision.get("type") == "marketplace_copy" and isinstance(decision.get("payload"), dict):
            return decision["payload"]
    return {}


def _first_by_status(items: list[dict[str, Any]]) -> dict[str, Any]:
    for item in items:
        if item.get("status") in {"supported_pending_policy_review", "supported"}:
            return item
    return items[0] if items else {}


def _find_asset_for_filename(manifest: dict[str, Any], filename: str | None) -> dict[str, Any] | None:
    if not filename:
        return None
    for asset in manifest.get("assets", []):
        if asset.get("original_filename") == filename or PurePosixPath(asset.get("original_relative_path", "")).name == filename:
            return asset
    return None


def _evidence_refs(prefix: str, rows: Any) -> list[str]:
    if not isinstance(rows, list):
        return []
    refs = []
    for row in rows:
        if isinstance(row, dict) and row.get("assetId"):
            refs.append(f"{prefix}:{row['assetId']}")
    return refs


def _policy_flag_code(flag: Any) -> str:
    if isinstance(flag, dict):
        return str(flag.get("code") or flag.get("id") or flag.get("type") or "policy_flag")
    return str(flag)


def _event(event_name: str, *, status: str, severity: str, **fields: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "event_id": _new_id("evt"),
        "event_name": event_name,
        "event_version": EVENT_VERSION,
        "event_time": _now(),
        "severity": severity,
        "status": status,
        "service_name": SERVICE_NAME,
        "environment": fields.pop("environment", None),
        "trace_id": None,
        "span_id": None,
        "correlation_id": fields.get("intake_id"),
    }
    base.update(fields)
    return base


def _failure_event_name(exc: Exception) -> str:
    if isinstance(exc, UnsafeZipEntryError):
        return "product_intake.zip_validation_failed"
    if isinstance(exc, IntakeError):
        return "product_intake.zip_validation_failed"
    return "product_intake.manifest_generation_failed"


def _safe_error_message(message: str) -> str:
    # Keep error useful without leaking absolute paths, tokens, or file content.
    message = re.sub(r"/[^\s:]+", "<path>", message)
    message = re.sub(r"[A-Za-z]:\\[^\s:]+", "<path>", message)
    return message[:240]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _package_set_id(sources: list[SourcePackage]) -> str:
    payload = "\n".join(sorted(s.source_zip_id for s in sources))
    return f"pkgset_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _manifest_row_id(intake_id: str, package_id: str, relative_path: str, asset_sha: str) -> str:
    payload = json.dumps([intake_id, package_id, relative_path, asset_sha], separators=(",", ":"))
    return f"row_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def _canonical_sha256(data: dict[str, Any]) -> str:
    clone = json.loads(json.dumps(data, sort_keys=True, separators=(",", ":")))
    clone["manifest_id"] = None
    clone["manifest_checksum_sha256"] = None
    clone["audit_events"] = []
    clone["generated_at"] = None
    payload = json.dumps(clone, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _hash_text(value: str | None) -> str | None:
    if value is None:
        return None
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _path_ref(path: Path) -> str:
    # A stable non-secret reference; no raw absolute path in audit events.
    name_hash = _hash_text(path.name)
    try:
        size = path.stat().st_size if path.exists() and path.is_file() else None
    except OSError:
        size = None
    payload = f"{path.name}:{size}"
    return f"pathref:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}:{name_hash}"


def _relative_posix(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
