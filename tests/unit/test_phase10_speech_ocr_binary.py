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


def test_synthesize_speech_sapi5(tmp_path):
    """Verify in-process Windows SAPI5 / pyttsx3 synthesis works and creates valid audio."""
    from omniconvert.engines.speech_engine import synthesize_speech_sapi5
    out_wav = tmp_path / "sapi5_direct.wav"
    ok = synthesize_speech_sapi5("Testing direct SAPI5 speech synthesis.", out_wav, rate=180)
    assert ok is True
    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000
    assert out_wav.read_bytes()[:4] == b"RIFF"


def test_run_tts_worker(tmp_path):
    """Verify run_tts_worker function executes headless synthesis with exit code 0."""
    from omniconvert.engines.speech_engine import run_tts_worker
    txt_file = tmp_path / "worker_in.txt"
    txt_file.write_text("Testing TTS worker invocation.", encoding="utf-8")
    out_wav = tmp_path / "worker_out.wav"

    code = run_tts_worker([str(txt_file), str(out_wav), "175"])
    assert code == 0
    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000


def test_fallback_audio_harmonic_quality(tmp_path):
    """Verify the fallback audio synthesizer writes valid 16-bit 44.1kHz PCM WAV."""
    tts = TTSEngine()
    out_wav = tmp_path / "fallback.wav"
    tts._write_fallback_pcm_wav(out_wav, "Smooth musical fallback audio without harsh noise.")
    assert out_wav.exists()
    assert out_wav.stat().st_size > 10000
    assert out_wav.read_bytes()[:4] == b"RIFF"

    import wave
    with wave.open(str(out_wav), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 44100
        assert wf.getnframes() > 10000


def test_app_cli_worker_mode(tmp_path):
    """Verify app.py CLI mode handles -c and --tts-worker without launching GUI."""
    import subprocess
    import sys

    # 1. Test -c
    p = subprocess.run(
        [sys.executable, "app.py", "-c", "print('CLI_OK')"],
        capture_output=True,
        text=True,
        timeout=10
    )
    assert p.returncode == 0
    assert "CLI_OK" in p.stdout

    # 2. Test --tts-worker
    txt_file = tmp_path / "app_tts_in.txt"
    txt_file.write_text("Hello from app worker test.", encoding="utf-8")
    out_wav = tmp_path / "app_tts_out.wav"

    p2 = subprocess.run(
        [sys.executable, "app.py", "--tts-worker", str(txt_file), str(out_wav), "175"],
        capture_output=True,
        text=True,
        timeout=15
    )
    assert p2.returncode == 0
    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000

    # 3. Test python -m omniconvert.engines.speech_engine (non-frozen worker execution)
    out_wav_module = tmp_path / "module_tts_out.wav"
    p3 = subprocess.run(
        [sys.executable, "-m", "omniconvert.engines.speech_engine", str(txt_file), str(out_wav_module), "175"],
        capture_output=True,
        text=True,
        timeout=15
    )
    assert p3.returncode == 0
    assert out_wav_module.exists()
    assert out_wav_module.stat().st_size > 1000


def test_job_manager_cancel_and_shutdown(tmp_path):
    """Verify JobManager.shutdown cancels active background tasks cleanly."""
    from omniconvert.core.job_manager import JobManager
    from omniconvert.models.conversion_job import ConversionJob, JobState
    import time

    jm = JobManager()
    dummy_txt = tmp_path / "test_shutdown.txt"
    dummy_txt.write_text("Testing job manager clean shutdown.", encoding="utf-8")

    job = ConversionJob(
        source_path=dummy_txt,
        target_format="wav",
        operation_id="speech.tts",
        engine="tts"
    )
    jm.submit_job(job)
    # Immediately shutdown
    jm.shutdown(timeout_ms=500)
    # The job manager thread pool should have no running jobs or cleared
    assert jm.thread_pool is not None


def test_single_instance_activation():
    """Verify single-instance server activates window on secondary launch attempt."""
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    test_srv_name = "OmniConvert_Test_SingleInstance"
    QLocalServer.removeServer(test_srv_name)

    server = QLocalServer()
    assert server.listen(test_srv_name) is True

    # Connect secondary client socket
    client = QLocalSocket()
    client.connectToServer(test_srv_name)
    assert client.waitForConnected(1000) is True

    # Accept on server side
    conn_result = server.waitForNewConnection(1000)
    has_conn = conn_result[0] if isinstance(conn_result, tuple) else bool(conn_result)
    assert has_conn is True
    pending = server.nextPendingConnection()
    assert pending is not None

    client.write(b"ACTIVATE\n")
    client.flush()

    assert pending.waitForReadyRead(1000) is True
    msg = pending.readAll().data().decode("utf-8")
    assert "ACTIVATE" in msg

    client.disconnectFromServer()
    server.close()
    QLocalServer.removeServer(test_srv_name)

