"""Static Binary Inspection Engine: Printable Strings, Cryptographic Hashes, PE Header Metadata, and Hex Dump."""

from pathlib import Path
import hashlib
import zlib
import math
import json
import re
import logging
from typing import Callable, Optional, Dict, Any, List

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress
from omniconvert.core.file_detector import inspect_file

logger = logging.getLogger(__name__)


class BinaryEngine(BaseEngine):
    """
    Performs safe, static analysis and representation of binary files (EXE, DLL, SYS, BIN, etc.)
    without EVER executing the file.
    """

    @property
    def name(self) -> str:
        return "binary"

    def is_available(self) -> bool:
        return True

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled before binary inspection.")

        source = job.source_path
        op = job.operation_id
        settings = job.settings or {}

        if not source.exists():
            raise FileNotFoundError(f"Source file does not exist: {source}")

        if op == "binary.extract_strings":
            return self._extract_strings(source, workspace_dir, settings, progress_callback, is_cancelled)
        elif op == "binary.inspect_to_json":
            return self._inspect_to_json(source, workspace_dir, settings, progress_callback, is_cancelled)
        elif op == "binary.hex_dump":
            return self._hex_dump(source, workspace_dir, settings, progress_callback, is_cancelled)

        raise NotImplementedError(f"Unsupported binary operation: {op}")

    def _extract_strings(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Extract printable ASCII and UTF-16LE strings from a binary file without executing it."""
        min_len = max(3, int(settings.get("min_length", 4)))
        max_bytes = int(settings.get("max_read_bytes", 16 * 1024 * 1024))  # 16 MB cap

        if progress_callback:
            progress_callback(JobProgress(percentage=20.0, stage="Scanning Binary", detail="Extracting printable strings"))

        with open(source, "rb") as f:
            data = f.read(max_bytes)

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled.")

        # 1. ASCII printable strings (0x20..0x7E)
        ascii_pattern = re.compile(rb"[\x20-\x7e]{" + str(min_len).encode("ascii") + rb",}")
        ascii_matches = [m.group(0).decode("ascii", errors="ignore") for m in ascii_pattern.finditer(data)]

        # 2. UTF-16LE printable strings
        utf16_pattern = re.compile(rb"(?:[\x20-\x7e]\x00){" + str(min_len).encode("ascii") + rb",}")
        utf16_matches = [m.group(0).decode("utf-16le", errors="ignore") for m in utf16_pattern.finditer(data)]

        target_file = workspace_dir / f"{source.stem}_strings.txt"
        lines = [
            f"=== Static Printable Strings Report: {source.name} ===",
            f"Minimum Length: {min_len} | ASCII Count: {len(ascii_matches)} | UTF-16LE Count: {len(utf16_matches)}",
            "--- ASCII Strings ---",
            *ascii_matches[:10000],
            "",
            "--- UTF-16LE Strings ---",
            *utf16_matches[:5000],
        ]
        target_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return target_file

    def _inspect_to_json(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Compute cryptographic hashes, byte entropy, signature, and static PE header info into JSON."""
        if progress_callback:
            progress_callback(JobProgress(percentage=20.0, stage="Hashing & Inspecting", detail=source.name))

        meta = inspect_file(source)
        md5_h = hashlib.md5()
        sha1_h = hashlib.sha1()
        sha256_h = hashlib.sha256()
        crc32_val = 0
        byte_counts = [0] * 256
        total_read = 0

        with open(source, "rb") as f:
            while True:
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled during hash computation.")
                chunk = f.read(65536)
                if not chunk:
                    break
                md5_h.update(chunk)
                sha1_h.update(chunk)
                sha256_h.update(chunk)
                crc32_val = zlib.crc32(chunk, crc32_val)
                if total_read < 1024 * 1024:  # Sample first 1MB for Shannon entropy
                    for b in chunk:
                        byte_counts[b] += 1
                    total_read += len(chunk)

        entropy = 0.0
        if total_read > 0:
            for count in byte_counts:
                if count > 0:
                    p = count / total_read
                    entropy -= p * math.log2(p)

        with open(source, "rb") as f:
            header_bytes = f.read(32)

        report: Dict[str, Any] = {
            "filename": source.name,
            "size_bytes": meta.size_bytes,
            "formatted_size": meta.formatted_size,
            "detected_format": meta.detected_format,
            "detected_category": meta.category,
            "detected_mime": meta.detected_mime,
            "header_hex": header_bytes.hex(),
            "shannon_entropy_bits": round(entropy, 4),
            "hashes": {
                "md5": md5_h.hexdigest(),
                "sha1": sha1_h.hexdigest(),
                "sha256": sha256_h.hexdigest(),
                "crc32": f"{crc32_val & 0xFFFFFFFF:08x}"
            }
        }

        # Static Windows PE inspection if file starts with MZ
        if header_bytes.startswith(b"MZ"):
            try:
                import pefile
                pe = pefile.PE(str(source), fast_load=True)
                try:
                    report["pe_metadata"] = {
                        "machine": hex(pe.FILE_HEADER.Machine),
                        "number_of_sections": pe.FILE_HEADER.NumberOfSections,
                        "time_date_stamp": pe.FILE_HEADER.TimeDateStamp,
                        "is_dll": bool(pe.is_dll()),
                        "is_exe": bool(pe.is_exe()),
                        "sections": [
                            {
                                "name": s.Name.decode("utf-8", errors="ignore").strip("\x00"),
                                "virtual_size": s.Misc_VirtualSize,
                                "raw_size": s.SizeOfRawData,
                            }
                            for s in pe.sections
                        ]
                    }
                finally:
                    pe.close()
            except Exception as e:
                report["pe_metadata_note"] = f"Not a full PE header or could not parse: {e}"

        target_file = workspace_dir / f"{source.stem}_inspection.json"
        target_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return target_file

    def _hex_dump(
        self,
        source: Path,
        workspace_dir: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]],
        is_cancelled: Optional[Callable[[], bool]]
    ) -> Path:
        """Generate a formatted hexadecimal + ASCII dump of a file."""
        max_bytes = int(settings.get("max_bytes", 256 * 1024))  # 256 KB default limit
        with open(source, "rb") as f:
            data = f.read(max_bytes)

        lines = [f"=== Hexadecimal Dump: {source.name} (Showing {len(data):,} bytes) ==="]
        for offset in range(0, len(data), 16):
            if is_cancelled and is_cancelled():
                raise InterruptedError("Cancelled during hex dump.")
            chunk = data[offset:offset + 16]
            hex_part = " ".join(f"{b:02x}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
            lines.append(f"{offset:08x}  {hex_part:<47}  |{ascii_part}|")

        target_file = workspace_dir / f"{source.stem}_hexdump.txt"
        target_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return target_file
