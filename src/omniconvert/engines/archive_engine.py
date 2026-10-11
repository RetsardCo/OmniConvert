"""Archive and Compression Engine (ZIP, TAR, TAR.GZ, GZ, 7Z) with strict security safeguards."""

from dataclasses import dataclass, field
from pathlib import Path
import zipfile
import tarfile
import gzip
import shutil
import logging
from typing import Callable, Optional, List, Dict, Any

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress

logger = logging.getLogger(__name__)

# Default security limits against zip bombs and resource exhaustion
DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
DEFAULT_MAX_ENTRIES = 10_000
DEFAULT_MAX_COMPRESSION_RATIO = 200.0


@dataclass
class ArchiveEntryInfo:
    name: str
    uncompressed_size: int
    compressed_size: int
    is_dir: bool = False
    is_symlink: bool = False


@dataclass
class ArchiveInspectionResult:
    is_valid: bool = False
    format: str = ""
    entries: List[ArchiveEntryInfo] = field(default_factory=list)
    total_uncompressed_bytes: int = 0
    total_compressed_bytes: int = 0
    has_suspicious_paths: bool = False
    suspicious_entries: List[str] = field(default_factory=list)
    error_message: Optional[str] = None


def is_safe_archive_member_path(member_name: str, target_dir: Path) -> bool:
    """
    Verify that an archive entry path does not attempt path traversal (Zip Slip)
    or use absolute / drive-qualified paths.
    """
    cleaned = member_name.replace("\\", "/")
    if cleaned.startswith("/") or cleaned.startswith("\\"):
        return False
    if ":" in cleaned.split("/")[0]:  # Windows drive letter like C:
        return False
    parts = [p for p in cleaned.split("/") if p]
    if ".." in parts:
        return False

    resolved_root = target_dir.resolve()
    candidate = (resolved_root / cleaned).resolve()
    try:
        candidate.relative_to(resolved_root)
        return True
    except ValueError:
        return False


class ArchiveEngine(BaseEngine):
    """
    Executes archive inspection, extraction, creation, and repacking with path traversal
    and decompression bomb protections.
    """

    @property
    def name(self) -> str:
        return "archive"

    def is_available(self) -> bool:
        return True

    def is_7z_available(self) -> bool:
        try:
            import py7zr
            return True
        except ImportError:
            return shutil.which("7z") is not None

    def inspect_archive(
        self,
        archive_path: Path,
        max_total_size: int = DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        max_ratio: float = DEFAULT_MAX_COMPRESSION_RATIO
    ) -> ArchiveInspectionResult:
        """Inspect archive contents and verify safety constraints before extraction."""
        path = Path(archive_path).resolve()
        if not path.exists():
            return ArchiveInspectionResult(error_message=f"Archive does not exist: {path}")

        name_lower = path.name.lower()
        entries: List[ArchiveEntryInfo] = []
        suspicious: List[str] = []
        total_uncompressed = 0
        total_compressed = 0
        dummy_root = Path.cwd()

        try:
            if name_lower.endswith(".zip") or zipfile.is_zipfile(path):
                fmt = "zip"
                with zipfile.ZipFile(path, "r") as zf:
                    infolist = zf.infolist()
                    if len(infolist) > max_entries:
                        return ArchiveInspectionResult(
                            format=fmt,
                            error_message=f"Archive exceeds maximum entry count ({len(infolist)} > {max_entries})."
                        )
                    for info in infolist:
                        is_symlink = (info.external_attr >> 16) & 0o170000 == 0o120000
                        if not is_safe_archive_member_path(info.filename, dummy_root) or is_symlink:
                            suspicious.append(info.filename)
                        total_uncompressed += info.file_size
                        total_compressed += max(info.compress_size, 1)
                        entries.append(ArchiveEntryInfo(
                            name=info.filename,
                            uncompressed_size=info.file_size,
                            compressed_size=info.compress_size,
                            is_dir=info.is_dir(),
                            is_symlink=is_symlink
                        ))

            elif any(name_lower.endswith(ext) for ext in (".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
                fmt = "tar"
                with tarfile.open(path, "r:*") as tf:
                    members = tf.getmembers()
                    if len(members) > max_entries:
                        return ArchiveInspectionResult(
                            format=fmt,
                            error_message=f"Archive exceeds maximum entry count ({len(members)} > {max_entries})."
                        )
                    archive_file_size = max(path.stat().st_size, 1)
                    for m in members:
                        is_sym = m.issym() or m.islnk()
                        if not is_safe_archive_member_path(m.name, dummy_root) or is_sym:
                            suspicious.append(m.name)
                        total_uncompressed += m.size
                        entries.append(ArchiveEntryInfo(
                            name=m.name,
                            uncompressed_size=m.size,
                            compressed_size=0,
                            is_dir=m.isdir(),
                            is_symlink=is_sym
                        ))
                    total_compressed = archive_file_size

            elif name_lower.endswith(".7z"):
                fmt = "7z"
                import py7zr
                with py7zr.SevenZipFile(path, mode="r") as sz:
                    archive_list = sz.list()
                    if len(archive_list) > max_entries:
                        return ArchiveInspectionResult(
                            format=fmt,
                            error_message=f"Archive exceeds maximum entry count ({len(archive_list)} > {max_entries})."
                        )
                    for item in archive_list:
                        is_sym = getattr(item, "is_symlink", False)
                        if not is_safe_archive_member_path(item.filename, dummy_root) or is_sym:
                            suspicious.append(item.filename)
                        uncomp = item.uncompressed or 0
                        comp = item.compressed or 1
                        total_uncompressed += uncomp
                        total_compressed += comp
                        entries.append(ArchiveEntryInfo(
                            name=item.filename,
                            uncompressed_size=uncomp,
                            compressed_size=comp,
                            is_dir=item.is_directory,
                            is_symlink=is_sym
                        ))

            elif name_lower.endswith(".gz"):
                fmt = "gz"
                comp_size = max(path.stat().st_size, 1)
                total_compressed = comp_size
                stem_name = path.stem or "decompressed_file"
                entries.append(ArchiveEntryInfo(
                    name=stem_name,
                    uncompressed_size=0,
                    compressed_size=comp_size,
                    is_dir=False,
                    is_symlink=False
                ))
            else:
                return ArchiveInspectionResult(error_message=f"Unsupported or unrecognized archive format: {path.name}")

        except Exception as e:
            return ArchiveInspectionResult(error_message=f"Corrupt or unreadable archive: {e}")

        if suspicious:
            return ArchiveInspectionResult(
                is_valid=False,
                format=fmt,
                entries=entries,
                total_uncompressed_bytes=total_uncompressed,
                total_compressed_bytes=total_compressed,
                has_suspicious_paths=True,
                suspicious_entries=suspicious,
                error_message=f"Unsafe archive entries detected (path traversal or symlink): {suspicious[:3]}"
            )

        if total_uncompressed > max_total_size:
            return ArchiveInspectionResult(
                is_valid=False,
                format=fmt,
                entries=entries,
                total_uncompressed_bytes=total_uncompressed,
                total_compressed_bytes=total_compressed,
                error_message=f"Decompressed size ({total_uncompressed:,} bytes) exceeds safety limit ({max_total_size:,} bytes)."
            )

        # Check compression ratio for large archives (>1MB uncompressed) to catch archive bombs
        if total_uncompressed > 1024 * 1024 and total_compressed > 0:
            ratio = total_uncompressed / total_compressed
            if ratio > max_ratio:
                return ArchiveInspectionResult(
                    is_valid=False,
                    format=fmt,
                    entries=entries,
                    total_uncompressed_bytes=total_uncompressed,
                    total_compressed_bytes=total_compressed,
                    error_message=f"Suspicious compression ratio ({ratio:.1f}:1 > {max_ratio}:1); potential archive bomb."
                )

        return ArchiveInspectionResult(
            is_valid=True,
            format=fmt,
            entries=entries,
            total_uncompressed_bytes=total_uncompressed,
            total_compressed_bytes=total_compressed
        )

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled before start.")

        source = job.source_path
        op = job.operation_id
        target_format = job.target_format.lower().lstrip(".")
        settings = job.settings or {}

        max_size = int(settings.get("max_uncompressed_bytes", DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES))
        max_entries = int(settings.get("max_entries", DEFAULT_MAX_ENTRIES))
        max_ratio = float(settings.get("max_compression_ratio", DEFAULT_MAX_COMPRESSION_RATIO))

        # 1. Inspect / List Archive to JSON
        if op == "archive.list_to_json" or (target_format == "json" and op.startswith("archive.")):
            import json
            info = self.inspect_archive(source, max_size, max_entries, max_ratio)
            if not info.is_valid and not info.entries:
                raise ValueError(info.error_message or "Invalid archive")
            target_file = workspace_dir / f"{source.stem}_manifest.json"
            payload = {
                "archive": source.name,
                "format": info.format,
                "is_valid": info.is_valid,
                "total_uncompressed_bytes": info.total_uncompressed_bytes,
                "entry_count": len(info.entries),
                "entries": [
                    {
                        "name": e.name,
                        "uncompressed_size": e.uncompressed_size,
                        "compressed_size": e.compressed_size,
                        "is_dir": e.is_dir
                    }
                    for e in info.entries
                ]
            }
            target_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return target_file

        # 2. Extract Archive (ZIP, TAR, TAR.GZ, GZ, 7Z)
        if op in ("archive.extract_zip", "archive.extract_tar", "archive.extract_gz", "archive.extract_7z", "archive.extract"):
            extract_dir = workspace_dir / f"{source.stem}_extracted"
            extract_dir.mkdir(parents=True, exist_ok=True)
            return self.extract_safely(
                source, extract_dir,
                max_total_size=max_size,
                max_entries=max_entries,
                max_ratio=max_ratio,
                progress_callback=progress_callback,
                is_cancelled=is_cancelled
            )

        # 3. Create Archive from file or directory (to ZIP, TAR, TAR.GZ, GZ, 7Z)
        if op in ("archive.create_zip", "archive.to_zip") or target_format == "zip":
            if source.suffix.lower() in (".tar", ".gz", ".tgz", ".7z") and source.is_file():
                # Repack existing archive into ZIP
                temp_extract = workspace_dir / "repack_extract"
                temp_extract.mkdir(parents=True, exist_ok=True)
                self.extract_safely(source, temp_extract, max_size, max_entries, max_ratio, progress_callback, is_cancelled)
                out_zip = workspace_dir / f"{source.stem}.zip"
                return self.create_zip(temp_extract, out_zip, settings, progress_callback, is_cancelled)
            else:
                out_zip = workspace_dir / f"{source.stem}.zip"
                return self.create_zip(source, out_zip, settings, progress_callback, is_cancelled)

        if op in ("archive.create_tar", "archive.to_tar") or target_format in ("tar", "tar.gz", "tgz"):
            compress_gz = target_format in ("tar.gz", "tgz") or settings.get("gzip", False)
            ext = "tar.gz" if compress_gz else "tar"
            out_tar = workspace_dir / f"{source.stem}.{ext}"
            if source.suffix.lower() in (".zip", ".7z") and source.is_file():
                temp_extract = workspace_dir / "repack_extract"
                temp_extract.mkdir(parents=True, exist_ok=True)
                self.extract_safely(source, temp_extract, max_size, max_entries, max_ratio, progress_callback, is_cancelled)
                return self.create_tar(temp_extract, out_tar, compress_gz, progress_callback, is_cancelled)
            return self.create_tar(source, out_tar, compress_gz, progress_callback, is_cancelled)

        if op in ("archive.create_gz", "archive.to_gz") or target_format == "gz":
            out_gz = workspace_dir / f"{source.name}.gz"
            return self.create_gz(source, out_gz, settings, progress_callback, is_cancelled)

        if op in ("archive.create_7z", "archive.to_7z") or target_format == "7z":
            out_7z = workspace_dir / f"{source.stem}.7z"
            if source.suffix.lower() in (".zip", ".tar", ".gz", ".tgz") and source.is_file():
                temp_extract = workspace_dir / "repack_extract"
                temp_extract.mkdir(parents=True, exist_ok=True)
                self.extract_safely(source, temp_extract, max_size, max_entries, max_ratio, progress_callback, is_cancelled)
                return self.create_7z(temp_extract, out_7z, progress_callback, is_cancelled)
            return self.create_7z(source, out_7z, progress_callback, is_cancelled)

        raise NotImplementedError(f"Unsupported archive operation: {op}")

    def extract_safely(
        self,
        archive_path: Path,
        dest_dir: Path,
        max_total_size: int = DEFAULT_MAX_TOTAL_UNCOMPRESSED_BYTES,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        max_ratio: float = DEFAULT_MAX_COMPRESSION_RATIO,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """Inspect and safely extract archive contents into dest_dir."""
        if progress_callback:
            progress_callback(JobProgress(percentage=10.0, stage="Inspecting archive", detail=archive_path.name))

        inspection = self.inspect_archive(archive_path, max_total_size, max_entries, max_ratio)
        if not inspection.is_valid:
            raise ValueError(inspection.error_message or "Archive failed security inspection.")

        dest_dir.mkdir(parents=True, exist_ok=True)
        fmt = inspection.format

        if fmt == "zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                members = zf.infolist()
                total = max(len(members), 1)
                bytes_written = 0
                for idx, member in enumerate(members):
                    if is_cancelled and is_cancelled():
                        raise InterruptedError("Archive extraction cancelled.")
                    if not is_safe_archive_member_path(member.filename, dest_dir):
                        raise ValueError(f"Path traversal blocked: {member.filename}")
                    target_path = (dest_dir / member.filename).resolve()
                    if member.is_dir():
                        target_path.mkdir(parents=True, exist_ok=True)
                        continue
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member, "r") as src_f, open(target_path, "wb") as dst_f:
                        while True:
                            chunk = src_f.read(65536)
                            if not chunk:
                                break
                            bytes_written += len(chunk)
                            if bytes_written > max_total_size:
                                raise ValueError("Decompressed data exceeded maximum size limit during extraction.")
                            dst_f.write(chunk)
                    if progress_callback:
                        progress_callback(JobProgress(
                            percentage=15.0 + (idx / total) * 80.0,
                            stage="Extracting ZIP",
                            detail=member.filename
                        ))

        elif fmt == "tar":
            with tarfile.open(archive_path, "r:*") as tf:
                members = tf.getmembers()
                total = max(len(members), 1)
                bytes_written = 0
                for idx, member in enumerate(members):
                    if is_cancelled and is_cancelled():
                        raise InterruptedError("Archive extraction cancelled.")
                    if member.issym() or member.islnk():
                        raise ValueError(f"Symbolic or hard links are blocked for security: {member.name}")
                    if not is_safe_archive_member_path(member.name, dest_dir):
                        raise ValueError(f"Path traversal blocked: {member.name}")
                    target_path = (dest_dir / member.name).resolve()
                    if member.isdir():
                        target_path.mkdir(parents=True, exist_ok=True)
                        continue
                    if member.isfile():
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        src_f = tf.extractfile(member)
                        if src_f:
                            with src_f, open(target_path, "wb") as dst_f:
                                while True:
                                    chunk = src_f.read(65536)
                                    if not chunk:
                                        break
                                    bytes_written += len(chunk)
                                    if bytes_written > max_total_size:
                                        raise ValueError("Decompressed data exceeded maximum size limit during extraction.")
                                    dst_f.write(chunk)
                    if progress_callback:
                        progress_callback(JobProgress(
                            percentage=15.0 + (idx / total) * 80.0,
                            stage="Extracting TAR",
                            detail=member.name
                        ))

        elif fmt == "gz":
            out_name = archive_path.stem or "decompressed.bin"
            if not is_safe_archive_member_path(out_name, dest_dir):
                out_name = "decompressed.bin"
            target_file = dest_dir / out_name
            bytes_written = 0
            with gzip.open(archive_path, "rb") as src_f, open(target_file, "wb") as dst_f:
                while True:
                    if is_cancelled and is_cancelled():
                        raise InterruptedError("GZ decompression cancelled.")
                    chunk = src_f.read(65536)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > max_total_size:
                        raise ValueError("GZip stream exceeded maximum decompressed size limit.")
                    dst_f.write(chunk)

        elif fmt == "7z":
            import py7zr
            with py7zr.SevenZipFile(archive_path, mode="r") as sz:
                for item in sz.list():
                    if not is_safe_archive_member_path(item.filename, dest_dir):
                        raise ValueError(f"Path traversal blocked in 7z archive: {item.filename}")
                sz.extractall(path=dest_dir)

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Archive extracted safely"))

        return dest_dir

    def create_zip(
        self,
        source: Path,
        out_zip: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """Create a validated ZIP archive from a file or directory."""
        comp_level = int(settings.get("compresslevel", 6))
        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=comp_level) as zf:
            if source.is_dir():
                files = [p for p in source.rglob("*") if p.is_file() and not p.is_symlink()]
                total = max(len(files), 1)
                for idx, fpath in enumerate(files):
                    if is_cancelled and is_cancelled():
                        raise InterruptedError("ZIP creation cancelled.")
                    arcname = str(fpath.relative_to(source))
                    zf.write(fpath, arcname=arcname)
                    if progress_callback:
                        progress_callback(JobProgress(
                            percentage=10.0 + (idx / total) * 85.0,
                            stage="Compressing ZIP",
                            detail=arcname
                        ))
            else:
                zf.write(source, arcname=source.name)

        # Validate created ZIP
        with zipfile.ZipFile(out_zip, "r") as check_zf:
            if check_zf.testzip() is not None:
                raise RuntimeError("Created ZIP failed integrity verification.")

        return out_zip

    def create_tar(
        self,
        source: Path,
        out_tar: Path,
        gzip_compress: bool = False,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """Create a TAR or TAR.GZ archive from a file or directory."""
        mode = "w:gz" if gzip_compress else "w"
        with tarfile.open(out_tar, mode) as tf:
            if source.is_dir():
                for fpath in source.rglob("*"):
                    if is_cancelled and is_cancelled():
                        raise InterruptedError("TAR creation cancelled.")
                    if fpath.is_symlink():
                        continue
                    arcname = str(fpath.relative_to(source))
                    tf.add(fpath, arcname=arcname, recursive=False)
            else:
                tf.add(source, arcname=source.name)

        return out_tar

    def create_gz(
        self,
        source: Path,
        out_gz: Path,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """Compress a single file with GZip."""
        if source.is_dir():
            raise ValueError("GZip compresses single files; use TAR.GZ or ZIP for directories.")
        comp_level = int(settings.get("compresslevel", 6))
        with open(source, "rb") as src_f, gzip.open(out_gz, "wb", compresslevel=comp_level) as dst_f:
            shutil.copyfileobj(src_f, dst_f)
        return out_gz

    def create_7z(
        self,
        source: Path,
        out_7z: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """Create a 7z archive using py7zr."""
        import py7zr
        with py7zr.SevenZipFile(out_7z, "w") as sz:
            if source.is_dir():
                sz.writeall(source, arcname="")
            else:
                sz.write(source, arcname=source.name)
        return out_7z
