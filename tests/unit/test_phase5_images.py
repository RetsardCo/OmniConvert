"""Unit and integration tests for Phase 5: Image Engine (Pillow)."""

import pytest
import time
from pathlib import Path
from PIL import Image
from PySide6.QtCore import QCoreApplication

from omniconvert.engines.image_engine import ImageEngine
from omniconvert.models.conversion_job import ConversionJob, JobState
from omniconvert.core.job_manager import JobManager
from omniconvert.core.validation import validate_output

@pytest.fixture
def sample_images(tmp_path):
    """Generate sample test images: RGBA PNG with transparency, RGB JPEG, and multi-frame GIF."""
    img_dir = tmp_path / "img_fixtures"
    img_dir.mkdir()

    # 1. RGBA PNG with semi-transparent alpha channel
    rgba_png = img_dir / "transparent.png"
    im_rgba = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
    im_rgba.save(rgba_png, "PNG")

    # 2. RGB JPEG
    rgb_jpg = img_dir / "photo.jpg"
    im_rgb = Image.new("RGB", (200, 150), (0, 128, 255))
    im_rgb.save(rgb_jpg, "JPEG")

    # 3. Multi-frame GIF
    anim_gif = img_dir / "animation.gif"
    f1 = Image.new("RGB", (50, 50), (255, 0, 0))
    f2 = Image.new("RGB", (50, 50), (0, 255, 0))
    f1.save(anim_gif, "GIF", save_all=True, append_images=[f2], duration=100, loop=0)

    return {
        "rgba_png": rgba_png,
        "rgb_jpg": rgb_jpg,
        "anim_gif": anim_gif
    }

def test_png_to_jpeg_transparency_flattening(sample_images, tmp_path):
    """Verify PNG with transparency converts to JPEG with white background without error."""
    engine = ImageEngine()
    job = ConversionJob(
        source_path=sample_images["rgba_png"],
        target_format="jpeg",
        operation_id="image.to_jpeg",
        engine="pillow",
        settings={"quality": 90, "background_color": "#FFFFFF"}
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".jpeg"
    assert any("Transparency was flattened" in w for w in job.warnings)

    # Validate output image mode and size
    with Image.open(output) as res:
        assert res.format == "JPEG"
        assert res.mode == "RGB"
        assert res.size == (100, 100)

def test_jpeg_to_png(sample_images, tmp_path):
    """Verify JPEG converts cleanly to PNG."""
    engine = ImageEngine()
    job = ConversionJob(
        source_path=sample_images["rgb_jpg"],
        target_format="png",
        operation_id="image.to_png",
        engine="pillow"
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".png"

    with Image.open(output) as res:
        assert res.format == "PNG"
        assert res.size == (200, 150)

def test_webp_conversion(sample_images, tmp_path):
    """Verify conversion to WebP format."""
    engine = ImageEngine()
    job = ConversionJob(
        source_path=sample_images["rgb_jpg"],
        target_format="webp",
        operation_id="image.to_webp",
        engine="pillow",
        settings={"quality": 80}
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".webp"

    with Image.open(output) as res:
        assert res.format == "WEBP"

def test_image_resizing_and_rotation(sample_images, tmp_path):
    """Verify width/height resizing and rotation settings."""
    engine = ImageEngine()
    job = ConversionJob(
        source_path=sample_images["rgb_jpg"],
        target_format="png",
        operation_id="image.to_png",
        engine="pillow",
        settings={"width": 100, "height": 75, "rotate": 90}
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()

    with Image.open(output) as res:
        # Initial 200x150 resized to 100x75, then rotated 90 deg -> 75x100
        assert res.size == (75, 100)

def test_generate_ico(sample_images, tmp_path):
    """Verify multi-resolution Windows .ico generation."""
    engine = ImageEngine()
    job = ConversionJob(
        source_path=sample_images["rgba_png"],
        target_format="ico",
        operation_id="image.to_ico",
        engine="pillow"
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".ico"

    with Image.open(output) as res:
        assert res.format == "ICO"

def test_corrupt_image_fails_safely(tmp_path):
    """Verify corrupt image file raises clear error and fails validation."""
    corrupt = tmp_path / "bad.png"
    corrupt.write_bytes(b"\x89PNG\r\n\x1a\ncorrupt garbage bytes")

    engine = ImageEngine()
    job = ConversionJob(
        source_path=corrupt,
        target_format="jpeg",
        operation_id="image.to_jpeg",
        engine="pillow"
    )
    with pytest.raises(ValueError, match="Could not open source image"):
        engine.execute(job=job, workspace_dir=tmp_path)

def test_job_manager_image_execution(sample_images, tmp_path):
    """Verify end-to-end background conversion of PNG to WEBP through JobManager."""
    app = QCoreApplication.instance() or QCoreApplication([])

    jm = JobManager(max_concurrent=2)
    job = ConversionJob(
        source_path=sample_images["rgba_png"],
        target_format="webp",
        operation_id="image.to_webp",
        engine="pillow",
        destination_path=tmp_path
    )

    completed = []
    jm.signals.completed.connect(lambda jid, dest: completed.append((jid, dest)))
    jm.submit_job(job)

    for _ in range(50):
        app.processEvents()
        if completed:
            break
        time.sleep(0.02)

    assert len(completed) == 1
    dest_path = Path(completed[0][1])
    assert dest_path.exists()
    assert dest_path.suffix == ".webp"
    assert job.state == JobState.COMPLETED
