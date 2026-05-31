from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import zipfile
from pathlib import Path

import pytest

from printing_magic_intake import (
    ArchiveSizeLimitError,
    UnsafeZipEntryError,
    UnsupportedZipEntryError,
    WorkflowEvidencePaths,
    build_asset_manifest,
    run_listing_intelligence_workflow,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PAPERCLIP_PROJECT_ROOT = Path(
    "/home/cweber/.paperclip/instances/default/projects/6e564770-9fdc-4fb4-b550-37e41ae47fa1/"
    "c9e9d509-8117-4fd8-9db8-29283e39764f"
)
FIXTURE_ROOT = Path(os.environ.get("WEB17_FIXTURE_ROOT", DEFAULT_PAPERCLIP_PROJECT_ROOT / "shared" / "tailscale-received" / "WEB-17-2026-05-30"))
MEDIA_ZIP = FIXTURE_ROOT / "collector-s-pitch-sticker-box-media-package.zip"
MODEL_ZIP = FIXTURE_ROOT / "Collectors_Pitch_Sticker_Box_fb278b1692.zip"

requires_web17_fixtures = pytest.mark.skipif(
    not MEDIA_ZIP.exists() or not MODEL_ZIP.exists(),
    reason="WEB-17 staged fixture zips not available",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_minimal_zip(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("Collector_s_Pitch_Sticker_Box8_b202b1fea6.png", b"image")
        zf.writestr("models/box.stl", b"model")
    return path


def _write_evidence(root: Path) -> WorkflowEvidencePaths:
    root.mkdir(parents=True, exist_ok=True)
    visual = root / "visual.json"
    copy = root / "copy.json"
    estimate = root / "estimate.json"
    visual.write_text(
        json.dumps(
            {
                "schemaVersion": "visual-analysis-output.v1",
                "productIdentification": {
                    "plainEnglishName": "Collector's Pitch Sticker Box",
                    "productType": "collector_card_or_sticker_storage_box",
                    "likelyUseCase": "Store flat collectibles.",
                    "confidence": 0.91,
                    "evidenceAssets": [{"assetId": "Collector_s_Pitch_Sticker_Box8_b202b1fea6"}],
                },
                "heroImageDecision": {
                    "status": "selected",
                    "selectedHero": {
                        "assetId": "Collector_s_Pitch_Sticker_Box8_b202b1fea6",
                        "filename": "Collector_s_Pitch_Sticker_Box8_b202b1fea6.png",
                        "score100": 94,
                        "conversionRationale": "Clear product identity.",
                    },
                },
                "backgroundRecommendation": {
                    "recommendedBackground": {"colorName": "black", "hex": "#000000", "confidence": 0.88}
                },
            }
        ),
        encoding="utf-8",
    )
    copy.write_text(
        json.dumps(
            {
                "schemaVersion": "analysis.agent-output.v1",
                "decisions": [
                    {
                        "type": "marketplace_copy",
                        "payload": {
                            "productIdentity": {
                                "workingName": "Collectors Pitch Sticker Box",
                                "physicalProductType": "3D printed sticker/storage box",
                                "targetBuyer": ["Sticker collectors"],
                            },
                            "titleVariants": [
                                {"id": "t1", "text": "Collectors Pitch Sticker Box", "status": "supported_pending_policy_review"}
                            ],
                            "descriptionVariants": [
                                {"id": "d1", "text": "A physical soccer-themed sticker storage box.", "status": "supported_pending_policy_review"}
                            ],
                            "bullets": [{"text": "Physical storage box"}],
                            "policyFlags": [{"code": "licensing_unverified"}],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    estimate.write_text(
        json.dumps(
            {
                "estimate_conclusion": {
                    "state": "requires_h2c_profile",
                    "print_time_minutes": None,
                    "filament_grams": None,
                    "material_cost": None,
                    "reason": "No H2C profile.",
                    "human_review_required": False,
                }
            }
        ),
        encoding="utf-8",
    )
    return WorkflowEvidencePaths(visual, copy, estimate)


@requires_web17_fixtures
def test_fixture_manifest_matches_web13_golden_inventory(tmp_path: Path) -> None:
    before = {MEDIA_ZIP: _sha256(MEDIA_ZIP), MODEL_ZIP: _sha256(MODEL_ZIP)}

    manifest = build_asset_manifest(
        [MEDIA_ZIP, MODEL_ZIP],
        tmp_path / "work",
        intake_id="intake_test_fixture",
        paperclip_issue_id="679ee145-b5de-4e44-9ef2-f556648afce2",
        paperclip_issue_identifier="WEB-18",
        environment="test",
    )

    assert {path: _sha256(path) for path in before} == before, "source ZIP bytes changed"
    assert manifest["schema_version"] == "0.1"
    assert manifest["originals_preserved"] is True
    assert manifest["h2c_estimate_state"] == "unknown"
    assert manifest["h2c_estimate_source"] is None
    assert manifest["unknowns"]["h2c_print_estimate"] is None
    assert len(manifest["packages"]) == 2
    assert len(manifest["assets"]) == 44

    by_name = {pkg["original_filename"]: pkg for pkg in manifest["packages"]}
    assert by_name[MEDIA_ZIP.name]["size_bytes"] == 14_152_671
    assert by_name[MEDIA_ZIP.name]["checksum"] == (
        "sha256:1432f5998ee1df937ad3c93bf4f6a66f7e3e9c14a20c80abf8918ce93303f395"
    )
    assert by_name[MEDIA_ZIP.name]["package_role"] == "media"
    assert by_name[MODEL_ZIP.name]["size_bytes"] == 194_471_799
    assert by_name[MODEL_ZIP.name]["checksum"] == (
        "sha256:7d3ca3d23ea6e014240921d3d529027e2612bef8726941fa1becb5b2f8ab5255"
    )
    assert by_name[MODEL_ZIP.name]["package_role"] == "model"

    type_counts: dict[str, int] = {}
    ext_counts: dict[str, int] = {}
    for asset in manifest["assets"]:
        type_counts[asset["asset_type"]] = type_counts.get(asset["asset_type"], 0) + 1
        ext_counts[asset["extension"]] = ext_counts.get(asset["extension"], 0) + 1
        assert asset["original_preserved"] is True
        assert asset["working_copy_path"]
        assert not Path(asset["working_copy_path"]).is_absolute()
        assert asset["h2c_estimate_state"] == "unknown"
        assert asset["h2c_estimate_source"] is None
        assert "print_time_minutes" not in asset
        assert "filament_grams" not in asset

    assert type_counts == {"image": 16, "video": 1, "document": 1, "model": 26}
    assert ext_counts == {".png": 16, ".webm": 1, ".pdf": 1, ".3mf": 6, ".stl": 20}
    assert manifest["asset_groups"] == [
        {
            "asset_group": "product-package-default",
            "asset_count": 44,
            "model_asset_ids": [a["asset_id"] for a in manifest["assets"] if a["asset_type"] == "model"],
            "media_asset_ids": [
                a["asset_id"]
                for a in manifest["assets"]
                if a["asset_type"] in {"image", "video", "document"}
            ],
            "h2c_estimate_state": "unknown",
            "h2c_estimate_source": None,
        }
    ]

    event_names = [event["event_name"] for event in manifest["audit_events"]]
    assert event_names.count("product_intake.package_received") == 2
    assert event_names.count("product_intake.zip_validated") == 2
    assert event_names.count("product_intake.assets_extracted") == 2
    assert "product_intake.manifest_generated" in event_names
    assert "product_intake.h2c_estimate_missing" in event_names
    for event in manifest["audit_events"]:
        serialized = json.dumps(event)
        assert str(FIXTURE_ROOT) not in serialized
        assert event["service_name"] == "product-intake"
        assert event["event_version"] == 1

    assert (tmp_path / "work" / "asset-manifest-v0.json").exists()
    assert (tmp_path / "work" / "audit-events.jsonl").exists()


def test_rejects_zip_slip_and_preserves_original(tmp_path: Path) -> None:
    bad_zip = tmp_path / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("../escape.stl", "not a real model")
    before = bad_zip.read_bytes()

    with pytest.raises(UnsafeZipEntryError):
        build_asset_manifest([bad_zip], tmp_path / "work", intake_id="intake_bad", environment="test")

    assert bad_zip.read_bytes() == before
    assert (tmp_path / "work" / "audit-events.jsonl").exists()
    assert "product_intake.zip_validation_failed" in (tmp_path / "work" / "audit-events.jsonl").read_text()


def test_duplicate_sanitized_names_do_not_overwrite(tmp_path: Path) -> None:
    dup_zip = tmp_path / "dups.zip"
    with zipfile.ZipFile(dup_zip, "w") as zf:
        zf.writestr("nested/a?.stl", "first")
        zf.writestr("nested/a*.stl", "second")

    manifest = build_asset_manifest([dup_zip], tmp_path / "work", intake_id="intake_dups", environment="test")

    normalized = [asset["normalized_relative_path"] for asset in manifest["assets"]]
    assert normalized == ["nested/a_.stl", "nested/a___2.stl"]
    extracted_paths = [tmp_path / "work" / asset["working_copy_path"] for asset in manifest["assets"]]
    assert [path.read_text() for path in extracted_paths] == ["first", "second"]


def test_rejects_absolute_and_backslash_traversal_paths(tmp_path: Path) -> None:
    for member_name in ["/abs/model.stl", "safe/..\\escape.stl", "C:/temp/model.stl"]:
        bad_zip = tmp_path / f"bad-{hash(member_name)}.zip"
        with zipfile.ZipFile(bad_zip, "w") as zf:
            zf.writestr(member_name, "payload")
        with pytest.raises(UnsafeZipEntryError):
            build_asset_manifest([bad_zip], tmp_path / f"work-{hash(member_name)}", environment="test")


def test_rejects_unsupported_extension_before_extraction(tmp_path: Path) -> None:
    bad_zip = tmp_path / "unsupported.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("safe/model.stl", "payload")
        zf.writestr("safe/evil.exe", "payload")

    with pytest.raises(UnsupportedZipEntryError):
        build_asset_manifest([bad_zip], tmp_path / "work", intake_id="intake_unsupported", environment="test")

    assert not any(path.is_file() for path in (tmp_path / "work" / "extracted").glob("**/*"))
    assert "product_intake.zip_validation_failed" in (tmp_path / "work" / "audit-events.jsonl").read_text()


def test_rejects_intake_id_path_escape_without_writing_files(tmp_path: Path) -> None:
    good_zip = _write_minimal_zip(tmp_path / "good.zip")

    with pytest.raises(UnsafeZipEntryError):
        build_asset_manifest([good_zip], tmp_path / "work", intake_id="../../escape", environment="test")

    assert not (tmp_path / "escape").exists()


def test_rejects_zip_member_over_size_limit(tmp_path: Path) -> None:
    huge_zip = tmp_path / "huge.zip"
    with zipfile.ZipFile(huge_zip, "w") as zf:
        zf.writestr("huge.stl", b"0" * (64 * 1024 * 1024 + 1))

    with pytest.raises(ArchiveSizeLimitError):
        build_asset_manifest([huge_zip], tmp_path / "work", intake_id="intake_huge", environment="test")


def test_listing_intelligence_workflow_persists_final_record_transactionally(tmp_path: Path) -> None:
    source_zip = _write_minimal_zip(tmp_path / "fixture.zip")
    evidence = _write_evidence(tmp_path / "evidence")
    work = tmp_path / "work"
    db_path = tmp_path / "records.sqlite3"

    record = run_listing_intelligence_workflow(
        [source_zip],
        work,
        db_path=db_path,
        intake_id="intake_workflow",
        paperclip_issue_identifier="GST-3",
        environment="test",
        evidence_paths=evidence,
    )

    assert record["schemaVersion"] == "product-intelligence-final.v1"
    assert record["status"] == "completed"
    assert record["readinessVerdict"] == "human_review_required"
    assert record["productIdentity"]["workingName"] == "Collectors Pitch Sticker Box"
    assert record["heroImage"]["workingCopyPath"]
    assert record["background"]["hex"] == "#000000"
    assert record["listingCopy"]["title"] == "Collectors Pitch Sticker Box"
    assert record["printEstimate"]["state"] == "requires_h2c_profile"
    assert record["printEstimate"]["printTimeMinutes"] is None
    assert record["marketplacePolicy"]["decision"] == "human_review"
    assert record["finalQuality"] == record["qaGate"]
    assert record["qaGate"]["status"] == "human_review"
    assert {item["decisionType"] for item in record["specialistOutputs"]} == {
        "visual_identity",
        "hero_image",
        "listing_copy",
        "h2c_estimate",
        "marketplace_policy",
        "listing_quality",
    }
    assert record["evidence"]
    assert record["originalPreservationState"]["sourcePackagesPreserved"] is True
    assert record["originalPreservationState"]["workingCopiesOnly"] is True
    assert any(event["event_name"] == "listing_intelligence.persistence_committed" for event in record["auditTrail"])
    assert (work / "product-intelligence-final-v1.json").exists()

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM product_intelligence_records").fetchone()[0]
        audit_count = conn.execute("SELECT COUNT(*) FROM product_intelligence_audit_events").fetchone()[0]
    assert count == 1
    assert audit_count >= 1


@requires_web17_fixtures
def test_manifest_generation_reproducible_except_declared_unknown_ids(tmp_path: Path) -> None:
    manifest_a = build_asset_manifest([MEDIA_ZIP], tmp_path / "a", intake_id="stable", environment="test")
    manifest_b = build_asset_manifest([MEDIA_ZIP], tmp_path / "b", intake_id="stable", environment="test")

    def stable_view(manifest: dict) -> dict:
        clone = json.loads(json.dumps(manifest, sort_keys=True))
        clone["generated_at"] = None
        clone["audit_events"] = []
        clone["manifest_id"] = None
        clone["manifest_checksum_sha256"] = None
        for asset in clone["assets"]:
            asset["working_copy_id"] = None
        return clone

    assert stable_view(manifest_a) == stable_view(manifest_b)
