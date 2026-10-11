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

    try:
        size = target_path.stat().st_size
        if size == 0:
            return False, f"Output file is empty (0 bytes): {target_path}"
    except Exception as e:
        return False, f"Could not inspect output file size: {e}"

    fmt = expected_format.lower().lstrip(".")

    # Format-specific validation
    if fmt in ("png", "jpg", "jpeg", "webp", "bmp", "ico", "tiff"):
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

    elif fmt == "json":
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            return False, f"Generated JSON is malformed: {e}"

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

    return True, None
