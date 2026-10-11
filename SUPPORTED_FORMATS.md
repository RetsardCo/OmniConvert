# OmniConvert — Supported Formats & Capabilities Matrix

This document tracks all format routes and operations in OmniConvert, detailing their current implementation and test status.

## Status Legend
- **Planned**: In architectural roadmap.
- **Implemented**: Engine logic and registry capabilities written.
- **Tested**: Verified via automated unit/integration tests.
- **Unavailable**: Requires external dependency (e.g. FFmpeg, LibreOffice, Tesseract) not found on host.

---

## 1. Image Conversions (Pillow Engine)

| Source Format | Target Format | Operation | Status | Dependencies |
|---|---|---|---|---|
| PNG | JPEG | Convert image format (transparency filled with white/black) | Planned (Phase 5) | Pillow |
| JPEG | PNG | Convert image format | Planned (Phase 5) | Pillow |
| WEBP | PNG, JPEG | Convert image format | Planned (Phase 5) | Pillow |
| BMP | PNG, JPEG | Convert image format | Planned (Phase 5) | Pillow |
| PNG, JPEG | ICO | Multi-resolution icon generation | Planned (Phase 5) | Pillow |
| PNG, JPEG | PDF | Wrap image in PDF page | Planned (Phase 5) | Pillow / pypdf |

---

## 2. Document & PDF Operations (PyPDF / Text Engines)

| Source Format | Target Format | Operation | Status | Dependencies |
|---|---|---|---|---|
| PDF | TXT | Extract plain text from PDF pages | Planned (Phase 6) | pypdf |
| PDF | PDF | Merge PDF files | Planned (Phase 6) | pypdf |
| TXT | PDF | Wrap text into formatted PDF | Planned (Phase 6) | pypdf / ReportLab |
| CSV | JSON | Tabular data serialization | Planned (Phase 8) | Standard library |
| JSON | CSV | Flatten structured data to CSV | Planned (Phase 8) | Standard library |

---

## 3. Media Operations (FFmpeg Engine)

*FFmpeg must be installed and in PATH for these operations.*

| Source Format | Target Format | Operation | Status | Dependencies |
|---|---|---|---|---|
| MP4, MKV, AVI, MOV | MP3 | Audio extraction & encoding | Planned (Phase 4) | FFmpeg |
| MP4, MKV, AVI, MOV | WAV | Uncompressed audio extraction | Planned (Phase 4) | FFmpeg |
| WAV | MP3 | Transcoding audio | Planned (Phase 4) | FFmpeg |
| MP4, MKV, MOV | MP4 | Video transcoding / compression (H.264/AAC) | Planned (Phase 4) | FFmpeg |
| MP4 | GIF | Video to animated GIF conversion | Planned (Phase 4) | FFmpeg |

---

## 4. Archive Operations (Python Builtin)

| Source Format | Target Format | Operation | Status | Dependencies |
|---|---|---|---|---|
| ZIP | Extracted Files | Safe extraction with path traversal safeguards | Planned (Phase 7) | Standard library |
| Directory / Files | ZIP | Deflate archive compression | Planned (Phase 7) | Standard library |
| TAR / TAR.GZ | Extracted Files | Safe archive extraction | Planned (Phase 7) | Standard library |

---

## 5. Binary Inspection (Static Analysis)

| Source Format | Target Format | Operation | Status | Dependencies |
|---|---|---|---|---|
| Any binary (EXE, DLL, etc.) | TXT | Printable ASCII/Unicode string extraction | Planned (Phase 9) | Standard library |
| Any file | JSON / TXT | Cryptographic hashes & metadata inspection | Planned (Phase 9) | Standard library |
