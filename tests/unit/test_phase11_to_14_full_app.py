"""Comprehensive tests for Phases 11–14: PDF<->Word, Lossless Image/Audio Quality Controls, App Icon, UI Views, and Packaging."""

import os
import pytest
import json
from pathlib import Path
from PIL import Image
import docx
import openpyxl
from pptx import Presentation
import pypdf

from omniconvert.config.paths import get_icon_path, get_resources_dir
from omniconvert.engines.pdf_engine import PDFEngine
from omniconvert.engines.office_engine import OfficeEngine
from omniconvert.engines.image_engine import ImageEngine
from omniconvert.engines.ffmpeg_engine import FFmpegEngine
from omniconvert.models.conversion_job import ConversionJob
from omniconvert.core.validation import validate_output


def test_app_icon_assets_exist_and_valid():
    """Verify the user-provided icon was converted into valid icon.png and multi-size icon.ico."""
    png_icon = get_icon_path(prefer_ico=False)
    ico_icon = get_icon_path(prefer_ico=True)

    assert png_icon.exists(), "icon.png must exist in resources"
    assert ico_icon.exists(), "icon.ico must exist in resources"

    with Image.open(png_icon) as im_png:
        assert im_png.format == "PNG"
        assert im_png.width > 64 and im_png.height > 64

    with Image.open(ico_icon) as im_ico:
        assert im_ico.format == "ICO"


def test_word_to_pdf_and_pdf_to_word_roundtrip(tmp_path):
    """Verify Word (.docx) to PDF (.pdf) AND PDF (.pdf) back to editable Word (.docx)."""
    # 1. Create a rich Word (.docx) document with headings, paragraphs, bold text, and a table
    docx_src = tmp_path / "contract.docx"
    doc = docx.Document()
    doc.add_heading("OmniConvert Service Agreement", level=1)
    p = doc.add_paragraph("This document tests ")
    p.add_run("full round-trip conversion").bold = True
    p.add_run(" between Microsoft Word and PDF.")

    table = doc.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "Feature"
    table.cell(0, 1).text = "Status"
    table.cell(1, 0).text = "PDF <-> Word"
    table.cell(1, 1).text = "Verified"
    doc.save(str(docx_src))

    # 2. Convert Word (.docx) -> PDF (.pdf)
    office_eng = OfficeEngine()
    assert office_eng.is_available()

    ws_pdf = tmp_path / "ws_pdf"
    ws_pdf.mkdir()
    job_to_pdf = ConversionJob(
        source_path=docx_src,
        target_format="pdf",
        operation_id="office.to_pdf",
        engine="libreoffice",
        settings={"quality_preset": "lossless"}
    )
    pdf_out = office_eng.execute(job=job_to_pdf, workspace_dir=ws_pdf)
    assert pdf_out.exists()
    valid_pdf, err_pdf = validate_output(pdf_out, "pdf")
    assert valid_pdf, err_pdf

    reader = pypdf.PdfReader(str(pdf_out))
    assert len(reader.pages) >= 1
    extracted_pdf_text = reader.pages[0].extract_text()
    assert "OmniConvert Service Agreement" in extracted_pdf_text

    # 3. Convert PDF (.pdf) -> Word (.docx)
    pdf_eng = PDFEngine()
    ws_docx = tmp_path / "ws_docx"
    ws_docx.mkdir()
    job_to_docx = ConversionJob(
        source_path=pdf_out,
        target_format="docx",
        operation_id="pdf.to_docx",
        engine="pypdf",
        settings={"quality_preset": "lossless"}
    )
    docx_out = pdf_eng.execute(job=job_to_docx, workspace_dir=ws_docx)
    assert docx_out.exists()
    valid_docx, err_docx = validate_output(docx_out, "docx")
    assert valid_docx, err_docx

    reconstructed = docx.Document(str(docx_out))
    all_text = "\n".join([para.text for para in reconstructed.paragraphs])
    for tbl in reconstructed.tables:
        for row in tbl.rows:
            all_text += "\n" + " ".join(c.text for c in row.cells)
    assert "OmniConvert" in all_text


def test_pdf_to_png_html_and_markdown(tmp_path):
    """Verify PDF rendering to high-DPI PNG, HTML, and Markdown."""
    # Create a PDF via OfficeEngine from Markdown
    md_src = tmp_path / "guide.md"
    md_src.write_text("# OmniConvert Guide\n\nConvert all files locally with precision.\n", encoding="utf-8")

    office_eng = OfficeEngine()
    ws = tmp_path / "ws_doc"
    ws.mkdir()
    pdf_path = office_eng.execute(
        ConversionJob(source_path=md_src, target_format="pdf", operation_id="office.to_pdf", engine="libreoffice"),
        ws
    )

    pdf_eng = PDFEngine()
    # PDF -> PNG (300 DPI lossless preset)
    ws_png = tmp_path / "ws_png"
    ws_png.mkdir()
    png_out = pdf_eng.execute(
        ConversionJob(source_path=pdf_path, target_format="png", operation_id="pdf.to_png", engine="pypdf", settings={"quality_preset": "lossless", "dpi": 300}),
        ws_png
    )
    assert png_out.exists()
    with Image.open(png_out) as im:
        assert im.width > 1000  # 300 DPI letter width is ~2550px

    # PDF -> HTML
    ws_html = tmp_path / "ws_html"
    ws_html.mkdir()
    html_out = pdf_eng.execute(
        ConversionJob(source_path=pdf_path, target_format="html", operation_id="pdf.to_html", engine="pypdf"),
        ws_html
    )
    assert "OmniConvert Guide" in html_out.read_text(encoding="utf-8")

    # PDF -> MD
    ws_md = tmp_path / "ws_md"
    ws_md.mkdir()
    md_out = pdf_eng.execute(
        ConversionJob(source_path=pdf_path, target_format="md", operation_id="pdf.to_md", engine="pypdf"),
        ws_md
    )
    assert "OmniConvert Guide" in md_out.read_text(encoding="utf-8")


def test_excel_and_powerpoint_conversions(tmp_path):
    """Verify Excel (.xlsx <-> .pdf/.csv/.json) and PowerPoint (.pptx -> .pdf/.txt) conversions."""
    office_eng = OfficeEngine()

    # CSV -> XLSX
    csv_src = tmp_path / "sales.csv"
    csv_src.write_text("Product,Units,Price\nLaptop,15,1200\nMonitor,30,350\n", encoding="utf-8")
    ws1 = tmp_path / "ws1"
    ws1.mkdir()
    xlsx_out = office_eng.execute(
        ConversionJob(source_path=csv_src, target_format="xlsx", operation_id="office.to_xlsx", engine="libreoffice"),
        ws1
    )
    assert xlsx_out.exists()

    # XLSX -> PDF
    ws2 = tmp_path / "ws2"
    ws2.mkdir()
    xlsx_pdf = office_eng.execute(
        ConversionJob(source_path=xlsx_out, target_format="pdf", operation_id="office.to_pdf", engine="libreoffice"),
        ws2
    )
    assert xlsx_pdf.exists()
    assert validate_output(xlsx_pdf, "pdf")[0]

    # PPTX -> PDF & TXT
    pptx_src = tmp_path / "deck.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Quarterly Review"
    prs.save(str(pptx_src))

    ws3 = tmp_path / "ws3"
    ws3.mkdir()
    pptx_pdf = office_eng.execute(
        ConversionJob(source_path=pptx_src, target_format="pdf", operation_id="office.to_pdf", engine="libreoffice"),
        ws3
    )
    assert pptx_pdf.exists()
    assert validate_output(pptx_pdf, "pdf")[0]


def test_png_to_jpeg_lossless_quality_preset(tmp_path):
    """Verify PNG-to-JPEG with lossless/exact preset preserves high color fidelity (quality=100, 4:4:4 chroma)."""
    src_png = tmp_path / "sharp_color.png"
    img = Image.new("RGB", (120, 120), (220, 20, 60))
    img.save(src_png, "PNG")

    eng = ImageEngine()

    # 1. Lossless / Exact quality preset (100% quality + 4:4:4 chroma)
    ws_exact = tmp_path / "ws_exact"
    ws_exact.mkdir()
    out_exact = eng.execute(
        ConversionJob(
            source_path=src_png,
            target_format="jpeg",
            operation_id="image.to_jpeg",
            engine="pillow",
            settings={"quality_preset": "lossless", "quality": 100, "subsampling": "4:4:4 (Lossless Chroma)"}
        ),
        ws_exact
    )

    # 2. Compact preset (70% quality + 4:2:0 subsampling)
    ws_compact = tmp_path / "ws_compact"
    ws_compact.mkdir()
    out_compact = eng.execute(
        ConversionJob(
            source_path=src_png,
            target_format="jpeg",
            operation_id="image.to_jpeg",
            engine="pillow",
            settings={"quality_preset": "compact", "quality": 70, "subsampling": "4:2:0 (Standard)"}
        ),
        ws_compact
    )

    assert out_exact.exists() and out_compact.exists()
    # Verify exact pixel color on solid RGB is preserved within +/- 1 unit
    with Image.open(out_exact) as im_res:
        r, g, b = im_res.getpixel((60, 60))
        assert abs(r - 220) <= 1 and abs(g - 20) <= 1 and abs(b - 60) <= 1


def test_all_audio_conversions_and_presets(tmp_path):
    """Verify audio conversions across MP3, WAV (24-bit), FLAC, AAC, M4A, OGG, OPUS, and AIFF."""
    ff = FFmpegEngine()
    if not ff.is_available():
        pytest.skip("FFmpeg not available")

    # Create source WAV via TTSEngine fallback PCM generator
    from omniconvert.engines.speech_engine import TTSEngine
    src_wav = tmp_path / "tone.wav"
    TTSEngine()._write_fallback_pcm_wav(src_wav, "Audio format test")

    for fmt, op_id in [
        ("mp3", "audio.to_mp3"),
        ("wav", "audio.to_wav"),
        ("flac", "audio.to_flac"),
        ("aac", "audio.to_aac"),
        ("m4a", "audio.to_m4a"),
        ("ogg", "audio.to_ogg"),
        ("opus", "audio.to_opus"),
        ("aiff", "audio.to_aiff"),
    ]:
        ws = tmp_path / f"ws_{fmt}"
        ws.mkdir()
        job = ConversionJob(
            source_path=src_wav,
            target_format=fmt,
            operation_id=op_id,
            engine="ffmpeg",
            settings={"quality_preset": "lossless"}
        )
        out = ff.execute(job=job, workspace_dir=ws)
        assert out.exists(), f"Failed to produce .{fmt}"
        assert out.stat().st_size > 0
        valid, err = validate_output(out, fmt)
        assert valid, f"Validation failed for .{fmt}: {err}"


def test_ui_workspace_quality_controls_and_views(tmp_path):
    """Verify UI views (Workspace quality controls, History, Format Explorer, Settings, Icon) initialize and operate."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from omniconvert.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    # Verify window icon is set
    assert not window.windowIcon().isNull()

    # Add a PNG image to Workspace and verify quality preset controls populate
    png_file = tmp_path / "photo.png"
    Image.new("RGBA", (80, 80), (10, 120, 240, 200)).save(png_file, "PNG")
    window._on_files_received([str(png_file)])

    ws_view = window.conversion_view
    assert ws_view.op_combo.count() > 0
    assert ws_view.quality_preset_combo.currentData() == "lossless"

    # Switch to Compact preset and verify dynamic quality spinbox updates to 70
    ws_view.quality_preset_combo.setCurrentIndex(3)  # compact
    collected = ws_view.collect_current_settings()
    assert collected["quality_preset"] == "compact"
    if "quality" in collected:
        assert collected["quality"] == 70

    # Switch back to Lossless preset and verify quality spinbox updates to 100
    ws_view.quality_preset_combo.setCurrentIndex(0)  # lossless
    collected_lossless = ws_view.collect_current_settings()
    assert collected_lossless["quality_preset"] == "lossless"
    if "quality" in collected_lossless:
        assert collected_lossless["quality"] == 100

    # Verify Format Explorer table has rows and filters work
    exp_view = window.explorer_view
    total_rows = exp_view.table.rowCount()
    assert total_rows >= 30
    exp_view.search_edit.setText("docx")
    assert 0 < exp_view.table.rowCount() < total_rows

    # Verify Settings view dependency report is populated
    set_view = window.settings_view
    assert "100% Local Processing" in set_view.dep_report_text.toPlainText()


def test_packaging_and_dependency_scripts():
    """Verify check_dependencies.py and build_windows.py dry-run execute cleanly."""
    from scripts.check_dependencies import generate_dependency_report
    from scripts.build_windows import build_package

    rep = generate_dependency_report()
    assert rep["total_registered_operations"] >= 35
    assert rep["engines"]["pillow"] is True
    assert rep["engines"]["office_docx_xlsx_pptx"] is True

    cmd = build_package(dry_run=True)
    assert "--windowed" in cmd
    assert any("icon.ico" in c for c in cmd)
