"""Unit, integration, and security tests for Phase 8: Archives and Compression."""

import pytest
import zipfile
import tarfile
import gzip
from pathlib import Path

from omniconvert.engines.archive_engine import ArchiveEngine, is_safe_archive_member_path
from omniconvert.models.conversion_job import ConversionJob


def test_safe_member_path_validation(tmp_path):
    """Verify path traversal, absolute paths, and drive-letter paths are rejected."""
    assert is_safe_archive_member_path("folder/readme.txt", tmp_path)
    assert not is_safe_archive_member_path("../evil.txt", tmp_path)
    assert not is_safe_archive_member_path("folder/../../outside.dll", tmp_path)
    assert not is_safe_archive_member_path("/etc/passwd", tmp_path)
    assert not is_safe_archive_member_path("\\Windows\\System32\\cmd.exe", tmp_path)
    assert not is_safe_archive_member_path("C:/Windows/win.ini", tmp_path)


def test_zip_creation_listing_and_extraction(tmp_path):
    """Verify creating, inspecting, and extracting a ZIP archive."""
    src_dir = tmp_path / "source_files"
    src_dir.mkdir()
    (src_dir / "hello.txt").write_text("OmniConvert Archive Test", encoding="utf-8")
    sub = src_dir / "nested"
    sub.mkdir()
    (sub / "data.json").write_text('{"ok": true}', encoding="utf-8")

    engine = ArchiveEngine()

    # 1. Create ZIP
    job_create = ConversionJob(
        source_path=src_dir,
        target_format="zip",
        operation_id="archive.to_zip",
        engine="archive"
    )
    ws_create = tmp_path / "ws_create"
    ws_create.mkdir()
    zip_out = engine.execute(job=job_create, workspace_dir=ws_create)
    assert zip_out.exists()
    assert zip_out.suffix == ".zip"

    # 2. Inspect ZIP
    info = engine.inspect_archive(zip_out)
    assert info.is_valid
    assert info.format == "zip"
    assert len(info.entries) == 2

    # 3. Extract ZIP
    job_extract = ConversionJob(
        source_path=zip_out,
        target_format="dir",
        operation_id="archive.extract_zip",
        engine="archive"
    )
    ws_extract = tmp_path / "ws_extract"
    ws_extract.mkdir()
    extracted_dir = engine.execute(job=job_extract, workspace_dir=ws_extract)
    assert extracted_dir.is_dir()
    assert (extracted_dir / "hello.txt").read_text(encoding="utf-8") == "OmniConvert Archive Test"
    assert (extracted_dir / "nested" / "data.json").exists()


def test_tar_gz_and_7z_workflows(tmp_path):
    """Verify TAR.GZ and 7Z archive creation and extraction."""
    sample_file = tmp_path / "notes.txt"
    sample_file.write_text("Sample content for TAR and 7Z compression.", encoding="utf-8")

    engine = ArchiveEngine()

    # TAR.GZ
    ws1 = tmp_path / "ws1"
    ws1.mkdir()
    tar_path = engine.create_tar(sample_file, ws1 / "notes.tar.gz", gzip_compress=True)
    assert tar_path.exists()

    ext_tar = ws1 / "ext_tar"
    engine.extract_safely(tar_path, ext_tar)
    assert (ext_tar / "notes.txt").read_text(encoding="utf-8") == "Sample content for TAR and 7Z compression."

    # 7Z
    ws2 = tmp_path / "ws2"
    ws2.mkdir()
    sz_path = engine.create_7z(sample_file, ws2 / "notes.7z")
    assert sz_path.exists()

    ext_7z = ws2 / "ext_7z"
    engine.extract_safely(sz_path, ext_7z)
    assert (ext_7z / "notes.txt").read_text(encoding="utf-8") == "Sample content for TAR and 7Z compression."


def test_malicious_zip_slip_blocked(tmp_path):
    """Verify malicious ZIP archive with '../' traversal is blocked before writing outside target."""
    malicious_zip = tmp_path / "evil.zip"
    with zipfile.ZipFile(malicious_zip, "w") as zf:
        zf.writestr("../../escaped_pwned.txt", "malicious payload")

    engine = ArchiveEngine()
    inspection = engine.inspect_archive(malicious_zip)
    assert not inspection.is_valid
    assert inspection.has_suspicious_paths

    ws = tmp_path / "ws_evil"
    ws.mkdir()
    job = ConversionJob(
        source_path=malicious_zip,
        target_format="dir",
        operation_id="archive.extract_zip",
        engine="archive"
    )
    with pytest.raises(ValueError, match="Unsafe archive entries"):
        engine.execute(job=job, workspace_dir=ws)

    assert not (tmp_path / "escaped_pwned.txt").exists()


def test_archive_size_limit_safeguard(tmp_path):
    """Verify archive exceeding max_uncompressed_bytes limit is rejected."""
    big_zip = tmp_path / "oversized.zip"
    with zipfile.ZipFile(big_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.bin", b"A" * 50000)

    engine = ArchiveEngine()
    ws = tmp_path / "ws_limit"
    ws.mkdir()
    job = ConversionJob(
        source_path=big_zip,
        target_format="dir",
        operation_id="archive.extract_zip",
        engine="archive",
        settings={"max_uncompressed_bytes": 1000}
    )
    with pytest.raises(ValueError, match="exceeds safety limit"):
        engine.execute(job=job, workspace_dir=ws)
