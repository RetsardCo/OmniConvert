"""FFmpeg Media Engine for audio/video transcoding, lossless/detail presets, stream extraction, metadata export, and CSV-to-video."""

from pathlib import Path
import json
import csv
import logging
from typing import Callable, Optional, List, Dict, Any

from omniconvert.engines.base import BaseEngine
from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.engines.media_inspector import MediaInspector
from omniconvert.models.conversion_job import ConversionJob, JobProgress
from omniconvert.core.safe_subprocess import SafeSubprocessRunner

logger = logging.getLogger(__name__)

AUDIO_PRESET_BITRATES = {
    "lossless": "320k",
    "exact": "320k",
    "high": "256k",
    "balanced": "192k",
    "compact": "128k",
}

VIDEO_PRESET_PARAMS = {
    "lossless": {"crf": "14", "preset": "slow", "audio_bitrate": "320k"},
    "exact": {"crf": "14", "preset": "slow", "audio_bitrate": "320k"},
    "high": {"crf": "18", "preset": "medium", "audio_bitrate": "256k"},
    "balanced": {"crf": "23", "preset": "medium", "audio_bitrate": "192k"},
    "compact": {"crf": "28", "preset": "fast", "audio_bitrate": "128k"},
}


class FFmpegEngine(BaseEngine):
    """Executes media conversion, audio/subtitle extraction, metadata export, and visualization encoding via FFmpeg."""

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
        settings = job.settings or {}
        op = job.operation_id

        # Special operation: CSV to Video visualization template
        if op == "data.csv_to_mp4":
            return self._csv_to_video(source, workspace_dir, settings, progress_callback, is_cancelled)

        # 1. Preflight inspection
        if progress_callback:
            progress_callback(JobProgress(percentage=5.0, stage="Inspecting", detail="Probing source streams"))

        inspection = self.inspector.inspect(source)
        if not inspection.is_valid:
            raise ValueError(f"Source file could not be read: {inspection.error_message}")

        # Special operation: Media metadata export to JSON
        if op in ("video.metadata_to_json", "audio.metadata_to_json") or target_format == "json":
            target_json = workspace_dir / f"{source.stem}.json"
            payload = {
                "filename": source.name,
                "format_name": inspection.format_name,
                "duration_seconds": inspection.duration_seconds,
                "bitrate": inspection.bitrate,
                "has_video": inspection.has_video,
                "has_audio": inspection.has_audio,
                "has_subtitles": inspection.has_subtitles,
                "video_streams": [vars(v) for v in inspection.video_streams],
                "audio_streams": [vars(a) for a in inspection.audio_streams],
                "subtitle_streams": [vars(s) for s in inspection.subtitle_streams],
                "metadata": inspection.metadata,
            }
            target_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return target_json

        # Check required stream types
        if op.startswith("video.extract_") and op != "video.extract_subtitles":
            if not inspection.has_audio:
                raise ValueError("Source file does not contain an audio stream to extract.")
        elif op.startswith("audio.to_"):
            if not inspection.has_audio:
                raise ValueError("Source file does not contain an audio stream to convert.")

        if op == "video.extract_subtitles":
            if not inspection.has_subtitles:
                raise ValueError("Source file does not contain a subtitle stream to extract.")

        # Avoid input == output filename collision inside workspace if source has same stem/ext
        target_file = workspace_dir / f"{source.stem}.{target_format}"

        # 2. Build FFmpeg command argument array
        args = [str(self.info.ffmpeg_path), "-y", "-i", str(source)]

        preset_key = str(settings.get("quality_preset", "lossless")).lower()
        default_ab = AUDIO_PRESET_BITRATES.get(preset_key, "192k")
        bitrate = str(settings.get("bitrate", default_ab))

        # Audio operations & video-to-audio extraction
        if op in ("video.extract_mp3", "audio.to_mp3") or target_format == "mp3":
            args.extend(["-vn", "-c:a", "libmp3lame", "-b:a", bitrate])
            if preset_key in ("lossless", "exact"):
                args.extend(["-q:a", "0"])

        elif op in ("video.extract_wav", "audio.to_wav") or target_format == "wav":
            default_bd = "24" if preset_key in ("lossless", "exact", "high") else "16"
            bit_depth = str(settings.get("bit_depth", default_bd))
            pcm_codec = "pcm_s24le" if bit_depth == "24" else "pcm_f32le" if bit_depth == "32" else "pcm_s16le"
            args.extend(["-vn", "-c:a", pcm_codec])

        elif op in ("video.extract_flac", "audio.to_flac") or target_format == "flac":
            args.extend(["-vn", "-c:a", "flac", "-compression_level", "8"])

        elif op in ("video.extract_aac", "audio.to_aac") or target_format == "aac":
            args.extend(["-vn", "-c:a", "aac", "-b:a", bitrate])

        elif op in ("video.extract_m4a", "audio.to_m4a") or target_format == "m4a":
            use_alac = settings.get("lossless_alac", preset_key in ("lossless", "exact"))
            if use_alac:
                args.extend(["-vn", "-c:a", "alac"])
            else:
                args.extend(["-vn", "-c:a", "aac", "-b:a", bitrate])

        elif op in ("video.extract_ogg", "audio.to_ogg") or target_format == "ogg":
            codec = "libvorbis" if "libvorbis" in self.info.supported_codecs else "vorbis"
            q_map = {"320k": "9", "256k": "8", "192k": "6", "128k": "4", "96k": "2"}
            q_val = q_map.get(bitrate, "7")
            if codec == "vorbis":
                args.extend(["-vn", "-c:a", "vorbis", "-strict", "-2", "-ac", "2", "-q:a", q_val])
            else:
                args.extend(["-vn", "-c:a", "libvorbis", "-q:a", q_val])

        elif op in ("video.extract_opus", "audio.to_opus") or target_format == "opus":
            codec = "libopus" if "libopus" in self.info.supported_codecs else "opus"
            in_ch = inspection.audio_streams[0].channels if inspection.audio_streams else 2
            out_ch = int(settings.get("channels", in_ch) or in_ch)
            opus_bitrate = "256k" if (out_ch == 1 and bitrate == "320k") else bitrate
            args.extend(["-vn", "-c:a", codec, "-b:a", opus_bitrate])
            if codec == "opus":
                args.extend(["-strict", "-2"])

        elif op == "audio.to_aiff" or target_format == "aiff":
            default_bd = "24" if preset_key in ("lossless", "exact", "high") else "16"
            bit_depth = str(settings.get("bit_depth", default_bd))
            aiff_codec = "pcm_s24be" if bit_depth == "24" else "pcm_s32be" if bit_depth == "32" else "pcm_s16be"
            args.extend(["-vn", "-c:a", aiff_codec])

        # Video transcoding operations
        elif op in ("video.to_mp4", "video.to_mkv", "video.to_mov", "video.to_avi", "video.to_webm"):
            v_defaults = VIDEO_PRESET_PARAMS.get(preset_key, VIDEO_PRESET_PARAMS["balanced"])
            crf = str(settings.get("crf", v_defaults["crf"]))
            v_preset = str(settings.get("preset", v_defaults["preset"]))
            a_bitrate = str(settings.get("bitrate", v_defaults["audio_bitrate"]))

            if target_format == "webm":
                v_codec = "libvpx-vp9" if "libvpx-vp9" in self.info.supported_codecs else "libvpx"
                a_codec = "libopus" if "libopus" in self.info.supported_codecs else "libvorbis"
                args.extend(["-c:v", v_codec, "-crf", crf, "-b:v", "0"])
                if inspection.has_audio:
                    args.extend(["-c:a", a_codec, "-b:a", a_bitrate])
            else:
                args.extend(["-c:v", "libx264", "-crf", crf, "-preset", v_preset, "-pix_fmt", "yuv420p"])
                if inspection.has_audio:
                    args.extend(["-c:a", "aac", "-b:a", a_bitrate])
                if target_format == "mp4":
                    args.extend(["-movflags", "+faststart"])

            # Optional resolution scaling and FPS
            vf_filters = []
            scale_h = settings.get("scale_height")
            if scale_h and str(scale_h).isdigit() and int(scale_h) > 0:
                vf_filters.append(f"scale=-2:{int(scale_h)}")
            fps = settings.get("fps")
            if fps and str(fps).isdigit() and int(fps) > 0:
                vf_filters.append(f"fps={int(fps)}")
            if vf_filters:
                args.extend(["-vf", ",".join(vf_filters)])

        elif op == "video.to_gif" or target_format == "gif":
            fps = str(settings.get("fps", 15 if preset_key in ("lossless", "exact", "high") else 12))
            width = str(settings.get("width", 640 if preset_key in ("lossless", "exact") else 480))
            args.extend(["-vf", f"fps={fps},scale={width}:-1:flags=lanczos", "-c:v", "gif"])

        elif op == "video.extract_subtitles":
            sub_codec = "srt" if target_format == "srt" else "webvtt" if target_format == "vtt" else "text"
            args.extend(["-map", "0:s:0", "-c:s", sub_codec])

        else:
            args.extend(["-c", "copy"])

        # Apply optional audio sample rate and channel overrides for audio outputs
        if target_format in ("mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "aiff"):
            srate = settings.get("sample_rate")
            if srate and str(srate).isdigit() and int(srate) > 0:
                sr_int = int(srate)
                if target_format != "opus" or sr_int in (8000, 12000, 16000, 24000, 48000):
                    args.extend(["-ar", str(sr_int)])
            channels = settings.get("channels")
            if channels and str(channels).isdigit() and int(channels) in (1, 2):
                args.extend(["-ac", str(int(channels))])

        args.append(str(target_file))

        if progress_callback:
            progress_callback(JobProgress(percentage=15.0, stage="Transcoding", detail=f"Encoding to .{target_format.upper()}"))

        # 3. Execute with SafeSubprocessRunner
        res = self._runner.run(args, timeout=600.0, is_cancelled=is_cancelled)

        if res.cancelled or (is_cancelled and is_cancelled()):
            raise InterruptedError("Job cancelled by user.")

        if res.timed_out:
            raise TimeoutError("Conversion timed out.")

        if res.returncode != 0:
            error_details = res.stderr.strip() or "FFmpeg process failed."
            err_lines = [line.strip() for line in error_details.splitlines() if line.strip()]
            concise_err = "\n".join(err_lines[-5:]) if err_lines else error_details
            raise RuntimeError(f"FFmpeg encoding error:\n{concise_err}")

        if progress_callback:
            progress_callback(JobProgress(percentage=90.0, stage="Encoding complete", detail="Verifying media output"))

        return target_file

    def _csv_to_video(
        self,
        csv_path: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Render tabular CSV data into animated chart/slideshow video frames and encode to MP4."""
        from PIL import Image, ImageDraw

        with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
            rows = list(csv.reader(f))

        if not rows:
            raise ValueError("CSV file is empty; cannot generate visualization video.")

        frames_dir = workspace_dir / "csv_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        headers = rows[0]
        data_rows = rows[1:] if len(rows) > 1 else [rows[0]]

        # Generate progressive visual chart frames
        total_frames = min(max(len(data_rows), 2), 30)
        width, height = 640, 360

        for idx in range(total_frames):
            if is_cancelled and is_cancelled():
                raise InterruptedError("Cancelled during CSV frame rendering.")
            img = Image.new("RGB", (width, height), (24, 25, 28))
            draw = ImageDraw.Draw(img)

            # Header banner
            draw.rectangle([0, 0, width, 54], fill=(0, 102, 204))
            draw.text((20, 18), f"OmniConvert Data Visualization: {csv_path.name}", fill=(255, 255, 255))

            # Draw rows up to current frame
            visible_count = min(idx + 1, len(data_rows))
            y = 75
            draw.text((20, y), " | ".join(str(h)[:18] for h in headers[:5]), fill=(155, 161, 166))
            y += 28

            for r_idx in range(min(visible_count, 8)):
                row = data_rows[max(0, visible_count - 8 + r_idx)]
                row_text = " | ".join(str(c)[:18] for c in row[:5])
                bar_w = min(width - 60, 80 + ((r_idx + 1) * 55))
                draw.rectangle([20, y, 20 + bar_w, y + 22], fill=(43, 47, 56), outline=(59, 130, 246))
                draw.text((28, y + 4), row_text, fill=(240, 242, 245))
                y += 28

            frame_file = frames_dir / f"frame_{idx:03d}.png"
            img.save(frame_file, "PNG")

        target_mp4 = workspace_dir / f"{csv_path.stem}.mp4"
        args = [
            str(self.info.ffmpeg_path), "-y",
            "-framerate", "2",
            "-i", str(frames_dir / "frame_%03d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(target_mp4)
        ]
        res = self._runner.run(args, timeout=120.0)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to encode CSV visualization video: {res.stderr[-300:]}")

        return target_mp4
