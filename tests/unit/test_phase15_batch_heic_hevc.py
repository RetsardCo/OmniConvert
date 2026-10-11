import pytest
from pathlib import Path
from PIL import Image
import pypdf

from omniconvert.core.file_detector import inspect_file
from omniconvert.core.registry import CapabilityRegistry
from omniconvert.engines.pdf_engine import PDFEngine
from omniconvert.engines.image_engine import ImageEngine
from omniconvert.models.conversion_job import ConversionJob, JobState
from omniconvert.core.job_manager import JobManager
from omniconvert.ui.conversion_workspace import ConversionWorkspaceView
from omniconvert.ui.queue_view import QueueManagerView


def test_heic_and_hevc_detection(tmp_path: Path):
    registry = CapabilityRegistry()
    
    # 1. HEIC file detection
    heic_dummy = tmp_path / "sample.heic"
    heic_dummy.write_bytes(b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heicmif1")
    meta_heic = inspect_file(heic_dummy)
    assert meta_heic.detected_format == "heic"
    assert meta_heic.category == "image"

    # Capability check for HEIC
    heic_ops = registry.find_operations_for_file(meta_heic)
    assert any(op.output_format == "png" for op in heic_ops)
    assert any(op.output_format == "jpeg" for op in heic_ops)
    assert any(op.output_format == "pdf" for op in heic_ops)

    # 2. HEVC video detection
    hevc_dummy = tmp_path / "sample.hevc"
    hevc_dummy.write_bytes(b"\x00\x00\x00\x01\x40\x01\x0c\x01\xff")
    meta_hevc = inspect_file(hevc_dummy)
    assert meta_hevc.detected_format == "hevc"
    assert meta_hevc.category == "video"

    hevc_ops = registry.find_operations_for_file(meta_hevc)
    assert any(op.output_format == "mp4" for op in hevc_ops)


def test_batch_images_to_pdf(tmp_path: Path):
    # Create 3 distinct color test images
    img1_path = tmp_path / "page1.png"
    img2_path = tmp_path / "page2.png"
    img3_path = tmp_path / "page3.png"

    Image.new("RGB", (60, 60), color="red").save(img1_path)
    Image.new("RGBA", (60, 60), color="green").save(img2_path)
    Image.new("RGB", (80, 80), color="blue").save(img3_path)

    pdf_engine = PDFEngine()
    out_pdf = tmp_path / "multipage.pdf"

    result = pdf_engine.images_to_pdf([img1_path, img2_path, img3_path], out_pdf)
    assert result.exists()
    assert result == out_pdf

    # Check pages count via pypdf
    reader = pypdf.PdfReader(str(out_pdf))
    assert len(reader.pages) == 3


def test_batch_images_to_gif(tmp_path: Path):
    img1_path = tmp_path / "frame1.png"
    img2_path = tmp_path / "frame2.png"
    img3_path = tmp_path / "frame3.png"

    Image.new("RGBA", (50, 50), color="yellow").save(img1_path)
    Image.new("RGBA", (50, 50), color="purple").save(img2_path)
    Image.new("RGBA", (50, 50), color="cyan").save(img3_path)

    img_engine = ImageEngine()
    out_gif = tmp_path / "animated.gif"

    result = img_engine.images_to_gif(
        [img1_path, img2_path, img3_path],
        out_gif,
        settings={"fps": 4, "loop": 0}
    )
    assert result.exists()
    assert result == out_gif

    with Image.open(out_gif) as gif:
        assert getattr(gif, "is_animated", False)
        assert gif.n_frames == 3


def test_workspace_remove_selected_file(tmp_path: Path):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    f1 = tmp_path / "file1.png"
    f2 = tmp_path / "file2.jpg"
    f3 = tmp_path / "file3.txt"
    f1.write_bytes(b"data1")
    f2.write_bytes(b"data2")
    f3.write_bytes(b"data3")

    view = ConversionWorkspaceView()
    view.add_files([f1, f2, f3])
    assert view.file_list.count() == 3
    assert len(view.files_meta) == 3

    # Select the middle file (row 1: file2.jpg)
    view.file_list.setCurrentRow(1)
    view.remove_selected_files()

    assert view.file_list.count() == 2
    assert len(view.files_meta) == 2
    assert view.files_meta[0].path == f1
    assert view.files_meta[1].path == f3

    # Remove all remaining
    view.clear_files()
    assert view.file_list.count() == 0
    assert len(view.files_meta) == 0


def test_queue_view_clear_buttons(tmp_path: Path):
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    job_mgr = JobManager(max_concurrent=1)
    queue_view = QueueManagerView(job_mgr)

    # Create dummy jobs
    job1 = ConversionJob(source_path=tmp_path / "a.png", target_format="jpg")
    job1.state = JobState.COMPLETED
    job2 = ConversionJob(source_path=tmp_path / "b.png", target_format="png")
    job2.state = JobState.FAILED
    job3 = ConversionJob(source_path=tmp_path / "c.png", target_format="pdf")
    job3.state = JobState.RUNNING

    queue_view.add_job_card(job1)
    queue_view.add_job_card(job2)
    queue_view.add_job_card(job3)
    assert len(queue_view.cards) == 3

    # Clear finished should remove job1 (completed) and job2 (failed), leaving job3 (running)
    queue_view.clear_finished_jobs()
    assert len(queue_view.cards) == 1
    assert job3.id in queue_view.cards

    # Clear all should cancel running job and empty cards (mocking QMessageBox.question to Yes)
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes):
        queue_view.clear_all_jobs()
    assert len(queue_view.cards) == 0
    assert not queue_view.empty_lbl.isHidden()

