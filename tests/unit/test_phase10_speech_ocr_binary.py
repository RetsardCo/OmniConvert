"""Unit and integration tests for Phase 10: Local TTS, Optional OCR/ASR, and Static Binary Inspection."""

import pytest
import json
from pathlib import Path

from omniconvert.engines.speech_engine import TTSEngine, ASREngine, SpeechDetector
from omniconvert.engines.ocr_engine import OCREngine, TesseractDetector
from omniconvert.engines.binary_engine import BinaryEngine
from omniconvert.models.conversion_job import ConversionJob


def test_local_tts_text_to_wav(tmp_path):
    """Verify local TTS converts a text file into a valid playable WAV file offline."""
    txt_file = tmp_path / "greeting.txt"
    txt_file.write_text("Hello from OmniConvert local text to speech synthesis.", encoding="utf-8")

    tts = TTSEngine()
    assert tts.is_available()

    ws = tmp_path / "ws_tts"
    ws.mkdir()
    job = ConversionJob(
        source_path=txt_file,
        target_format="wav",
        operation_id="speech.text_to_wav",
        engine="tts",
        settings={"rate": 180}
    )
    wav_out = tts.execute(job=job, workspace_dir=ws)
    assert wav_out.exists()
    assert wav_out.suffix == ".wav"
    assert wav_out.stat().st_size > 100
    assert wav_out.read_bytes()[:4] == b"RIFF"


def test_optional_ocr_and_asr_detection():
    """Verify OCR and ASR detectors report availability cleanly without crashing when missing."""
    ocr_det = TesseractDetector()
    ocr_info = ocr_det.detect()
    assert isinstance(ocr_info.is_available, bool)
    if not ocr_info.is_available:
        assert ocr_info.error_message is not None

    sp_det = SpeechDetector()
    sp_info = sp_det.detect()
    assert sp_info.tts_available is True
    assert isinstance(sp_info.asr_available, bool)


def test_binary_engine_strings_hashes_and_hexdump(tmp_path):
    """Verify static binary inspection extracts strings, hashes, entropy, and hex dump without executing."""
    fake_exe = tmp_path / "sample_app.exe"
    fake_exe.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00OmniConvertStaticBinaryStringTest\x00\x00" + b"\x41" * 128)

    engine = BinaryEngine()

    # 1. Extract printable strings
    ws1 = tmp_path / "ws_str"
    ws1.mkdir()
    job_str = ConversionJob(
        source_path=fake_exe,
        target_format="txt",
        operation_id="binary.extract_strings",
        engine="binary",
        settings={"min_length": 5}
    )
    str_out = engine.execute(job=job_str, workspace_dir=ws1)
    assert str_out.exists()
    assert "OmniConvertStaticBinaryStringTest" in str_out.read_text(encoding="utf-8")

    # 2. Inspect hashes & metadata to JSON
    ws2 = tmp_path / "ws_json"
    ws2.mkdir()
    job_json = ConversionJob(
        source_path=fake_exe,
        target_format="json",
        operation_id="binary.inspect_to_json",
        engine="binary"
    )
    json_out = engine.execute(job=job_json, workspace_dir=ws2)
    assert json_out.exists()
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["detected_format"] == "exe"
    assert len(report["hashes"]["sha256"]) == 64
    assert report["shannon_entropy_bits"] > 0

    # 3. Hex dump
    ws3 = tmp_path / "ws_hex"
    ws3.mkdir()
    job_hex = ConversionJob(
        source_path=fake_exe,
        target_format="txt",
        operation_id="binary.hex_dump",
        engine="binary"
    )
    hex_out = engine.execute(job=job_hex, workspace_dir=ws3)
    assert hex_out.exists()
    assert "4d 5a" in hex_out.read_text(encoding="utf-8")
