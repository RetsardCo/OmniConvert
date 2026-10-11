"""Output file verification and integrity checks."""

from pathlib import Path
from typing import Tuple, Optional
import json


def validate_output(
    target_path: Path,
    expected_format: str,
    validation_type: str = "existence_and_size"
) -> Tuple[bool, Optional[str]]:
    """
    Validate that conversion output exists, is non-empty, and satisfies format-specific checks.
    """
    if not target_path.exists():
        return False, f"Output file does not exist at expected destination: {target_path}"

    fmt = expected_format.lower().lstrip(".")

    # Directory output validation (e.g. archive extraction or GIF frame extraction)
    if target_path.is_dir() or fmt == "dir":
        if not target_path.is_dir():
            return False, f"Expected output directory but found file: {target_path}"
        if not any(target_path.iterdir()):
            return False, f"Extracted output directory is empty: {target_path}"
        return True, None

    try:
        size = target_path.stat().st_size
        if size == 0:
            return False, f"Output file is empty (0 bytes): {target_path}"
    except Exception as e:
        return False, f"Could not inspect output file size: {e}"

    # Format-specific validation
    if fmt in ("png", "jpg", "jpeg", "webp", "bmp", "ico", "tiff", "tif", "gif"):
        try:
            from PIL import Image
            with Image.open(target_path) as img:
                img.verify()
        except Exception as e:
            return False, f"Generated image is invalid or corrupt: {e}"

    elif fmt == "pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(str(target_path))
            if len(reader.pages) == 0:
                return False, "Generated PDF contains no pages."
        except Exception as e:
            return False, f"Generated PDF could not be parsed: {e}"

    elif fmt == "docx":
        try:
            import docx
            doc = docx.Document(str(target_path))
            if doc is None:
                return False, "Generated DOCX document could not be loaded."
        except Exception as e:
            return False, f"Generated DOCX document is invalid: {e}"

    elif fmt == "xlsx":
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(target_path), read_only=True)
            wb.close()
        except Exception as e:
            return False, f"Generated XLSX workbook is invalid: {e}"

    elif fmt == "json":
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            return False, f"Generated JSON is malformed: {e}"

    elif fmt in ("yaml", "yml"):
        try:
            import yaml
            with open(target_path, "r", encoding="utf-8") as f:
                yaml.safe_load(f)
        except Exception as e:
            return False, f"Generated YAML is malformed: {e}"

    elif fmt == "xml":
        try:
            import defusedxml.ElementTree as ET
            ET.parse(str(target_path))
        except Exception as e:
            return False, f"Generated XML is malformed: {e}"

    elif fmt == "csv":
        try:
            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(1024)
                if not content.strip():
                    return False, "Generated CSV has no content."
        except Exception as e:
            return False, f"Generated CSV could not be read: {e}"

    elif fmt == "zip":
        try:
            import zipfile
            with zipfile.ZipFile(target_path, "r") as z:
                if z.testzip() is not None:
                    return False, "Generated ZIP contains corrupt entries."
        except Exception as e:
            return False, f"Generated ZIP archive is invalid: {e}"

    elif fmt in ("tar", "tar.gz", "tgz"):
        try:
            import tarfile
            with tarfile.open(target_path, "r:*") as tf:
                tf.getnames()
        except Exception as e:
            return False, f"Generated TAR archive is invalid: {e}"

    elif fmt == "7z":
        try:
            import py7zr
            with py7zr.SevenZipFile(target_path, "r") as sz:
                sz.list()
        except Exception as e:
            return False, f"Generated 7Z archive is invalid: {e}"

    elif fmt == "gz":
        try:
            import gzip
            with gzip.open(target_path, "rb") as gz:
                gz.read(64)
        except Exception as e:
            return False, f"Generated GZ archive is invalid: {e}"

    elif fmt in ("mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "aiff", "mp4", "mkv", "avi", "mov", "webm", "gif"):
        try:
            from omniconvert.engines.media_inspector import MediaInspector
            inspector = MediaInspector()
            if inspector.ffprobe_path and inspector.ffprobe_path.exists():
                res = inspector.inspect(target_path)
                if not res.is_valid:
                    return False, f"Generated media is corrupt: {res.error_message}"
                if fmt in ("mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "aiff") and not res.has_audio:
                    return False, "Generated audio file contains no readable audio stream."
                if fmt in ("mp4", "mkv", "avi", "mov", "webm") and not res.has_video:
                    return False, "Generated video file contains no readable video stream."
        except Exception as e:
            return False, f"Could not verify media output stream: {e}"

    return True, None
