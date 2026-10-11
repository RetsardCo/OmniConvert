"""Unit and integration tests for Phase 4: FFmpeg and Media Engine."""

import pytest
import time
from pathlib import Path
from PySide6.QtCore import QCoreApplication

from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.engines.media_inspector import MediaInspector
from omniconvert.engines.ffmpeg_engine import FFmpegEngine
from omniconvert.models.conversion_job import ConversionJob, JobState
from omniconvert.core.job_manager import JobManager
from omniconvert.core.safe_subprocess import SafeSubprocessRunner

@pytest.fixture(scope="module")
def sample_media(tmp_path_factory):
    """Generate synthetic media fixtures using ffmpeg lavfi (audio sine wave and test video)."""
    detector = FFmpegDetector()
    info = detector.detect()
    if not info.is_available:
        pytest.skip("FFmpeg not installed on system; skipping media test generation.")

    media_dir = tmp_path_factory.mktemp("media_fixtures")
    runner = SafeSubprocessRunner()

    # 1. Synthetic 1-second WAV audio file (sine wave, 440Hz, stereo, 44100Hz)
    wav_path = media_dir / "sample.wav"
    runner.run([
        str(info.ffmpeg_path), "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1.0",
        "-c:a", "pcm_s16le",
        str(wav_path)
    ], timeout=10.0)

    # 2. Synthetic 1-second MP4 video file with both video (testsrc) and audio (sine)
    mp4_path = media_dir / "sample.mp4"
    runner.run([
        str(info.ffmpeg_path), "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=1.0",
        "-c:v", "libx264", "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        str(mp4_path)
    ], timeout=15.0)

    # 3. Synthetic silent video without audio track
    silent_mp4 = media_dir / "silent.mp4"
    runner.run([
        str(info.ffmpeg_path), "-y",
        "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=15",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(silent_mp4)
    ], timeout=15.0)

    return {
        "wav": wav_path,
        "mp4": mp4_path,
        "silent_mp4": silent_mp4,
        "ffmpeg_info": info
    }

def test_ffmpeg_detection():
    """Verify FFmpeg and FFprobe binary detection and codec inspection."""
    detector = FFmpegDetector()
    info = detector.detect()
    assert info.is_available, f"FFmpeg should be detected: {info.error_message}"
    assert info.ffmpeg_path and info.ffmpeg_path.exists()
    assert info.ffprobe_path and info.ffprobe_path.exists()
    assert info.ffmpeg_version is not None
    assert "aac" in info.supported_codecs or "libmp3lame" in info.supported_codecs

def test_media_inspector_on_synthetic_video(sample_media):
    """Verify MediaInspector accurately extracts streams, resolution, and duration."""
    inspector = MediaInspector(sample_media["ffmpeg_info"].ffprobe_path)
    res = inspector.inspect(sample_media["mp4"])

    assert res.is_valid
    assert res.has_video
    assert res.has_audio
    assert len(res.video_streams) == 1
    assert len(res.audio_streams) == 1
    assert res.video_streams[0].width == 320
    assert res.video_streams[0].height == 240
    assert res.duration_seconds > 0.8

def test_media_inspector_silent_video(sample_media):
    """Verify inspector detects video without audio stream."""
    inspector = MediaInspector(sample_media["ffmpeg_info"].ffprobe_path)
    res = inspector.inspect(sample_media["silent_mp4"])

    assert res.is_valid
    assert res.has_video
    assert not res.has_audio

def test_video_extract_mp3(sample_media, tmp_path):
    """Verify extracting MP3 audio track from an MP4 file."""
    engine = FFmpegEngine()
    job = ConversionJob(
        source_path=sample_media["mp4"],
        target_format="mp3",
        operation_id="video.extract_mp3",
        engine="ffmpeg",
        settings={"bitrate": "128k"}
    )
    output = engine.execute(job=job, workspace_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".mp3"
    assert output.stat().st_size > 0

    # Probe extracted audio with inspector
    res = engine.inspector.inspect(output)
    assert res.is_valid
    assert res.has_audio
    assert not res.has_video

def test_video_extract_audio_fails_on_silent_video(sample_media, tmp_path):
    """Verify engine raises useful error when trying to extract audio from video without audio."""
    engine = FFmpegEngine()
    job = ConversionJob(
        source_path=sample_media["silent_mp4"],
        target_format="mp3",
        operation_id="video.extract_mp3",
        engine="ffmpeg"
    )
    with pytest.raises(ValueError, match="does not contain an audio stream"):
        engine.execute(job=job, workspace_dir=tmp_path)

def test_audio_to_wav_and_flac(sample_media, tmp_path):
    """Verify audio transcoding to WAV and FLAC."""
    engine = FFmpegEngine()
    # 1. Transcode to WAV
    job_wav = ConversionJob(
        source_path=sample_media["wav"],
        target_format="wav",
        operation_id="audio.to_wav",
        engine="ffmpeg"
    )
    wav_out = engine.execute(job=job_wav, workspace_dir=tmp_path)
    assert wav_out.exists()
    assert wav_out.suffix == ".wav"

    # 2. Transcode to FLAC
    job_flac = ConversionJob(
        source_path=sample_media["wav"],
        target_format="flac",
        operation_id="audio.to_flac",
        engine="ffmpeg"
    )
    flac_out = engine.execute(job=job_flac, workspace_dir=tmp_path)
    assert flac_out.exists()
    assert flac_out.suffix == ".flac"

def test_video_to_gif(sample_media, tmp_path):
    """Verify converting video to animated GIF."""
    engine = FFmpegEngine()
    job_gif = ConversionJob(
        source_path=sample_media["mp4"],
        target_format="gif",
        operation_id="video.to_gif",
        engine="ffmpeg",
        settings={"fps": 10, "width": 160}
    )
    gif_out = engine.execute(job=job_gif, workspace_dir=tmp_path)
    assert gif_out.exists()
    assert gif_out.suffix == ".gif"
    assert gif_out.stat().st_size > 0

def test_job_manager_media_execution(sample_media, tmp_path):
    """Verify end-to-end background conversion of MP4 to MP3 via JobManager."""
    app = QCoreApplication.instance() or QCoreApplication([])

    jm = JobManager(max_concurrent=2)
    job = ConversionJob(
        source_path=sample_media["mp4"],
        target_format="mp3",
        operation_id="video.extract_mp3",
        engine="ffmpeg",
        destination_path=tmp_path
    )

    completed = []
    jm.signals.completed.connect(lambda jid, dest: completed.append((jid, dest)))
    jm.submit_job(job)

    for _ in range(100):
        app.processEvents()
        if completed:
            break
        time.sleep(0.05)

    assert len(completed) == 1
    dest_path = Path(completed[0][1])
    assert dest_path.exists()
    assert dest_path.suffix == ".mp3"
    assert job.state == JobState.COMPLETED
