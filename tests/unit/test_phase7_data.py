"""Unit and integration tests for Phase 7: Structured Data and Text."""

import pytest
import json
import yaml
import time
from pathlib import Path
from PySide6.QtCore import QCoreApplication

from omniconvert.engines.data_engine import DataEngine
from omniconvert.models.conversion_job import ConversionJob, JobState
from omniconvert.core.job_manager import JobManager

@pytest.fixture
def sample_data(tmp_path):
    d = tmp_path / "data_fixtures"
    d.mkdir()

    # JSON with nested dictionary
    json_path = d / "config.json"
    json_path.write_text(json.dumps({
        "app": "OmniConvert",
        "settings": {"theme": "dark", "threads": 4},
        "tags": ["desktop", "windows", "conversion"]
    }, indent=2), encoding="utf-8")

    # CSV
    csv_path = d / "users.csv"
    csv_path.write_text("id,name,role\n101,John Doe,Admin\n102,Jane Smith,User\n", encoding="utf-8")

    # XML
    xml_path = d / "data.xml"
    xml_path.write_text('<?xml version="1.0"?><catalog><item id="1"><name>Widget</name><price>19.99</price></item></catalog>', encoding="utf-8")

    return {
        "json": json_path,
        "csv": csv_path,
        "xml": xml_path
    }

def test_json_to_yaml(sample_data, tmp_path):
    """Verify JSON converts cleanly to valid YAML."""
    engine = DataEngine()
    job = ConversionJob(
        source_path=sample_data["json"],
        target_format="yaml",
        operation_id="data.json_to_yaml",
        engine="data"
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".yaml"

    parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert parsed["app"] == "OmniConvert"
    assert parsed["settings"]["threads"] == 4

def test_yaml_to_json(tmp_path):
    """Verify YAML parses and serializes to valid JSON."""
    yaml_file = tmp_path / "input.yaml"
    yaml_file.write_text("server:\n  host: 127.0.0.1\n  port: 8080\nenabled: true\n", encoding="utf-8")

    engine = DataEngine()
    job = ConversionJob(
        source_path=yaml_file,
        target_format="json",
        operation_id="data.yaml_to_json",
        engine="data"
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".json"

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["server"]["port"] == 8080
    assert data["enabled"] is True

def test_xml_to_json_and_json_to_xml(sample_data, tmp_path):
    """Verify XML parses safely using defusedxml into JSON, and back to XML."""
    engine = DataEngine()

    # XML -> JSON
    job1 = ConversionJob(
        source_path=sample_data["xml"],
        target_format="json",
        operation_id="data.xml_to_json",
        engine="data"
    )
    json_out = engine.execute(job=job1, workspace_dir=tmp_path)
    assert json_out.exists()
    assert json_out.suffix == ".json"

    parsed_json = json.loads(json_out.read_text(encoding="utf-8"))
    assert "catalog" in parsed_json

    # JSON -> XML
    job2 = ConversionJob(
        source_path=json_out,
        target_format="xml",
        operation_id="data.json_to_xml",
        engine="data"
    )
    xml_out = engine.execute(job=job2, workspace_dir=tmp_path)
    assert xml_out.exists()
    assert xml_out.suffix == ".xml"
    assert "<root>" in xml_out.read_text(encoding="utf-8")

def test_line_ending_conversions(tmp_path):
    """Verify line endings conversion between Unix LF and Windows CRLF."""
    test_file = tmp_path / "mixed.txt"
    test_file.write_bytes(b"line 1\nline 2\r\nline 3\n")

    engine = DataEngine()

    # Convert to CRLF
    job_crlf = ConversionJob(
        source_path=test_file,
        target_format="txt",
        operation_id="text.to_crlf",
        engine="data"
    )
    out_crlf = engine.execute(job=job_crlf, workspace_dir=tmp_path)
    crlf_bytes = out_crlf.read_bytes()
    assert b"\r\n" in crlf_bytes
    assert crlf_bytes.count(b"\r\n") == 3

    # Convert to LF
    job_lf = ConversionJob(
        source_path=out_crlf,
        target_format="txt",
        operation_id="text.to_lf",
        engine="data"
    )
    out_lf = engine.execute(job=job_lf, workspace_dir=tmp_path)
    lf_bytes = out_lf.read_bytes()
    assert b"\r\n" not in lf_bytes
    assert lf_bytes.count(b"\n") == 3

def test_job_manager_data_yaml_execution(sample_data, tmp_path):
    """Verify end-to-end background conversion of JSON to YAML through JobManager."""
    app = QCoreApplication.instance() or QCoreApplication([])

    jm = JobManager(max_concurrent=2)
    job = ConversionJob(
        source_path=sample_data["json"],
        target_format="yaml",
        operation_id="data.json_to_yaml",
        engine="data",
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
    assert dest_path.suffix == ".yaml"
    assert job.state == JobState.COMPLETED
