# OmniConvert — Verified Supported Formats & Capability Matrix

All conversions listed below are **100% local and offline** (no cloud APIs or external file uploads) and are verified by automated test suites (`tests/unit/`). Every Operation ID below corresponds directly to a registered `Capability` in [`src/omniconvert/core/registry.py`](src/omniconvert/core/registry.py).

---

## 1. Document, PDF & Office Conversions

| Operation ID | Source Formats | Target Format | Engine | Quality / Detail Controls | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pdf.to_docx` | `pdf` | `docx` | `pypdf` (`pdf2docx` + `PyMuPDF` + `python-docx`) | Lossless / Exact, High, Balanced, Compact | Reconstructs editable paragraphs, tables, and embedded images. Scanned image-only PDFs are embedded as high-DPI page images unless OCR is used. |
| `pdf.extract_pages` | `pdf` | `pdf` | `pypdf` | Start Page (`1`..N), End Page (`0`=Last) | Extracts or splits a page range from a PDF into a new PDF document. |
| `office.to_pdf` | `docx`, `doc`, `pptx`, `xlsx`, `odt`, `rtf`, `txt`, `markdown`, `html` | `pdf` | `libreoffice` (`reportlab` / `openpyxl` / `python-pptx` / LibreOffice) | Lossless / Exact (300 DPI), High, Balanced, Compact, Page Size (`letter`/`a4`) | Offline pure-Python rendering preserving interleaved paragraphs, tables, and images in document order, with automatic LibreOffice escalation when installed. |
| `office.to_docx` | `txt`, `markdown`, `html`, `rtf` | `docx` | `libreoffice` (`python-docx`) | — | Converts Plain Text, Markdown, or HTML into an editable Microsoft Word (`.docx`) document. |
| `office.to_txt` | `docx`, `doc`, `odt`, `rtf`, `pptx`, `xlsx`, `html`, `markdown` | `txt` | `libreoffice` | — | Extracts paragraphs, tables (in document order), slide text, and speaker notes to UTF-8 text. |
| `office.docx_to_html` | `docx`, `xlsx`, `markdown` | `html` | `libreoffice` | — | Exports styled semantic HTML5 document with interleaved headings, paragraphs, and tables. |
| `office.docx_to_md` | `docx`, `html` | `md` | `libreoffice` | — | Converts Word headings, paragraphs, and tables (formatted as Markdown pipe tables) to Markdown. |
| `office.xlsx_to_csv` | `xlsx` | `csv` | `libreoffice` (`openpyxl`) | — | Exports worksheet rows to UTF-8 CSV (evaluates cached formula values). |
| `office.xlsx_to_json` | `xlsx` | `json` | `libreoffice` (`openpyxl`) | — | Serializes Excel worksheet rows into a structured JSON array. |
| `office.to_xlsx` | `csv`, `tsv`, `json` | `xlsx` | `libreoffice` (`openpyxl`) | — | Creates an Excel (`.xlsx`) workbook from CSV, TSV, or JSON records with bold header cells. |
| `pdf.to_png` | `pdf` | `png` | `pypdf` (`PyMuPDF`) | Quality Preset, DPI (`72`–`600`, default `300`) | Renders single or multi-page PDF into high-DPI lossless PNG. |
| `pdf.to_jpeg` | `pdf` | `jpeg` | `pypdf` (`PyMuPDF`) | Quality Preset, DPI (`72`–`600`), Quality (`1`–`100`) | Renders PDF pages to JPEG (uses `4:4:4` chroma subsampling at 100% quality). |
| `pdf.to_html` | `pdf` | `html` | `pypdf` (`PyMuPDF`) | — | Converts PDF pages to structured HTML. |
| `pdf.to_md` | `pdf` | `md` | `pypdf` (`PyMuPDF`) | — | Extracts PDF pages into Markdown sections. |
| `pdf.extract_text` | `pdf` | `txt` | `pypdf` | Password support | Extracts embedded text streams; scanned PDFs without a text layer require `ocr.image_to_txt`. |
| `pdf.to_json` | `pdf` | `json` | `pypdf` | Password support | Exports document metadata and per-page text to JSON. |
| `image.to_pdf` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `tiff`, `tif` | `pdf` | `pypdf` (`Pillow`) | Quality Preset, DPI (`72`–`600`, default `300`) | Wraps raster images into a standard PDF page at exact physical DPI. |

---

## 2. Image & Graphics Conversions

| Operation ID | Source Formats | Target Format | Engine | Quality / Detail Controls | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `image.to_jpeg` | `png`, `webp`, `bmp`, `tiff`, `tif`, `gif`, `ico`, `svg`, `jpeg`, `jpg` | `jpeg` | `pillow` | Quality (`1`–`100`, default `100`), Subsampling (`4:4:4` at Lossless/Exact), Resize, Rotate, Crop, BG Color | At **Lossless / Exact Quality (100%)**, encodes with `quality=100, subsampling=0 (4:4:4)` for zero chroma subsampling loss. Flattens alpha channel onto configurable background color. |
| `image.to_png` | `jpeg`, `jpg`, `webp`, `bmp`, `tiff`, `tif`, `ico`, `gif`, `svg`, `png` | `png` | `pillow` | Lossless compression, Resize, Rotate, Crop | 100% lossless pixel preservation including RGBA transparency. |
| `image.to_webp` | `png`, `jpeg`, `jpg`, `bmp`, `tiff`, `tif`, `gif`, `svg` | `webp` | `pillow` | Quality (`1`–`100`), True Lossless WebP toggle (`default=True`), Resize, Rotate | Defaults to true lossless WebP (`lossless=True`) in Lossless/Exact mode; supports lossy WebP in Balanced/Compact modes. |
| `image.to_bmp` | `png`, `jpeg`, `jpg`, `webp`, `tiff`, `tif`, `gif`, `svg` | `bmp` | `pillow` | Resize, Rotate | Uncompressed Windows Bitmap output. |
| `image.to_tiff` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `gif`, `svg` | `tiff` | `pillow` | Lossless LZW compression | Archival lossless TIFF output. |
| `image.to_gif` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `tiff`, `tif`, `svg` | `gif` | `pillow` | — | 256-color palette GIF output. |
| `image.to_ico` | `png`, `jpeg`, `jpg`, `bmp`, `webp`, `svg` | `ico` | `pillow` | Multi-resolution icon bundle | Generates multi-resolution Windows `.ico` (`16x16` through `256x256`). |
| `image.extract_frames` | `gif` | `dir` | `pillow` | — | Extracts all animation frames from an animated GIF into lossless PNG images. |

---

## 3. Audio & Video Media Conversions (FFmpeg)

| Operation ID | Source Formats | Target Format | Engine | Quality / Detail Controls | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `audio.to_mp3` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `mp3` | `ffmpeg` | Quality Preset, Bitrate (`320k`, `256k`, `192k`, `128k`, `96k`), Sample Rate, Channels | Uses `libmp3lame` (`-b:a 320k -q:a 0` in Lossless/Exact preset). |
| `audio.to_wav` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `wav` | `ffmpeg` | Quality Preset, Bit Depth (`16`-bit, `24`-bit default in Lossless/High, `32`-bit float PCM), Sample Rate, Channels | Uncompressed lossless PCM WAV output (`pcm_s24le` by default in Lossless/High mode). |
| `audio.to_flac` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `flac` | `ffmpeg` | Lossless compression level 8, Sample Rate, Channels | Archival lossless FLAC compression. |
| `audio.to_aac` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `aac` | `ffmpeg` | Bitrate (`320k`–`96k`), Sample Rate, Channels | Raw ADTS AAC audio stream. |
| `audio.to_m4a` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `m4a` | `ffmpeg` | Quality Preset, Bitrate (`320k`–`96k`) or **Lossless ALAC** toggle | Automatically uses Apple Lossless (`alac`) in Lossless/Exact preset or high-bitrate AAC when toggled off. |
| `audio.to_ogg` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `ogg` | `ffmpeg` | Quality scale (`-q:a 9` at 320k down to `-q:a 2`), Sample Rate, Channels | Ogg Vorbis audio encoding (`libvorbis`). |
| `audio.to_opus` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `opus` | `ffmpeg` | Bitrate (`320k`/`256k`–`96k`), Channels | High-efficiency Opus audio encoding (`libopus`). |
| `audio.to_aiff` | `wav`, `mp3`, `flac`, `aac`, `ogg`, `opus`, `m4a`, `aiff`, `wma` | `aiff` | `ffmpeg` | Quality Preset, Bit Depth (`16`, `24`, `32`), Sample Rate, Channels | Uncompressed big-endian PCM AIFF audio (`pcm_s24be` in Lossless/High mode). |
| `video.extract_mp3` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `mp3` | `ffmpeg` | Bitrate (`320k`–`96k`) | Requires source video to contain an audio stream (filtered automatically on silent videos). |
| `video.extract_wav` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `wav` | `ffmpeg` | Bit Depth (`16`, `24`, `32`) | Extracts uncompressed PCM WAV audio from video. |
| `video.extract_flac` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `flac` | `ffmpeg` | Lossless | Extracts lossless FLAC audio from video. |
| `video.extract_m4a` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `m4a` | `ffmpeg` | Bitrate / Lossless ALAC | Extracts M4A audio track from video. |
| `video.to_mp4` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `mp4` | `ffmpeg` | CRF (`0`–`51`, default `14` in Lossless/Exact), Preset (`slow`/`medium`/`fast`), Scale Height, FPS, Audio Bitrate | H.264 (`libx264`) + AAC with `+faststart`. |
| `video.to_mkv` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `mkv` | `ffmpeg` | CRF, Preset, Scale Height, FPS, Audio Bitrate | Matroska container transcoding. |
| `video.to_mov` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `mov` | `ffmpeg` | CRF, Preset, Scale Height, FPS, Audio Bitrate | Apple QuickTime MOV output. |
| `video.to_avi` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `avi` | `ffmpeg` | CRF, Preset, Scale Height, FPS, Audio Bitrate | AVI video transcoding. |
| `video.to_webm` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `webm` | `ffmpeg` | CRF, Preset, Scale Height, FPS, Audio Bitrate | VP9 (`libvpx-vp9`) + Opus/Vorbis WebM encoding. |
| `video.to_gif` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `wmv`, `flv`, `mpeg` | `gif` | `ffmpeg` | FPS (`5`–`30`), Width (`160`–`1920`) | Lanczos-scaled animated GIF generation. |
| `video.extract_subtitles` | `mp4`, `mkv`, `mov`, `webm` | `srt` | `ffmpeg` | — | Extracts first text subtitle stream to SubRip `.srt` (hidden when source has no subtitle stream). |
| `video.metadata_to_json` | `mp4`, `mkv`, `avi`, `mov`, `webm`, `mp3`, `wav`, `flac`, `aac`, `ogg`, `opus`, `m4a` | `json` | `ffmpeg` | — | Exports container, video, audio, and subtitle stream telemetry via FFprobe. |

---

## 4. Structured Data, Archives, Speech, OCR & Binary Inspection

| Operation ID | Source Formats | Target Format | Engine | Notes & Limitations |
| :--- | :--- | :--- | :--- | :--- |
| `data.csv_to_json` / `data.json_to_csv` | `csv`, `tsv` ⇄ `json` | `json` / `csv` | `data` | Configurable delimiter and nested dictionary key flattening. |
| `data.json_to_yaml` / `data.yaml_to_json` | `json` ⇄ `yaml`, `yml` | `yaml` / `json` | `data` | Safe YAML parsing and formatting (`pyyaml`). |
| `data.xml_to_json` / `data.json_to_xml` | `xml` ⇄ `json` | `json` / `xml` | `data` | XXE/entity-expansion hardened via `defusedxml`. |
| `text.to_crlf` / `text.to_lf` | `txt`, `csv`, `json`, `yaml`, `xml`, `markdown` | `txt` | `data` | Converts line endings between Windows (`CRLF`) and Unix (`LF`). |
| `text.convert_encoding` | `txt`, `csv`, `json`, `yaml`, `xml`, `markdown` | `txt` | `data` | Normalizes character encoding (`utf-8`, `utf-16`, `ascii`, `latin-1`). |
| `data.csv_to_mp4` | `csv` | `mp4` | `ffmpeg` | Renders animated bar-chart visualization frames from CSV columns and encodes to H.264 MP4. |
| `archive.extract_zip` / `archive.extract_tar` / `archive.extract_gz` / `archive.extract_7z` | `zip`, `tar`, `tgz`, `gz`, `7z` | `dir` | `archive` | Enforces Zip-Slip path traversal blocking, symlink rejection, and 2 GB / 200:1 decompression bomb limits. |
| `archive.list_to_json` | `zip`, `tar`, `tgz`, `gz`, `7z` | `json` | `archive` | Inspects archive entries, sizes, and safety status without extracting. |
| `archive.to_zip` / `archive.to_7z` / `archive.to_tar` / `archive.to_gz` | Files, `dir`, or existing `zip`/`tar`/`tgz`/`gz`/`7z` | `zip` / `7z` / `tar` / `gz` | `archive` | Packages files/folders or safely extracts and repacks between archive formats. |
| `workflow.archive_to_pdf` | `zip`, `tar`, `tgz`, `7z` | `pdf` | `workflow` | Safely extracts eligible images, PDFs, text, and Office docs from an archive and merges them into one combined PDF. |
| `speech.text_to_wav` | `txt`, `markdown` | `wav` | `tts` | Offline speech synthesis using Windows SAPI5 (`pyttsx3`) with deterministic PCM WAV fallback. |
| `ocr.image_to_txt` | `png`, `jpeg`, `jpg`, `webp`, `bmp`, `tiff`, `tif` | `txt` | `ocr` | Requires local Tesseract OCR binary (`tesseract.exe`). Hidden in default workspace when Tesseract is absent. |
| `speech.audio_to_txt` | `wav`, `mp3`, `flac`, `m4a`, `ogg` | `txt` | `asr` | Requires optional local `faster-whisper` package and model weights. Hidden when absent. |
| `binary.inspect_to_json` | `exe`, `dll`, `sys`, `bin`, `*` | `json` | `binary` | Static inspection only (MD5/SHA-1/SHA-256, Shannon entropy, PE headers). Never executes or decompiles binaries. |
| `binary.extract_strings` | `exe`, `dll`, `sys`, `bin`, `*` | `txt` | `binary` | Extracts printable ASCII and UTF-16LE strings statically. |
| `binary.hex_dump` | `exe`, `dll`, `sys`, `bin` | `txt` | `binary` | Generates formatted 16-byte-per-line hexadecimal + ASCII inspection dump. |
