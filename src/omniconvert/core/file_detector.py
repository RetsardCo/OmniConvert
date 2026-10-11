"""File format detection and magic byte signature inspection."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import os


@dataclass
class FileMetadata:
    path: Path
    filename: str
    extension: str
    size_bytes: int
    detected_mime: str
    detected_format: str
    category: str
    is_readable: bool
    is_empty: bool
    error: Optional[str] = None

    @property
    def formatted_size(self) -> str:
        """Format size in human-readable units."""
        if self.size_bytes < 1024:
            return f"{self.size_bytes} B"
        elif self.size_bytes < 1024 * 1024:
            return f"{self.size_bytes / 1024:.1f} KB"
        elif self.size_bytes < 1024 * 1024 * 1024:
            return f"{self.size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{self.size_bytes / (1024 * 1024 * 1024):.2f} GB"


# Magic byte signatures (offset, signature_bytes, format, category, mime)
SIGNATURES = [
    # Images
    (0, b"\x89PNG\r\n\x1a\n", "png", "image", "image/png"),
    (0, b"\xff\xd8\xff", "jpeg", "image", "image/jpeg"),
    (0, b"GIF87a", "gif", "image", "image/gif"),
    (0, b"GIF89a", "gif", "image", "image/gif"),
    (0, b"BM", "bmp", "image", "image/bmp"),
    (0, b"II*\x00", "tiff", "image", "image/tiff"),
    (0, b"MM\x00*", "tiff", "image", "image/tiff"),
    (0, b"\x00\x00\x01\x00", "ico", "image", "image/x-icon"),

    # PDF
    (0, b"%PDF-", "pdf", "document", "application/pdf"),
    (0, b"{\\rtf", "rtf", "document", "application/rtf"),

    # Audio / Video
    (0, b"ID3", "mp3", "audio", "audio/mpeg"),
    (0, b"\xff\xfb", "mp3", "audio", "audio/mpeg"),
    (0, b"\xff\xf3", "mp3", "audio", "audio/mpeg"),
    (0, b"\xff\xf2", "mp3", "audio", "audio/mpeg"),
    (0, b"\xff\xf1", "aac", "audio", "audio/aac"),
    (0, b"\xff\xf9", "aac", "audio", "audio/aac"),
    (0, b"fLaC", "flac", "audio", "audio/flac"),
    (0, b"OggS", "ogg", "audio", "audio/ogg"),
    (0, b"RIFF", "riff", "container", "application/octet-stream"),
    (4, b"ftyp", "mp4", "video", "video/mp4"),
    (0, b"\x1aE\xdf\xa3", "mkv", "video", "video/x-matroska"),

    # Archives
    (0, b"PK\x03\x04", "zip", "archive", "application/zip"),
    (0, b"\x1f\x8b\x08", "gz", "archive", "application/gzip"),
    (0, b"7z\xbc\xaf\x27\x1c", "7z", "archive", "application/x-7z-compressed"),
    (0, b"Rar!\x1a\x07\x00", "rar", "archive", "application/x-rar-compressed"),
    (0, b"Rar!\x1a\x07\x01\x00", "rar", "archive", "application/x-rar-compressed"),

    # Executables / Binaries
    (0, b"MZ", "exe", "binary", "application/x-msdownload"),
]

EXTENSION_MAP = {
    # Documents / Text
    "txt": ("txt", "text", "text/plain"),
    "log": ("txt", "text", "text/plain"),
    "csv": ("csv", "data", "text/csv"),
    "tsv": ("tsv", "data", "text/tab-separated-values"),
    "json": ("json", "data", "application/json"),
    "yaml": ("yaml", "data", "application/x-yaml"),
    "yml": ("yaml", "data", "application/x-yaml"),
    "xml": ("xml", "data", "application/xml"),
    "md": ("markdown", "text", "text/markdown"),
    "markdown": ("markdown", "text", "text/markdown"),
    "html": ("html", "document", "text/html"),
    "htm": ("html", "document", "text/html"),
    "rtf": ("rtf", "document", "application/rtf"),
    "docx": ("docx", "document", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "doc": ("doc", "document", "application/msword"),
    "odt": ("odt", "document", "application/vnd.oasis.opendocument.text"),
    "xlsx": ("xlsx", "document", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    "xls": ("xls", "document", "application/vnd.ms-excel"),
    "pptx": ("pptx", "document", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
    "odp": ("odp", "document", "application/vnd.oasis.opendocument.presentation"),
    "pdf": ("pdf", "document", "application/pdf"),

    # Images
    "png": ("png", "image", "image/png"),
    "jpg": ("jpeg", "image", "image/jpeg"),
    "jpeg": ("jpeg", "image", "image/jpeg"),
    "webp": ("webp", "image", "image/webp"),
    "bmp": ("bmp", "image", "image/bmp"),
    "ico": ("ico", "image", "image/x-icon"),
    "tiff": ("tiff", "image", "image/tiff"),
    "tif": ("tiff", "image", "image/tiff"),
    "gif": ("gif", "image", "image/gif"),
    "svg": ("svg", "image", "image/svg+xml"),

    # Audio
    "mp3": ("mp3", "audio", "audio/mpeg"),
    "wav": ("wav", "audio", "audio/wav"),
    "flac": ("flac", "audio", "audio/flac"),
    "aac": ("aac", "audio", "audio/aac"),
    "ogg": ("ogg", "audio", "audio/ogg"),
    "opus": ("opus", "audio", "audio/opus"),
    "m4a": ("m4a", "audio", "audio/mp4"),
    "aiff": ("aiff", "audio", "audio/aiff"),
    "aif": ("aiff", "audio", "audio/aiff"),
    "wma": ("wma", "audio", "audio/x-ms-wma"),

    # Video
    "mp4": ("mp4", "video", "video/mp4"),
    "mkv": ("mkv", "video", "video/x-matroska"),
    "avi": ("avi", "video", "video/x-msvideo"),
    "mov": ("mov", "video", "video/quicktime"),
    "webm": ("webm", "video", "video/webm"),
    "wmv": ("wmv", "video", "video/x-ms-wmv"),
    "flv": ("flv", "video", "video/x-flv"),
    "mpeg": ("mpeg", "video", "video/mpeg"),
    "mpg": ("mpeg", "video", "video/mpeg"),

    # Archives
    "zip": ("zip", "archive", "application/zip"),
    "tar": ("tar", "archive", "application/x-tar"),
    "tgz": ("tar", "archive", "application/gzip"),
    "gz": ("gz", "archive", "application/gzip"),
    "7z": ("7z", "archive", "application/x-7z-compressed"),

    # Binaries
    "exe": ("exe", "binary", "application/x-msdownload"),
    "dll": ("dll", "binary", "application/x-msdownload"),
    "sys": ("sys", "binary", "application/octet-stream"),
    "bin": ("bin", "binary", "application/octet-stream"),
}


def inspect_file(file_path: Path | str) -> FileMetadata:
    """
    Inspect a file and detect format using magic bytes where possible,
    falling back to extension-based inference. Reads at most 64 bytes for signature.
    """
    path = Path(file_path).resolve()
    filename = path.name
    ext = path.suffix.lower().lstrip(".")

    if not path.exists():
        return FileMetadata(
            path=path,
            filename=filename,
            extension=ext,
            size_bytes=0,
            detected_mime="unknown",
            detected_format="unknown",
            category="unknown",
            is_readable=False,
            is_empty=True,
            error=f"File does not exist: {path}"
        )

    if path.is_dir():
        return FileMetadata(
            path=path,
            filename=filename,
            extension="dir",
            size_bytes=0,
            detected_mime="inode/directory",
            detected_format="dir",
            category="directory",
            is_readable=True,
            is_empty=False,
            error=None
        )

    try:
        size = path.stat().st_size
    except Exception as e:
        return FileMetadata(
            path=path,
            filename=filename,
            extension=ext,
            size_bytes=0,
            detected_mime="unknown",
            detected_format="unknown",
            category="unknown",
            is_readable=False,
            is_empty=True,
            error=f"Cannot stat file: {e}"
        )

    if size == 0:
        return FileMetadata(
            path=path,
            filename=filename,
            extension=ext,
            size_bytes=0,
            detected_mime="application/x-empty",
            detected_format=ext or "empty",
            category="empty",
            is_readable=True,
            is_empty=True,
            error=None
        )

    # Read up to 64 bytes to inspect magic signatures
    header = b""
    try:
        with open(path, "rb") as f:
            header = f.read(64)
    except Exception as e:
        return FileMetadata(
            path=path,
            filename=filename,
            extension=ext,
            size_bytes=size,
            detected_mime="unknown",
            detected_format="unknown",
            category="unknown",
            is_readable=False,
            is_empty=False,
            error=f"Unreadable file: {e}"
        )

    detected_format = None
    detected_category = None
    detected_mime = None

    # 1. Handle RIFF special container (WAV, WEBP, AVI) and FORM (AIFF)
    if header.startswith(b"RIFF") and len(header) >= 12:
        riff_type = header[8:12]
        if riff_type == b"WAVE":
            detected_format = "wav"
            detected_category = "audio"
            detected_mime = "audio/wav"
        elif riff_type == b"WEBP":
            detected_format = "webp"
            detected_category = "image"
            detected_mime = "image/webp"
        elif riff_type == b"AVI ":
            detected_format = "avi"
            detected_category = "video"
            detected_mime = "video/x-msvideo"
    elif header.startswith(b"FORM") and len(header) >= 12 and header[8:12] in (b"AIFF", b"AIFC"):
        detected_format = "aiff"
        detected_category = "audio"
        detected_mime = "audio/aiff"

    # 2. Handle OpenXML / ODF ZIP-packaged Office Documents (.docx, .xlsx, .pptx, .odt, .odp)
    if not detected_format and header.startswith(b"PK\x03\x04") and ext in ("docx", "xlsx", "pptx", "odt", "odp"):
        detected_format, detected_category, detected_mime = EXTENSION_MAP[ext]

    # 3. Handle ISO Base Media File Format (ftyp: mp4, mov, m4a)
    if not detected_format and len(header) >= 12 and header[4:8] == b"ftyp":
        brand = header[8:12]
        if brand == b"M4A " or ext == "m4a":
            detected_format, detected_category, detected_mime = EXTENSION_MAP["m4a"]
        elif brand == b"qt  " or ext == "mov":
            detected_format, detected_category, detected_mime = EXTENSION_MAP["mov"]
        else:
            detected_format, detected_category, detected_mime = ("mp4", "video", "video/mp4")

    # 4. Handle .tar.gz / .tgz compound archive extension
    if not detected_format and header.startswith(b"\x1f\x8b\x08") and (filename.lower().endswith(".tar.gz") or ext == "tgz"):
        detected_format, detected_category, detected_mime = ("tar", "archive", "application/gzip")

    # 5. Match standard Magic Signatures
    if not detected_format:
        for offset, sig, fmt, cat, mime in SIGNATURES:
            if len(header) >= offset + len(sig):
                if header[offset:offset + len(sig)] == sig:
                    if fmt == "ogg" and ext == "opus":
                        detected_format, detected_category, detected_mime = EXTENSION_MAP["opus"]
                    elif fmt == "mkv" and ext == "webm":
                        detected_format, detected_category, detected_mime = EXTENSION_MAP["webm"]
                    elif fmt == "exe" and ext == "dll":
                        detected_format, detected_category, detected_mime = EXTENSION_MAP["dll"]
                    else:
                        detected_format = fmt
                        detected_category = cat
                        detected_mime = mime
                    break

    # 6. Check if text/plain or markup
    if not detected_format and ext in EXTENSION_MAP:
        exp_fmt, exp_cat, exp_mime = EXTENSION_MAP[ext]
        if exp_cat in ("text", "data", "document"):
            try:
                header.decode("utf-8")
                detected_format = exp_fmt
                detected_category = exp_cat
                detected_mime = exp_mime
            except UnicodeDecodeError:
                pass

    # 7. Fallback to extension map
    if not detected_format and ext in EXTENSION_MAP:
        detected_format, detected_category, detected_mime = EXTENSION_MAP[ext]

    if not detected_format:
        detected_format = ext or "unknown"
        detected_category = "binary"
        detected_mime = "application/octet-stream"

    return FileMetadata(
        path=path,
        filename=filename,
        extension=ext,
        size_bytes=size,
        detected_mime=detected_mime,
        detected_format=detected_format,
        category=detected_category,
        is_readable=True,
        is_empty=False,
        error=None
    )
