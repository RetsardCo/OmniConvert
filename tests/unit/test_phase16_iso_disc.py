import pytest
from pathlib import Path
import pycdlib

from omniconvert.core.file_detector import inspect_file
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.core.validation import validate_output
from omniconvert.engines.archive_engine import ArchiveEngine
from omniconvert.models.conversion_job import ConversionJob


def test_iso_creation_inspection_and_extraction(tmp_path: Path):
    engine = ArchiveEngine()

    # 1. Prepare directory structure with nested files
    src_dir = tmp_path / "disc_content"
    src_dir.mkdir()
    (src_dir / "README.txt").write_text("OmniConvert ISO Disc Image Test")
    sub_dir = src_dir / "media"
    sub_dir.mkdir()
    (sub_dir / "data.bin").write_bytes(b"\x00\x01\x02\x03\x04\x05")

    # 2. Master / Create ISO
    out_iso = tmp_path / "test_disc.iso"
    result = engine.create_iso(src_dir, out_iso)
    assert result.exists()
    assert result == out_iso
    assert out_iso.stat().st_size > 0

    # 3. Output Validation
    is_valid, err = validate_output(out_iso, "iso")
    assert is_valid is True
    assert err is None

    # 4. File Detection (sniffing format and category)
    meta = inspect_file(out_iso)
    assert meta.detected_format == "iso"
    assert meta.category == "archive"
    assert meta.detected_mime == "application/x-iso9660-image"

    # 5. Archive Inspection (Manifest check)
    inspection = engine.inspect_archive(out_iso)
    assert inspection.is_valid is True
    assert inspection.format == "iso"
    assert len(inspection.entries) >= 2
    entry_names = [e.name for e in inspection.entries]
    assert any("README.txt" in n for n in entry_names)
    assert any("media" in n for n in entry_names)

    # 6. Extract ISO Safely
    dest_dir = tmp_path / "extracted_disc"
    engine.extract_safely(out_iso, dest_dir)
    assert (dest_dir / "README.txt").exists()
    assert (dest_dir / "README.txt").read_text() == "OmniConvert ISO Disc Image Test"
    assert (dest_dir / "media" / "data.bin").exists()
    assert (dest_dir / "media" / "data.bin").read_bytes() == b"\x00\x01\x02\x03\x04\x05"


def test_iso_capability_and_repack_job(tmp_path: Path):
    registry = CapabilityRegistry()
    engine = ArchiveEngine()

    # Create dummy ISO
    src_dir = tmp_path / "folder_to_burn"
    src_dir.mkdir()
    (src_dir / "notes.txt").write_text("Burn to ISO test")
    out_iso = tmp_path / "burned.iso"

    # Capability check for directory -> iso
    dir_meta = inspect_file(src_dir)
    dir_ops = registry.find_operations_for_file(dir_meta)
    assert any(op.output_format == "iso" for op in dir_ops)

    # Execute Job: Directory to ISO
    job = ConversionJob(
        source_path=src_dir,
        target_format="iso",
        operation_id="archive.to_iso",
        engine="archive"
    )
    workspace_dir = tmp_path / "workspace"
    workspace_dir.mkdir()

    generated_iso = engine.execute(job, workspace_dir)
    assert generated_iso.exists()
    assert generated_iso.suffix.lower() == ".iso"

    # Verify repack: ISO -> ZIP
    iso_meta = inspect_file(generated_iso)
    iso_ops = registry.find_operations_for_file(iso_meta)
    assert any(op.output_format == "zip" for op in iso_ops)
    assert any(op.output_format == "dir" for op in iso_ops)

    repack_job = ConversionJob(
        source_path=generated_iso,
        target_format="zip",
        operation_id="archive.to_zip",
        engine="archive"
    )
    repack_workspace = tmp_path / "repack_workspace"
    repack_workspace.mkdir()
    generated_zip = engine.execute(repack_job, repack_workspace)
    assert generated_zip.exists()
    assert generated_zip.suffix.lower() == ".zip"
