"""Startup and CLI dependency inspection report for OmniConvert."""

import sys
from pathlib import Path

# Ensure src is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from omniconvert.core.registry import CapabilityRegistry
from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.engines.office_detector import LibreOfficeDetector
from omniconvert.engines.ocr_engine import TesseractDetector
from omniconvert.engines.speech_engine import SpeechDetector


def generate_dependency_report() -> dict:
    reg = CapabilityRegistry()
    ff = FFmpegDetector().detect()
    lo = LibreOfficeDetector().detect()
    ocr = TesseractDetector().detect()
    sp = SpeechDetector().detect()

    all_caps = reg.get_all(only_available=False)
    avail_caps = reg.get_all(only_available=True)

    return {
        "total_registered_operations": len(all_caps),
        "available_operations": len(avail_caps),
        "unavailable_operations": len(all_caps) - len(avail_caps),
        "engines": {
            "pillow": reg.is_engine_available("pillow"),
            "pypdf_pymupdf_pdf2docx": reg.is_engine_available("pypdf"),
            "office_docx_xlsx_pptx": reg.is_engine_available("libreoffice"),
            "libreoffice_binary": lo.is_available,
            "ffmpeg": ff.is_available,
            "ffmpeg_version": ff.ffmpeg_version,
            "archive_zip_tar_7z": reg.is_engine_available("archive"),
            "data_json_yaml_xml_csv": reg.is_engine_available("data"),
            "binary_static_inspector": reg.is_engine_available("binary"),
            "tts_local_sapi5": sp.tts_available,
            "ocr_tesseract_optional": ocr.is_available,
            "asr_whisper_optional": sp.asr_available,
        }
    }


if __name__ == "__main__":
    import json
    report = generate_dependency_report()
    print(json.dumps(report, indent=2))
