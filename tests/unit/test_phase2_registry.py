"""Unit tests for Phase 2: File detection, Capability Registry, and Job collision."""

import pytest
from pathlib import Path
from omniconvert.core.file_detector import inspect_file, FileMetadata
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.models.capability import Capability
from omniconvert.models.conversion_job import resolve_output_collision, JobState, ConversionJob

def test_file_detector_missing_file():
    """Verify non-existent files are handled safely without throwing."""
    meta = inspect_file("C:/does_not_exist/random_file.unknown")
    assert not meta.is_readable
    assert meta.is_empty
    assert "does not exist" in meta.error

def test_file_detector_empty_file(tmp_path):
    """Verify 0-byte files are detected correctly."""
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")
    meta = inspect_file(empty_file)
    assert meta.is_empty
    assert meta.is_readable
    assert meta.category == "empty"
    assert meta.size_bytes == 0

def test_file_detector_png_signature(tmp_path):
    """Verify PNG magic byte header detection even if extension is missing/wrong."""
    fake_png = tmp_path / "sample.dat"
    # PNG signature: 89 50 4E 47 0D 0A 1A 0A
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
    meta = inspect_file(fake_png)
    assert meta.detected_format == "png"
    assert meta.category == "image"
    assert meta.detected_mime == "image/png"
    assert meta.is_readable

def test_file_detector_wav_riff_signature(tmp_path):
    """Verify RIFF WAVE container recognition."""
    fake_wav = tmp_path / "sound.dat"
    fake_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 20)
    meta = inspect_file(fake_wav)
    assert meta.detected_format == "wav"
    assert meta.category == "audio"
    assert meta.detected_mime == "audio/wav"

def test_file_detector_pdf_signature(tmp_path):
    """Verify PDF signature recognition."""
    fake_pdf = tmp_path / "doc.unknown"
    fake_pdf.write_bytes(b"%PDF-1.7\n%test pdf content")
    meta = inspect_file(fake_pdf)
    assert meta.detected_format == "pdf"
    assert meta.category == "document"
    assert meta.detected_mime == "application/pdf"

def test_capability_registry_filtering(tmp_path):
    """Verify operations are matched by file format and filtered by engine availability."""
    reg = CapabilityRegistry()

    # Image file matching Pillow capabilities
    fake_png = tmp_path / "photo.png"
    fake_png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    meta_png = inspect_file(fake_png)

    ops = reg.find_operations_for_file(meta_png, only_available=True)
    op_ids = [op.id for op in ops]
    assert "image.to_jpeg" in op_ids
    assert "image.to_webp" in op_ids

    # Video file matching FFmpeg (available or unavailable based on system)
    fake_mp4 = tmp_path / "video.mp4"
    fake_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 16)
    meta_mp4 = inspect_file(fake_mp4)

    all_video_ops = reg.find_operations_for_file(meta_mp4, only_available=False)
    assert any(op.id == "video.extract_mp3" for op in all_video_ops)

def test_output_collision_resolution(tmp_path):
    """Verify safe collision handling without overwriting existing files."""
    existing_file = tmp_path / "report.pdf"
    existing_file.write_text("v1")

    # Policy rename
    new_path = resolve_output_collision(tmp_path, "report", "pdf", policy="rename")
    assert new_path.name == "report (1).pdf"
    assert not new_path.exists()

    # Create collision 1 and test collision 2
    new_path.write_text("v2")
    next_path = resolve_output_collision(tmp_path, "report", "pdf", policy="rename")
    assert next_path.name == "report (2).pdf"

    # Policy overwrite returns existing file directly
    overwrite_path = resolve_output_collision(tmp_path, "report", "pdf", policy="overwrite")
    assert overwrite_path == existing_file
