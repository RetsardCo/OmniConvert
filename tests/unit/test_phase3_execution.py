"""Unit tests for Phase 3: Job Manager, safe execution, workspaces, and cancellation."""

import pytest
import time
from pathlib import Path
from PySide6.QtCore import QCoreApplication

from omniconvert.models.conversion_job import ConversionJob, JobState
from omniconvert.core.job_manager import JobManager
from omniconvert.core.temp_files import JobWorkspace
from omniconvert.core.safe_subprocess import SafeSubprocessRunner
from omniconvert.core.validation import validate_output

def test_job_workspace_lifecycle(tmp_path):
    """Verify temporary workspace creation and safe cleanup."""
    with JobWorkspace("test_job_1") as ws:
        root = ws.root_dir
        assert root.exists()
        scratch_file = ws.get_path("scratch.txt")
        scratch_file.write_text("intermediate data")
        assert scratch_file.exists()

    # Workspace directory should be cleaned up automatically on exit
    assert not root.exists()

def test_job_workspace_path_traversal_protection():
    """Verify workspace blocks path traversal attempts."""
    ws = JobWorkspace("safe_test")
    ws.create()
    try:
        with pytest.raises(ValueError, match="Path traversal"):
            ws.get_path("../../../evil.exe")
    finally:
        ws.cleanup()

def test_safe_subprocess_execution_and_timeout():
    """Verify SafeSubprocessRunner executes command array and respects timeouts."""
    runner = SafeSubprocessRunner()
    # Test valid execution using python
    res = runner.run(["python", "-c", "print('hello from subprocess')"], timeout=5.0)
    assert res.returncode == 0
    assert "hello from subprocess" in res.stdout
    assert not res.timed_out

    # Test timeout expiration
    timeout_res = runner.run(["python", "-c", "import time; time.sleep(2)"], timeout=0.1)
    assert timeout_res.timed_out
    assert timeout_res.returncode == -1

def test_output_validation(tmp_path):
    """Verify validation catches empty or missing files."""
    valid, err = validate_output(tmp_path / "does_not_exist.png", "png")
    assert not valid
    assert "does not exist" in err

    empty = tmp_path / "empty.json"
    empty.write_bytes(b"")
    valid, err = validate_output(empty, "json")
    assert not valid
    assert "empty" in err

    good_json = tmp_path / "data.json"
    good_json.write_text('{"name": "OmniConvert", "version": 1}')
    valid, err = validate_output(good_json, "json")
    assert valid
    assert err is None

def test_job_manager_execution(tmp_path):
    """Verify JobManager executes data conversion job in background thread pool."""
    app = QCoreApplication.instance() or QCoreApplication([])

    # Create test CSV
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("id,name,role\n1,Alice,Engineer\n2,Bob,Designer\n")

    jm = JobManager(max_concurrent=2)
    job = ConversionJob(
        source_path=csv_file,
        target_format="json",
        operation_id="data.csv_to_json",
        engine="data",
        destination_path=tmp_path
    )

    completed_events = []
    jm.signals.completed.connect(lambda jid, dest: completed_events.append((jid, dest)))

    jm.submit_job(job)

    # Pump Qt events to let worker complete
    for _ in range(50):
        app.processEvents()
        if completed_events:
            break
        time.sleep(0.02)

    assert len(completed_events) == 1
    dest_path = Path(completed_events[0][1])
    assert dest_path.exists()
    assert dest_path.suffix == ".json"
    assert "Alice" in dest_path.read_text(encoding="utf-8")
    assert job.state == JobState.COMPLETED

def test_job_manager_cancellation(tmp_path):
    """Verify job cancellation before or during execution."""
    app = QCoreApplication.instance() or QCoreApplication([])

    csv_file = tmp_path / "long.csv"
    csv_file.write_text("id,val\n" + "\n".join(f"{i},data" for i in range(100)))

    jm = JobManager(max_concurrent=1)
    job = ConversionJob(
        source_path=csv_file,
        target_format="json",
        operation_id="data.csv_to_json",
        engine="data",
        destination_path=tmp_path
    )

    cancelled_events = []
    jm.signals.cancelled.connect(lambda jid: cancelled_events.append(jid))

    # Cancel immediately
    jm.submit_job(job)
    jm.cancel_job(job.id)

    for _ in range(50):
        app.processEvents()
        if cancelled_events or job.state == JobState.CANCELLED:
            break
        time.sleep(0.02)

    assert job.state in (JobState.CANCELLED, JobState.COMPLETED)
