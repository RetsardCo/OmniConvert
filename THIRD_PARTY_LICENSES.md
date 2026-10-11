# Third-Party Licenses & Notices

OmniConvert relies on open-source Python packages and optional local command-line tools. All processing is performed locally on the user's machine.

## Core Python Dependencies

| Package | License | Purpose |
| :--- | :--- | :--- |
| **PySide6** (Qt for Python) | LGPLv3 | Desktop GUI framework, thread pool, and event loop |
| **Pillow** (PIL Fork) | HPND (MIT-like) | Raster image decoding, transformation, and encoding |
| **pypdf** | BSD-3-Clause | PDF text extraction, metadata parsing, merging, and validation |
| **PyMuPDF** (`fitz`) | AGPLv3 / Commercial | High-DPI PDF rendering, SVG rasterization, and PDF layout inspection |
| **pdf2docx** | GPLv3 | PDF-to-Word (`.pdf` -> `.docx`) layout and table reconstruction |
| **python-docx** | MIT | Reading and authoring Microsoft Word (`.docx`) documents |
| **reportlab** | BSD-3-Clause | Generating structured multi-page PDF documents from Word, Excel, PowerPoint, and text |
| **openpyxl** | MIT | Reading and writing Microsoft Excel (`.xlsx`) workbooks |
| **python-pptx** | MIT | Reading Microsoft PowerPoint (`.pptx`) presentations |
| **Markdown** | BSD-3-Clause | Markdown-to-HTML conversion |
| **py7zr** | LGPLv2.1+ | 7-Zip (`.7z`) archive listing, extraction, and creation |
| **pyttsx3** | MPL-2.0 | Offline Windows SAPI5 text-to-speech synthesis |
| **pytesseract** | Apache-2.0 | Wrapper for local Tesseract OCR executable |
| **PyYAML** | MIT | YAML parsing and serialization |
| **defusedxml** | PSFL | Safe XML parsing hardened against XXE and entity expansion bombs |

## Optional External Local Binaries

- **FFmpeg / FFprobe** (`LGPLv2.1+` or `GPLv2+` depending on build): Invoked as an isolated local subprocess (`SafeSubprocessRunner` with `shell=False`) for audio and video transcoding.
- **LibreOffice** (`MPL-2.0`): Optional local office suite invoked in `--headless` mode when installed.
- **Tesseract OCR** (`Apache-2.0`): Optional local OCR engine invoked as an isolated subprocess when installed.
