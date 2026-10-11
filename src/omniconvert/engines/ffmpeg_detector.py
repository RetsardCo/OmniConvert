"""FFmpeg executable discovery and dependency reporting."""

import shutil
import re
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Set

from omniconvert.core.safe_subprocess import SafeSubprocessRunner

@dataclass
class FFmpegInfo:
    is_available: bool = False
    ffmpeg_path: Optional[Path] = None
    ffprobe_path: Optional[Path] = None
    ffmpeg_version: Optional[str] = None
    ffprobe_version: Optional[str] = None
    supported_codecs: Set[str] = field(default_factory=set)
    supported_formats: Set[str] = field(default_factory=set)
    error_message: Optional[str] = None

class FFmpegDetector:
    """Detects, inspects, and validates local FFmpeg and FFprobe installations."""

    def __init__(self, custom_path: Optional[str] = None):
        self.custom_path = custom_path
        self._runner = SafeSubprocessRunner()

    def detect(self) -> FFmpegInfo:
        """Find binaries in PATH or user custom path and probe capabilities."""
        info = FFmpegInfo()

        ffmpeg_bin = self._find_binary("ffmpeg")
        ffprobe_bin = self._find_binary("ffprobe")

        if not ffmpeg_bin or not ffprobe_bin:
            missing = []
            if not ffmpeg_bin:
                missing.append("ffmpeg")
            if not ffprobe_bin:
                missing.append("ffprobe")
            info.error_message = (
                f"Missing required media executables: {', '.join(missing)}.\n"
                "Install FFmpeg (e.g. `winget install Gyan.FFmpeg`) and ensure it is on your PATH."
            )
            return info

        info.ffmpeg_path = ffmpeg_bin
        info.ffprobe_path = ffprobe_bin

        # 1. Read FFmpeg version
        res_ffmpeg = self._runner.run([str(ffmpeg_bin), "-version"], timeout=5.0)
        if res_ffmpeg.returncode == 0:
            match = re.search(r"ffmpeg version\s+([^\s]+)", res_ffmpeg.stdout)
            info.ffmpeg_version = match.group(1) if match else "unknown"

        # 2. Read FFprobe version
        res_ffprobe = self._runner.run([str(ffprobe_bin), "-version"], timeout=5.0)
        if res_ffprobe.returncode == 0:
            match = re.search(r"ffprobe version\s+([^\s]+)", res_ffprobe.stdout)
            info.ffprobe_version = match.group(1) if match else "unknown"

        # 3. Read Codecs & Encoders
        res_codecs = self._runner.run([str(ffmpeg_bin), "-codecs"], timeout=10.0)
        if res_codecs.returncode == 0:
            for line in res_codecs.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and len(parts[0]) == 6:
                    info.supported_codecs.add(parts[1].lower())
                    enc_match = re.search(r"\(encoders:\s*([^)]+)\)", line)
                    if enc_match:
                        for enc in enc_match.group(1).split():
                            info.supported_codecs.add(enc.strip().lower())

        # 4. Read Formats
        res_fmts = self._runner.run([str(ffmpeg_bin), "-formats"], timeout=10.0)
        if res_fmts.returncode == 0:
            for line in res_fmts.stdout.splitlines():
                parts = line.strip().split()
                if len(parts) >= 2 and len(parts[0]) in (2, 3):
                    info.supported_formats.add(parts[1].lower())

        info.is_available = True
        return info

    def _find_binary(self, name: str) -> Optional[Path]:
        """Search PATH, common Windows install directories, or custom path."""
        exe_name = f"{name}.exe" if os.name == "nt" else name

        if self.custom_path:
            p = Path(self.custom_path) / exe_name
            if p.exists():
                return p

        # Check system PATH
        found = shutil.which(exe_name) or shutil.which(name)
        if found:
            return Path(found)

        # Check common Windows winget / scoop / chocolatey paths
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", "")
        user_profile = os.environ.get("USERPROFILE", "")

        candidate_dirs = [
            Path(local_app_data) / "Microsoft" / "WinGet" / "Packages",
            Path(program_files) / "ffmpeg" / "bin",
            Path(program_files) / "Gyan" / "FFmpeg" / "bin",
            Path(user_profile) / "scoop" / "apps" / "ffmpeg" / "current" / "bin",
            Path("C:/ffmpeg/bin"),
        ]

        for cdir in candidate_dirs:
            if cdir.exists():
                direct_match = cdir / exe_name
                if direct_match.exists():
                    return direct_match
                # Recursive search in subdirectories (useful for winget packages)
                for matched in cdir.glob(f"**/{exe_name}"):
                    if matched.exists():
                        return matched

        return None
