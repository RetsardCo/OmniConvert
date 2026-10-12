"""LibreOffice detection and headless conversion runner."""

import os
import shutil
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

from omniconvert.core.safe_subprocess import SafeSubprocessRunner

@dataclass
class LibreOfficeInfo:
    is_available: bool = False
    soffice_path: Optional[Path] = None
    version: Optional[str] = None
    error_message: Optional[str] = None

class LibreOfficeDetector:
    """Discovers local LibreOffice (soffice) executable."""

    def __init__(self, custom_path: Optional[str] = None):
        self.custom_path = custom_path
        self._runner = SafeSubprocessRunner()

    def detect(self) -> LibreOfficeInfo:
        info = LibreOfficeInfo()
        soffice_bin = self._find_binary()

        if not soffice_bin:
            info.error_message = (
                "LibreOffice executable (soffice.exe) not found on host.\n"
                "Install LibreOffice (e.g. `winget install TheDocumentFoundation.LibreOffice`) "
                "to enable office document to PDF conversion."
            )
            return info

        info.soffice_path = soffice_bin

        # Probe version: soffice --version
        res = self._runner.run([str(soffice_bin), "--version"], timeout=5.0)
        if res.returncode == 0:
            match = re.search(r"LibreOffice\s+([\d\.]+)", res.stdout)
            info.version = match.group(1) if match else "unknown"

        info.is_available = True
        return info

    def _find_binary(self) -> Optional[Path]:
        exe_name = "soffice.exe" if os.name == "nt" else "soffice"

        if self.custom_path:
            p = Path(self.custom_path) / exe_name
            if p.exists():
                return p

        # Check system PATH
        found = shutil.which(exe_name) or shutil.which("soffice") or shutil.which("libreoffice")
        if found:
            return Path(found)

        # Check portable/bundled app engines folder
        from omniconvert.config.paths import get_app_root
        app_engines_dir = get_app_root() / "engines" / "libreoffice" / "program" / exe_name

        # Common Windows install paths
        candidate_paths = [
            app_engines_dir,
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "LibreOffice" / "program" / exe_name,
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "LibreOffice" / "program" / exe_name,
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "LibreOffice" / "program" / exe_name,
        ]

        for cp in candidate_paths:
            if cp.exists():
                return cp

        return None
