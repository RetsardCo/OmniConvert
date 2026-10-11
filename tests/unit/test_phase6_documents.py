"""Unit and integration tests for Phase 6: Documents and PDFs."""

import pytest
import json
import time
from pathlib import Path
import pypdf
from PIL import Image
from PySide6.QtCore import QCoreApplication

from omniconvert.engines.pdf_engine import PDFEngine
from omniconvert.engines.office_detector import LibreOfficeDetector
from omniconvert.models.conversion_job import ConversionJob, JobState
from omniconvert.core.job_manager import JobManager

@pytest.fixture
def sample_pdf(tmp_path):
    """Generate a clean synthetic 2-page PDF document with text."""
    pdf_path = tmp_path / "test_doc.pdf"
    writer = pypdf.PdfWriter()

    # Add 2 blank pages with text annotations or text
    p1 = writer.add_blank_page(width=300, height=400)
    p2 = writer.add_blank_page(width=300, height=400)

    # Note: blank pages in pypdf can be serialized and reopened
    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path

@pytest.fixture
def sample_image(tmp_path):
    """Generate a simple test image for PDF wrapping."""
    img_path = tmp_path / "chart.png"
    im = Image.new("RGB", (200, 200), (20, 140, 200))
    im.save(img_path, "PNG")
    return img_path

def test_office_detector():
    """Verify LibreOffice detection handles presence or absence safely."""
    detector = LibreOfficeDetector()
    info = detector.detect()
    assert isinstance(info.is_available, bool)
    if not info.is_available:
        assert info.error_message is not None

def test_image_to_pdf(sample_image, tmp_path):
    """Verify wrapping an image into a clean PDF."""
    engine = PDFEngine()
    job = ConversionJob(
        source_path=sample_image,
        target_format="pdf",
        operation_id="image.to_pdf",
        engine="pypdf"
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".pdf"

    # Verify produced PDF with pypdf
    reader = pypdf.PdfReader(str(output))
    assert len(reader.pages) == 1

def test_pdf_extract_text(sample_pdf, tmp_path):
    """Verify text extraction operation from PDF."""
    engine = PDFEngine()
    job = ConversionJob(
        source_path=sample_pdf,
        target_format="txt",
        operation_id="pdf.extract_text",
        engine="pypdf"
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".txt"

    content = output.read_text(encoding="utf-8")
    assert "Page 1" in content
    assert "Page 2" in content

def test_pdf_to_json_export(sample_pdf, tmp_path):
    """Verify structured PDF text and metadata export to JSON."""
    engine = PDFEngine()
    job = ConversionJob(
        source_path=sample_pdf,
        target_format="json",
        operation_id="pdf.to_json",
        engine="pypdf"
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".json"

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["filename"] == "test_doc.pdf"
    assert data["page_count"] == 2
    assert len(data["pages"]) == 2

def test_pdf_merger(sample_image, tmp_path):
    """Verify PDF merger utility."""
    engine = PDFEngine()
    # Create two PDFs
    pdf1 = tmp_path / "part1.pdf"
    pdf2 = tmp_path / "part2.pdf"

    w1 = pypdf.PdfWriter()
    w1.add_blank_page(width=100, height=100)
    with open(pdf1, "wb") as f:
        w1.write(f)

    w2 = pypdf.PdfWriter()
    w2.add_blank_page(width=100, height=100)
    with open(pdf2, "wb") as f:
        w2.write(f)

    merged = engine.merge_pdfs([pdf1, pdf2], tmp_path / "combined.pdf")
    assert merged.exists()

    reader = pypdf.PdfReader(str(merged))
    assert len(reader.pages) == 2

def test_job_manager_pdf_execution(sample_image, tmp_path):
    """Verify end-to-end background conversion of Image to PDF through JobManager."""
    app = QCoreApplication.instance() or QCoreApplication([])

    jm = JobManager(max_concurrent=2)
    job = ConversionJob(
        source_path=sample_image,
        target_format="pdf",
        operation_id="image.to_pdf",
        engine="pypdf",
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
    assert dest_path.suffix == ".pdf"
    assert job.state == JobState.COMPLETED
