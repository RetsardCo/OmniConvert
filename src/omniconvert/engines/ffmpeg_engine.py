"""FFmpeg Media Engine for transcoding, extraction, and compression."""

from pathlib import Path
import re
import logging
from typing import Callable, Optional, List

from omniconvert.engines.base import BaseEngine
from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.engines.media_inspector import MediaInspector
from omniconvert.models.conversion_job import ConversionJob, JobProgress
from omniconvert.core.safe_subprocess import SafeSubprocessRunner

logger = logging.getLogger(__name__)

class FFmpegEngine(BaseEngine):
    """Executes media conversion and audio/subtitle extraction via FFmpeg."""

    def __init__(self, custom_path: Optional[str] = None):
        self.detector = FFmpegDetector(custom_path)
        self.info = self.detector.detect()
        self.inspector = MediaInspector(self.info.ffprobe_path)
        self._runner = SafeSubprocessRunner()

    @property
    def name(self) -> str:
        return "ffmpeg"

    def is_available(self) -> bool:
        return self.info.is_available

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if not self.is_available():
            raise RuntimeError(f"FFmpeg is not available: {self.info.error_message}")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Job cancelled before start.")

        source = job.source_path
        target_format = job.target_format.lower().lstrip(".")
        target_file = workspace_dir / f"{source.stem}.{target_format}"

        # 1. Preflight inspection
        if progress_callback:
            progress_callback(JobProgress(percentage=5.0, stage="Inspecting", detail="Probing source streams"))

        inspection = self.inspector.inspect(source)
        if not inspection.is_valid:
            raise ValueError(f"Source file could not be read: {inspection.error_message}")

        # Check required stream types
        if job.operation_id.startswith("video.extract_") or job.operation_id.startswith("audio.to_"):
            if not inspection.has_audio:
                raise ValueError("Source file does not contain an audio stream to extract.")

        if job.operation_id == "video.extract_subtitles":
            if not inspection.has_subtitles:
                raise ValueError("Source file does not contain a subtitle stream to extract.")

        # 2. Build FFmpeg command argument array
        args = [str(self.info.ffmpeg_path), "-y", "-i", str(source)]

        # Apply operation-specific encoding flags
        if job.operation_id in ("video.extract_mp3", "audio.to_mp3"):
            bitrate = job.settings.get("bitrate", "192k")
            args.extend(["-vn", "-c:a", "libmp3lame", "-b:a", bitrate])

        elif job.operation_id in ("video.extract_wav", "audio.to_wav"):
            args.extend(["-vn", "-c:a", "pcm_s16le"])

        elif job.operation_id == "audio.to_flac":
            args.extend(["-vn", "-c:a", "flac"])

        elif job.operation_id == "video.to_mp4":
            # H.264 video + AAC audio preset
            crf = str(job.settings.get("crf", 23))
            preset = job.settings.get("preset", "medium")
            args.extend(["-c:v", "libx264", "-crf", crf, "-preset", preset, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"])

        elif job.operation_id == "video.to_mkv":
            args.extend(["-c:v", "libx264", "-crf", "23", "-preset", "medium", "-c:a", "aac", "-b:a", "192k"])

        elif job.operation_id == "video.to_gif":
            # High quality palettegen / paletteuse GIF filter
            fps = str(job.settings.get("fps", 12))
            width = str(job.settings.get("width", 480))
            args.extend(["-vf", f"fps={fps},scale={width}:-1:flags=lanczos", "-c:v", "gif"])

        elif job.operation_id == "video.extract_subtitles":
            # Extract first text subtitle stream to srt / vtt / txt
            sub_codec = "srt" if target_format == "srt" else "webvtt" if target_format == "vtt" else "text"
            args.extend(["-map", "0:s:0", "-c:s", sub_codec])

        else:
            # Fallback direct container remux / encode
            args.extend(["-c", "copy"])

        args.append(str(target_file))

        if progress_callback:
            progress_callback(JobProgress(percentage=15.0, stage="Transcoding", detail=f"Encoding to .{target_format.upper()}"))

        # 3. Execute with SafeSubprocessRunner
        runner = SafeSubprocessRunner()

        def check_cancellation():
            if is_cancelled and is_cancelled():
                runner.cancel()

        # Run conversion process
        res = runner.run(args, timeout=600.0)

        if res.cancelled or (is_cancelled and is_cancelled()):
            raise InterruptedError("Job cancelled by user.")

        if res.timed_out:
            raise TimeoutError("Conversion timed out.")

        if res.returncode != 0:
            error_details = res.stderr.strip() or "FFmpeg process failed."
            # Keep last 5 lines of stderr for concise, actionable error reporting
            err_lines = [line.strip() for line in error_details.splitlines() if line.strip()]
            concise_err = "\n".join(err_lines[-5:]) if err_lines else error_details
            raise RuntimeError(f"FFmpeg encoding error:\n{concise_err}")

        if progress_callback:
            progress_callback(JobProgress(percentage=90.0, stage="Encoding complete", detail="Verifying media output"))

        return target_file
