# OmniConvert — Verified Supported Formats & Capability Matrix

All conversions listed below are **100% local and offline** (no cloud APIs or external file uploads) and are verified by automated test suites (`tests/unit/`).

---

## 1. Document & Office Conversions

| Operation ID | Source Formats | Target Format | Engine | Quality / Detail Controls | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pdf.to_docx` | `pdf` | `docx` | `pypdf` (`pdf2docx` + `PyMuPDF` + `python-docx`) | Lossless / Exact, High, Balanced, Compact | Reconstructs editable paragraphs, tables, and embedded images. Scanned image-only PDFs are embedded as high-DPI page images unless OCR is used. |
| `office.docx_to_pdf` | `docx` | `pdf` | `office` (`reportlab` / LibreOffice) | Lossless / Exact (300 DPI), High, Balanced, Compact | Converts headings, paragraphs, tables, and embedded images into a multi-page PDF. Uses LibreOffice automatically if installed for complex page rules. |
| `office.to_pdf` | `docx`, `xlsx`, `pptx`, `odt`, `ods`, `odp`, `rtf` | `pdf` | `office` | Quality preset | Offline pure-Python rendering (`reportlab`/`openpyxl`/`python-pptx`/`python-docx`) with automatic LibreOffice escalation when available. |
| `office.docx_to_txt` | `docx` | `txt` | `office` | — | Extracts paragraphs and table cells to UTF-8 text. |
| `office.docx_to_html` | `docx` | `html` | `office` | — | Exports styled semantic HTML5 document with tables. |
| `office.docx_to_md` | `docx` | `md` | `office` | — | Converts Word headings, paragraphs, and tables to Markdown. |
| `office.text_to_docx` | `txt`, `md`, `html` | `docx` | `office` | — | Generates an editable `.docx` document from plain text, Markdown, or HTML. |
| `office.text_to_pdf` | `txt`, `md`, `html` | `pdf` | `office` | — | Generates a clean multi-page PDF document from plain text, Markdown, or HTML. |
| `office.xlsx_to_csv` | `xlsx` | `csv` | `office` | Sheet selection | Exports worksheet rows to UTF-8 CSV (evaluates cached formula values). |
| `office.xlsx_to_json` | `xlsx` | `json` | `office` | — | Exports all sheets or header-mapped records to structured JSON. |
| `office.xlsx_to_html` | `xlsx` | `html` | `office` | — | Exports worksheets to styled HTML tables. |
| `office.csv_to_xlsx` | `csv` | `xlsx` | `office` | — | Converts CSV tabular data into a formatted Excel `.xlsx` workbook with bold headers. |
| `office.pptx_to_txt` | `pptx` | `txt` | `office` | — | Extracts slide text, table cells, and speaker notes per slide. |
| `pdf.to_png` | `pdf` | `png` | `pypdf` (`PyMuPDF`) | DPI (72–600, default 300) | Renders single or multi-page PDF into high-DPI lossless PNG. |
| `pdf.to_jpeg` | `pdf` | `jpeg` | `pypdf` (`PyMuPDF`) | DPI (72–600), Quality (1–100) | Renders PDF pages to JPEG (uses 4:4:4 chroma subsampling at 100% quality). |
| `pdf.to_html` | `pdf` | `html` | `pypdf` (`PyMuPDF`) | — | Converts PDF pages to structured HTML. |
| `pdf.to_md` | `pdf` | `md` | `pypdf` (`PyMuPDF`) | — | Extracts PDF pages into Markdown sections. |
| `pdf.extract_text` | `pdf` | `txt` | `pypdf` | Password support | Extracts embedded text streams; scanned PDFs without a text layer require `ocr.image_to_txt`. |
| `pdf.to_json` | `pdf` | `json` | `pypdf` | Password support | Exports document metadata, page dimensions, and per-page text to JSON. |
| `image.to_pdf` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `tiff`, `tif` | `pdf` | `pypdf` (`PyMuPDF` / `Pillow`) | DPI (72–600, default 300) | Wraps raster images into a standard PDF page at exact physical DPI. |

---

## 2. Image & Graphics Conversions

| Operation ID | Source Formats | Target Format | Engine | Quality / Detail Controls | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `image.to_jpeg` | `png`, `webp`, `bmp`, `tiff`, `tif`, `gif`, `ico`, `svg` | `jpeg` | `pillow` | Quality (1–100, default 100), Subsampling (`4:4:4` at Lossless/Exact), Resize, Rotate, Crop, BG Color | At **Lossless / Exact Quality (100%)**, encodes with `quality=100, subsampling=0 (4:4:4)` for zero chroma subsampling loss. Flattens alpha channel onto configurable background color. |
| `image.to_png` | `jpeg`, `jpg`, `webp`, `bmp`, `tiff`, `tif`, `gif`, `ico`, `svg` | `png` | `pillow` | Lossless compression, Resize, Rotate, Crop, Strip Metadata | 100% lossless pixel preservation including RGBA transparency. |
| `image.to_webp` | `png`, `jpeg`, `jpg`, `bmp`, `tiff`, `tif`, `gif`, `svg` | `webp` | `pillow` | Quality (1–100), Lossless WebP toggle, Resize, Rotate, Crop | Supports true lossless WebP (`lossless=True` in Lossless/Exact preset) as well as lossy WebP. |
| `image.to_bmp` | `png`, `jpeg`, `jpg`, `webp`, `tiff`, `tif`, `gif`, `svg` | `bmp` | `pillow` | Resize, Rotate, Crop | Uncompressed raster bitmap output. |
| `image.to_tiff` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `gif`, `svg` | `tiff` | `pillow` | Lossless LZW / Raw compression, Resize, Rotate | Archival lossless TIFF output. |
| `image.to_gif` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `svg` | `gif` | `pillow` | Resize, Rotate | 256-color quantized GIF output. |
| `image.to_ico` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `svg` | `ico` | `pillow` | Multi-resolution icon bundle | Generates multi-resolution Windows `.ico` (`16x16` through `256x256`). |

---

## 3. Audio & Video Media Conversions (FFmpeg)

| Operation ID | Source Formats | Target Format | Engine | Quality / Detail Controls | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `audio.to_mp3` | `wav`, `flac`, `aac`, `m4a`, `ogg`, `opus`, `aiff`, `mp3` | `mp3` | `ffmpeg` | Bitrate (`320k`, `256k`, `192k`, `128k`, `96k`), Sample Rate, Channels | Uses `libmp3lame` (`-b:a 320k -q:a 0` in Lossless/Exact preset). |
| `audio.to_wav` | `mp3`, `flac`, `aac`, `m4a`, `ogg`, `opus`, `aiff`, `wav` | `wav` | `ffmpeg` | Bit Depth (`16`-bit, `24`-bit, `32`-bit float PCM), Sample Rate, Channels | Uncompressed lossless PCM WAV output. |
| `audio.to_flac` | `mp3`, `wav`, `aac`, `m4a`, `ogg`, `opus`, `aiff`, `flac` | `flac` | `ffmpeg` | Lossless compression level 8, Sample Rate, Channels | Archival lossless FLAC compression. |
| `audio.to_aac` | `mp3`, `wav`, `flac`, `m4a`, `ogg`, `opus`, `aiff` | `aac` | `ffmpeg` | Bitrate (`320k`–`96k`), Sample Rate, Channels | Raw ADTS AAC audio stream. |
| `audio.to_m4a` | `mp3`, `wav`, `flac`, `aac`, `ogg`, `opus`, `aiff` | `m4a` | `ffmpeg` | Bitrate (`320k`–`96k`) or **Lossless ALAC** toggle, Sample Rate, Channels | Supports both high-bitrate AAC and Apple Lossless (`alac`) in MP4 container. |
| `audio.to_ogg` | `mp3`, `wav`, `flac`, `aac`, `m4a`, `opus`, `aiff` | `ogg` | `ffmpeg` | Quality scale (`-q:a 9` at 320k down to `-q:a 2`), Sample Rate, Channels | Ogg Vorbis audio encoding (`libvorbis`). |
| `audio.to_opus` | `mp3`, `wav`, `flac`, `aac`, `m4a`, `ogg`, `aiff` | `opus` | `ffmpeg` | Bitrate (`320k`/`256k`–`96k`), Channels | High-efficiency Opus audio encoding (`libopus`). |
| `audio.to_aiff` | `mp3`, `wav`, `flac`, `aac`, `m4a`, `ogg`, `opus` | `aiff` | `ffmpeg` | Sample Rate, Channels | Uncompressed big-endian PCM AIFF audio. |
| `video.extract_mp3` | `mp4`, `mkv`, `webm`, `mov`, `avi` | `mp3` | `ffmpeg` | Bitrate (`320k`–`96k`) | Requires source video to contain an audio stream. |
| `video.extract_wav` | `mp4`, `mkv`, `webm`, `mov`, `avi` | `wav` | `ffmpeg` | Bit Depth (`16`, `24`, `32`) | Extracts uncompressed PCM WAV audio from video. |
| `video.extract_flac` | `mp4`, `mkv`, `webm`, `mov`, `avi` | `flac` | `ffmpeg` | Lossless | Extracts lossless FLAC audio from video. |
| `video.extract_m4a` | `mp4`, `mkv`, `webm`, `mov`, `avi` | `m4a` | `ffmpeg` | Bitrate / Lossless ALAC | Extracts M4A audio track from video. |
| `video.to_mp4` | `mkv`, `webm`, `mov`, `avi`, `mp4` | `mp4` | `ffmpeg` | CRF (`0`–`51`, default `14` in Lossless/Exact), Preset (`slow`/`medium`/`fast`), Scale Height, FPS, Audio Bitrate | H.264 (`libx264`) + AAC with `+faststart`. |
| `video.to_mkv` | `mp4`, `webm`, `mov`, `avi` | `mkv` | `ffmpeg` | CRF, Preset, Scale Height, FPS, Audio Bitrate | Matroska container transcoding. |
| `video.to_webm` | `mp4`, `mkv`, `mov`, `avi` | `webm` | `ffmpeg` | CRF, Preset, Scale Height, FPS, Audio Bitrate | VP9 (`libvpx-vp9`) + Opus/Vorbis WebM encoding. |
| `video.to_mov` | `mp4`, `mkv`, `webm`, `avi` | `mov` | `ffmpeg` | CRF, Preset, Scale Height, FPS, Audio Bitrate | Apple QuickTime MOV output. |
| `video.to_gif` | `mp4`, `mkv`, `webm`, `mov`, `avi` | `gif` | `ffmpeg` | FPS (`5`–`30`), Width (`160`–`1920`) | Lanczos-scaled animated GIF generation. |
| `video.extract_subtitles` | `mp4`, `mkv`, `webm`, `mov` | `srt` | `ffmpeg` | — | Extracts first text subtitle stream to SubRip `.srt`. |
| `video.metadata_to_json` | `mp4`, `mkv`, `webm`, `mov`, `avi`, `mp3`, `wav`, `flac`, `m4a`, `ogg`, `opus` | `json` | `ffmpeg` | — | Exports container, video, audio, and subtitle stream telemetry via FFprobe. |

---

## 4. Structured Data, Archives, Speech, OCR & Binary Inspection

| Operation ID | Source Formats | Target Format | Engine | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- |
| `data.csv_to_json` / `data.json_to_csv` | `csv` <-> `json` | `json` / `csv` | `data` | Configurable delimiter and nested dictionary key flattening. |
| `data.json_to_yaml` / `data.yaml_to_json` | `json` <-> `yaml` | `yaml` / `json` | `data` | Safe YAML parsing and formatting (`pyyaml`). |
| `data.xml_to_json` / `data.json_to_xml` | `xml` <-> `json` | `json` / `xml` | `data` | XXE/entity-expansion hardened via `defusedxml`. |
| `data.txt_normalize` | `txt`, `md`, `csv`, `json`, `yaml`, `xml`, `html` | `txt` | `data` | Encoding normalization (`utf-8`, `utf-8-sig`, `utf-16`, `latin-1`) & line-ending conversion (`LF`/`CRLF`). |
| `data.csv_to_mp4` | `csv` | `mp4` | `ffmpeg` | Renders animated bar-chart visualization frames from numeric CSV columns and encodes to H.264 MP4. |
| `archive.extract` | `zip`, `tar`, `gz`, `tgz`, `7z` | `dir` | `archive` | Enforces Zip-Slip path traversal blocking, symlink rejection, and 2 GB / 200:1 decompression bomb limits. |
| `archive.list_to_json` | `zip`, `tar`, `gz`, `tgz`, `7z` | `json` | `archive` | Inspects archive entries, sizes, and safety status without extracting. |
| `archive.create_zip` / `archive.create_tar_gz` / `archive.create_7z` | `dir`, `txt`, `csv`, `json`, `pdf`, `png`, `jpeg`, `docx`, `xlsx`, `mp3`, `wav`, `mp4` | `zip` / `tgz` / `7z` | `archive` | Packages files or directories and validates the resulting archive. |
| `archive.to_zip` / `archive.to_tar_gz` / `archive.to_7z` | `zip`, `tar`, `gz`, `tgz`, `7z` | `zip` / `tgz` / `7z` | `archive` | Safely extracts and repacks between archive formats. |
| `tts.text_to_wav` | `txt`, `md` | `wav` | `tts` | Offline speech synthesis using Windows SAPI5 (`pyttsx3`) with deterministic PCM WAV fallback. |
| `ocr.image_to_txt` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `tiff`, `tif` | `txt` | `ocr` | Requires local Tesseract OCR binary (`tesseract.exe`). Hidden when Tesseract is absent. |
| `asr.audio_to_txt` | `wav`, `mp3`, `flac`, `m4a`, `ogg` | `txt` | `asr` | Requires local Whisper CLI/library. Hidden when absent. |
| `binary.inspect_to_json` | `exe`, `dll`, `bin`, `so`, `dylib`, `pdf`, `zip`, `png`, `mp4` | `json` | `binary` | Static inspection only (MD5/SHA-1/SHA-256, Shannon entropy, PE headers). Does NOT decompile binaries. |
| `binary.extract_strings` | `exe`, `dll`, `bin`, `so`, `dylib` | `txt` | `binary` | Extracts printable ASCII and UTF-16LE strings. |
| `binary.hex_dump` | `exe`, `dll`, `bin`, `so`, `dylib` | `txt` | `binary` | Generates formatted offset + hex + ASCII dump. |
| `workflow.archive_to_pdf` | `zip`, `tar`, `gz`, `tgz`, `7z` | `pdf` | `workflow` | Safely extracts eligible images, PDFs, text, and Word docs from an archive and merges them into one combined PDF. |
