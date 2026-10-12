"""Local OCR Engine using Tesseract OCR (Apache-2.0 License) with language and dependency management."""

from dataclasses import dataclass, field
from pathlib import Path
import os
import shutil
import logging
from typing import Callable, Optional, List

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress
from omniconvert.core.safe_subprocess import SafeSubprocessRunner

logger = logging.getLogger(__name__)


@dataclass
class OCRInfo:
    is_available: bool = False
    tesseract_path: Optional[Path] = None
    version: Optional[str] = None
    languages: List[str] = field(default_factory=lambda: ["eng"])
    license: str = "Apache-2.0 (Tesseract OCR)"
    error_message: Optional[str] = None


class TesseractDetector:
    """Discovers local Tesseract OCR installation and installed language packs."""

    def __init__(self, custom_path: Optional[str] = None):
        self.custom_path = custom_path
        self._runner = SafeSubprocessRunner()

    def detect(self) -> OCRInfo:
        info = OCRInfo()
        tess_bin = self._find_binary()
        if not tess_bin:
            info.error_message = (
                "Local Tesseract OCR executable (tesseract.exe) not found.\n"
                "Install via `winget install UB-Mannheim.TesseractOCR` to enable offline OCR operations."
            )
            return info

        info.tesseract_path = tess_bin
        res = self._runner.run([str(tess_bin), "--version"], timeout=5.0)
        if res.returncode == 0:
            first_line = (res.stdout or res.stderr).splitlines()
            info.version = first_line[0].strip() if first_line else "unknown"

        res_langs = self._runner.run([str(tess_bin), "--list-langs"], timeout=5.0)
        if res_langs.returncode == 0:
            langs = []
            for line in (res_langs.stdout or "").splitlines():
                line = line.strip()
                if line and not line.lower().startswith("list of available"):
                    langs.append(line)
            if langs:
                info.languages = langs

        info.is_available = True
        return info

    def _find_binary(self) -> Optional[Path]:
        exe_name = "tesseract.exe" if os.name == "nt" else "tesseract"
        if self.custom_path:
            p = Path(self.custom_path) / exe_name
            if p.exists():
                return p

        found = shutil.which(exe_name) or shutil.which("tesseract")
        if found:
            return Path(found)

        # Check local bundled app bin/tesseract folder
        from omniconvert.config.paths import get_app_root
        bundled_tess = get_app_root() / "bin" / "tesseract" / exe_name

        candidates = [
            bundled_tess,
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / exe_name,
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Tesseract-OCR" / exe_name,
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / exe_name,
            Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / exe_name,
        ]
        for cp in candidates:
            if cp.exists():
                return cp

        return None


class OCREngine(BaseEngine):
    """Executes local image-to-text optical character recognition using Tesseract."""

    def __init__(self, custom_path: Optional[str] = None):
        self.detector = TesseractDetector(custom_path)
        self.info = self.detector.detect()
        self._runner = SafeSubprocessRunner()

    @property
    def name(self) -> str:
        return "ocr"

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
            raise RuntimeError(f"OCR engine is unavailable: {self.info.error_message}")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled before OCR start.")

        source = job.source_path
        settings = job.settings or {}
        lang = str(settings.get("language", "eng")).strip() or "eng"
        out_base = workspace_dir / source.stem
        target_file = workspace_dir / f"{source.stem}.txt"

        if progress_callback:
            progress_callback(JobProgress(percentage=20.0, stage="Running Local OCR", detail=f"Language: {lang}"))

        args = [
            str(self.info.tesseract_path),
            str(source),
            str(out_base),
            "-l", lang
        ]
        res = self._runner.run(args, timeout=120.0, is_cancelled=is_cancelled)
        if res.cancelled or (is_cancelled and is_cancelled()):
            raise InterruptedError("OCR job cancelled.")
        if res.timed_out:
            raise TimeoutError("OCR recognition timed out.")
        if res.returncode != 0:
            raise RuntimeError(f"Tesseract OCR failed: {res.stderr.strip()}")

        if not target_file.exists():
            raise FileNotFoundError(f"OCR output file was not produced: {target_file}")

        # Ensure non-empty file for validation if image had no recognizable characters
        if target_file.stat().st_size == 0:
            target_file.write_text("[No recognizable text detected in image]\n", encoding="utf-8")

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="OCR text extracted"))

        return target_file
