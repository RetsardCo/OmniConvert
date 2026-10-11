"""Media container and stream inspection using FFprobe."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import logging

from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.core.safe_subprocess import SafeSubprocessRunner

logger = logging.getLogger(__name__)

@dataclass
class AudioStreamInfo:
    index: int
    codec_name: str
    sample_rate: int
    channels: int
    bitrate: Optional[int] = None
    language: Optional[str] = None

@dataclass
class VideoStreamInfo:
    index: int
    codec_name: str
    width: int
    height: int
    frame_rate: Optional[float] = None
    bitrate: Optional[int] = None
    pix_fmt: Optional[str] = None

@dataclass
class SubtitleStreamInfo:
    index: int
    codec_name: str
    language: Optional[str] = None
    title: Optional[str] = None

@dataclass
class MediaInspectionResult:
    is_valid: bool = False
    duration_seconds: float = 0.0
    format_name: str = ""
    bitrate: Optional[int] = None
    video_streams: List[VideoStreamInfo] = field(default_factory=list)
    audio_streams: List[AudioStreamInfo] = field(default_factory=list)
    subtitle_streams: List[SubtitleStreamInfo] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    @property
    def has_audio(self) -> bool:
        return len(self.audio_streams) > 0

    @property
    def has_video(self) -> bool:
        return len(self.video_streams) > 0

    @property
    def has_subtitles(self) -> bool:
        return len(self.subtitle_streams) > 0


class MediaInspector:
    """Inspects media files using ffprobe with structured JSON output."""

    def __init__(self, ffprobe_path: Optional[Path] = None):
        if ffprobe_path:
            self.ffprobe_path = ffprobe_path
        else:
            detector = FFmpegDetector()
            info = detector.detect()
            self.ffprobe_path = info.ffprobe_path
        self._runner = SafeSubprocessRunner()

    def inspect(self, file_path: Path | str) -> MediaInspectionResult:
        path = Path(file_path).resolve()
        if not path.exists():
            return MediaInspectionResult(error_message=f"File does not exist: {path}")

        if not self.ffprobe_path or not self.ffprobe_path.exists():
            return MediaInspectionResult(error_message="FFprobe executable not found on host.")

        args = [
            str(self.ffprobe_path),
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path)
        ]

        res = self._runner.run(args, timeout=15.0)
        if res.returncode != 0 or not res.stdout.strip():
            err = res.stderr.strip() or "FFprobe failed to read file."
            return MediaInspectionResult(error_message=f"Corrupt or unsupported media: {err}")

        try:
            data = json.loads(res.stdout)
        except json.JSONDecodeError as e:
            return MediaInspectionResult(error_message=f"Failed to parse FFprobe output: {e}")

        result = MediaInspectionResult(is_valid=True)
        fmt = data.get("format", {})
        result.format_name = fmt.get("format_name", "")
        try:
            result.duration_seconds = float(fmt.get("duration", 0.0))
        except (ValueError, TypeError):
            result.duration_seconds = 0.0

        try:
            result.bitrate = int(fmt.get("bit_rate")) if fmt.get("bit_rate") else None
        except (ValueError, TypeError):
            result.bitrate = None

        result.metadata = fmt.get("tags", {})

        for stream in data.get("streams", []):
            stype = stream.get("codec_type")
            idx = stream.get("index", 0)
            codec = stream.get("codec_name", "unknown")
            tags = stream.get("tags", {})
            lang = tags.get("language")

            if stype == "video":
                # Skip attached picture streams (e.g. album art in MP3)
                if stream.get("disposition", {}).get("attached_pic"):
                    continue
                w = stream.get("width", 0)
                h = stream.get("height", 0)
                fps = None
                r_frame_rate = stream.get("r_frame_rate", "")
                if "/" in r_frame_rate:
                    num, den = r_frame_rate.split("/")
                    try:
                        if float(den) > 0:
                            fps = round(float(num) / float(den), 2)
                    except (ValueError, ZeroDivisionError):
                        pass

                result.video_streams.append(VideoStreamInfo(
                    index=idx,
                    codec_name=codec,
                    width=w,
                    height=h,
                    frame_rate=fps,
                    pix_fmt=stream.get("pix_fmt")
                ))

            elif stype == "audio":
                try:
                    srate = int(stream.get("sample_rate", 44100))
                except (ValueError, TypeError):
                    srate = 44100
                channels = stream.get("channels", 2)
                result.audio_streams.append(AudioStreamInfo(
                    index=idx,
                    codec_name=codec,
                    sample_rate=srate,
                    channels=channels,
                    language=lang
                ))

            elif stype == "subtitle":
                result.subtitle_streams.append(SubtitleStreamInfo(
                    index=idx,
                    codec_name=codec,
                    language=lang,
                    title=tags.get("title")
                ))

        return result
