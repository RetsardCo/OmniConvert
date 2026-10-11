"""Central Capability Registry and operation discovery."""

from typing import List, Dict, Optional, Set
from omniconvert.models.capability import Capability
from omniconvert.core.file_detector import FileMetadata
from omniconvert.engines.ffmpeg_detector import FFmpegDetector
from omniconvert.engines.office_engine import OfficeEngine
from omniconvert.engines.ocr_engine import OCREngine
from omniconvert.engines.speech_engine import TTSEngine, ASREngine


# Shared schema snippet for quality/detail preset selection
QUALITY_PRESET_SCHEMA = {
    "type": "choice",
    "values": ["lossless", "high", "balanced", "compact"],
    "default": "lossless",
    "label": "Quality / Detail Level"
}


class CapabilityRegistry:
    """Registry managing supported operations, engine requirements, and filtering."""

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._installed_engines: Set[str] = set()
        self._detect_system_engines()
        self._register_default_capabilities()

    def _detect_system_engines(self):
        """Discover available local tools and engines."""
        # Python built-in capabilities always available
        self._installed_engines.add("builtin")
        self._installed_engines.add("data")
        self._installed_engines.add("archive")
        self._installed_engines.add("binary")
        self._installed_engines.add("workflow")

        # Check Pillow
        try:
            import PIL
            self._installed_engines.add("pillow")
        except ImportError:
            pass

        # Check pypdf
        try:
            import pypdf
            self._installed_engines.add("pypdf")
        except ImportError:
            pass

        # Check FFmpeg (using FFmpegDetector which inspects PATH + WinGet + common folders)
        try:
            if FFmpegDetector().detect().is_available:
                self._installed_engines.add("ffmpeg")
        except Exception:
            pass

        # Check Office Engine (LibreOffice OR built-in python-docx + reportlab)
        try:
            if OfficeEngine().is_available():
                self._installed_engines.add("libreoffice")
        except Exception:
            pass

        # Check Local TTS Engine
        try:
            if TTSEngine().is_available():
                self._installed_engines.add("tts")
        except Exception:
            pass

        # Check Optional Local OCR Engine (Tesseract)
        try:
            if OCREngine().is_available():
                self._installed_engines.add("ocr")
        except Exception:
            pass

        # Check Optional Local ASR Engine (faster-whisper / whisper)
        try:
            if ASREngine().is_available():
                self._installed_engines.add("asr")
        except Exception:
            pass

    def register(self, cap: Capability) -> None:
        """Register a new capability."""
        self._capabilities[cap.id] = cap

    def get(self, cap_id: str) -> Optional[Capability]:
        """Retrieve capability by id."""
        return self._capabilities.get(cap_id)

    def is_engine_available(self, engine: str) -> bool:
        """Check if engine is installed and ready."""
        return engine.lower() in self._installed_engines

    def get_all(self, only_available: bool = False) -> List[Capability]:
        """Return all registered capabilities."""
        if not only_available:
            return list(self._capabilities.values())
        return [
            c for c in self._capabilities.values()
            if self.is_engine_available(c.engine)
        ]

    def find_operations_for_file(
        self,
        meta: FileMetadata,
        only_available: bool = True
    ) -> List[Capability]:
        """Find matching capabilities for detected file."""
        matches = []
        det_fmt = meta.detected_format.lower()
        for cap in self._capabilities.values():
            if only_available and not self.is_engine_available(cap.engine):
                continue
            # Match by explicit input format first; only use wildcard category if '*' in input_formats
            fmt_match = det_fmt in [f.lower() for f in cap.input_formats] or "*" in cap.input_formats
            if fmt_match:
                matches.append(cap)
        return matches

    def _register_default_capabilities(self):
        """Populate registered capabilities across all categories."""

        # =====================================================================
        # 1. Images (Pillow Engine)
        # =====================================================================
        self.register(Capability(
            id="image.to_jpeg",
            display_name="Convert to JPEG (Supports Lossless 4:4:4 Quality)",
            description="Convert raster/vector image to JPEG with configurable quality and 4:4:4 lossless chroma.",
            input_categories=["image"],
            input_formats=["png", "webp", "heic", "heif", "bmp", "tiff", "tif", "gif", "ico", "svg", "jpeg", "jpg"],
            output_category="image",
            output_format="jpeg",
            engine="pillow",
            operation="convert_image",
            lossy=True,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "quality": {"type": "int", "min": 1, "max": 100, "default": 100, "label": "JPEG Quality (1-100)"},
                "subsampling": {
                    "type": "choice",
                    "values": ["4:4:4 (Lossless Chroma)", "4:2:2", "4:2:0 (Standard)"],
                    "default": "4:4:4 (Lossless Chroma)",
                    "label": "Color Subsampling"
                },
                "background_color": {"type": "color", "default": "#FFFFFF", "label": "Transparency Fill"},
                "width": {"type": "int", "min": 0, "max": 16384, "default": 0, "label": "Resize Width (0=Original)"},
                "height": {"type": "int", "min": 0, "max": 16384, "default": 0, "label": "Resize Height (0=Original)"},
                "rotate": {"type": "choice", "values": ["0", "90", "180", "270"], "default": "0", "label": "Rotate (°)"}
            },
            limitations=["Transparency will be flattened against background color."]
        ))

        self.register(Capability(
            id="image.to_png",
            display_name="Convert to PNG (Lossless)",
            description="Convert image to 100% lossless PNG format with alpha channel support.",
            input_categories=["image"],
            input_formats=["jpeg", "jpg", "webp", "heic", "heif", "bmp", "tiff", "tif", "ico", "gif", "svg", "png"],
            output_category="image",
            output_format="png",
            engine="pillow",
            operation="convert_image",
            lossy=False,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "width": {"type": "int", "min": 0, "max": 16384, "default": 0, "label": "Resize Width (0=Original)"},
                "height": {"type": "int", "min": 0, "max": 16384, "default": 0, "label": "Resize Height (0=Original)"},
                "rotate": {"type": "choice", "values": ["0", "90", "180", "270"], "default": "0", "label": "Rotate (°)"}
            }
        ))

        self.register(Capability(
            id="image.to_webp",
            display_name="Convert to WebP (Lossless or Compressed)",
            description="Convert image to modern WebP format with optional true lossless mode.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "heic", "heif", "bmp", "tiff", "tif", "gif", "svg"],
            output_category="image",
            output_format="webp",
            engine="pillow",
            operation="convert_image",
            lossy=False,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "lossless": {"type": "bool", "default": True, "label": "True Lossless WebP"},
                "quality": {"type": "int", "min": 1, "max": 100, "default": 100, "label": "Quality (1-100)"},
                "width": {"type": "int", "min": 0, "max": 16384, "default": 0, "label": "Resize Width (0=Original)"},
                "height": {"type": "int", "min": 0, "max": 16384, "default": 0, "label": "Resize Height (0=Original)"}
            }
        ))

        self.register(Capability(
            id="image.to_bmp",
            display_name="Convert to BMP (Uncompressed)",
            description="Convert image to uncompressed Windows Bitmap.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "heic", "heif", "tiff", "tif", "gif", "svg"],
            output_category="image",
            output_format="bmp",
            engine="pillow",
            operation="convert_image",
            lossy=True,
            limitations=["BMP does not preserve alpha transparency."]
        ))

        self.register(Capability(
            id="image.to_tiff",
            display_name="Convert to TIFF (Lossless LZW)",
            description="Convert image to archival lossless TIFF format.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "heic", "heif", "bmp", "gif", "svg"],
            output_category="image",
            output_format="tiff",
            engine="pillow",
            operation="convert_image",
            lossy=False,
            settings_schema={"quality_preset": QUALITY_PRESET_SCHEMA}
        ))

        self.register(Capability(
            id="image.to_ico",
            display_name="Generate Windows Icon (.ico)",
            description="Create multi-resolution Windows icon file (16x16 up to 256x256).",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "bmp", "webp", "svg"],
            output_category="image",
            output_format="ico",
            engine="pillow",
            operation="generate_ico",
            lossy=False
        ))

        self.register(Capability(
            id="image.to_gif",
            display_name="Convert to GIF (.gif)",
            description="Convert static or vector image into GIF format.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "bmp", "tiff", "tif", "svg"],
            output_category="image",
            output_format="gif",
            engine="pillow",
            operation="convert_image",
            lossy=True,
            limitations=["GIF uses a 256-color palette per frame."]
        ))

        self.register(Capability(
            id="image.batch_to_gif",
            display_name="Combine Multiple Images into Animated GIF (.gif)",
            description="Sequence multiple selected images into a single animated GIF with custom frame timing.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "bmp", "tiff", "tif", "heic", "heif"],
            output_category="image",
            output_format="gif",
            engine="pillow",
            operation="images_to_gif",
            lossy=True,
            settings_schema={
                "fps": {"type": "int", "min": 1, "max": 60, "default": 2, "label": "Animation Speed (FPS)"},
                "loop": {"type": "int", "min": 0, "max": 100, "default": 0, "label": "Loop Count (0 = Infinite)"}
            }
        ))


        self.register(Capability(
            id="image.extract_frames",
            display_name="Extract GIF Frames to PNG Folder",
            description="Extract all animation frames from a GIF into lossless PNG images.",
            input_categories=["image"],
            input_formats=["gif"],
            output_category="directory",
            output_format="dir",
            engine="pillow",
            operation="extract_frames",
            lossy=False
        ))

        # =====================================================================
        # 2. Documents, PDF & Word (pypdf & libreoffice/office Engines)
        # =====================================================================
        self.register(Capability(
            id="pdf.extract_pages",
            display_name="Split / Extract PDF Page Range (.pdf)",
            description="Extract a specific page range from a PDF into a new PDF document.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="document",
            output_format="pdf",
            engine="pypdf",
            operation="extract_pages",
            lossy=False,
            settings_schema={
                "start_page": {"type": "int", "min": 1, "max": 9999, "default": 1, "label": "Start Page (1-based)"},
                "end_page": {"type": "int", "min": 0, "max": 9999, "default": 0, "label": "End Page (0=Last Page)"}
            }
        ))
        self.register(Capability(
            id="pdf.to_docx",
            display_name="Convert PDF to Word (.docx)",
            description="Reconstruct PDF layout, paragraphs, tables, and embedded images into an editable Word document.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="document",
            output_format="docx",
            engine="pypdf",
            operation="pdf_to_docx",
            lossy=False,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
            },
            limitations=["Complex multi-column vector graphics may be approximated as images or paragraphs."]
        ))

        self.register(Capability(
            id="office.to_pdf",
            display_name="Convert Document to PDF (.pdf)",
            description="Render Word (.docx), Excel (.xlsx), PowerPoint (.pptx), Markdown, or Text document into a formatted PDF.",
            input_categories=["document", "text"],
            input_formats=["docx", "doc", "pptx", "xlsx", "odt", "rtf", "txt", "markdown", "html"],
            output_category="document",
            output_format="pdf",
            engine="libreoffice",
            operation="office_to_pdf",
            lossy=False,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "page_size": {"type": "choice", "values": ["letter", "a4"], "default": "letter", "label": "Page Size"}
            }
        ))

        self.register(Capability(
            id="office.to_docx",
            display_name="Convert to Word Document (.docx)",
            description="Convert Plain Text, Markdown, or HTML into an editable Microsoft Word (.docx) document.",
            input_categories=["text", "document"],
            input_formats=["txt", "markdown", "html", "rtf"],
            output_category="document",
            output_format="docx",
            engine="libreoffice",
            operation="to_docx",
            lossy=False
        ))

        self.register(Capability(
            id="pdf.extract_text",
            display_name="Extract PDF Text to TXT",
            description="Extract printable text content from PDF pages.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="text",
            output_format="txt",
            engine="pypdf",
            operation="pdf_to_text",
            lossy=False,
            limitations=["Cannot extract text from scanned images without OCR."]
        ))

        self.register(Capability(
            id="pdf.to_json",
            display_name="Extract PDF Text & Metadata to JSON",
            description="Extract page-by-page text and document metadata into structured JSON.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="data",
            output_format="json",
            engine="pypdf",
            operation="pdf_to_json",
            lossy=False
        ))

        self.register(Capability(
            id="pdf.to_png",
            display_name="Render PDF Pages to PNG Image",
            description="Render PDF document pages into a crisp high-resolution lossless PNG image.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="image",
            output_format="png",
            engine="pypdf",
            operation="pdf_to_png",
            lossy=False,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "dpi": {"type": "int", "min": 72, "max": 600, "default": 300, "label": "Render DPI"}
            }
        ))

        self.register(Capability(
            id="pdf.to_jpeg",
            display_name="Render PDF Pages to JPEG Image",
            description="Render PDF document pages into a high-resolution JPEG image.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="image",
            output_format="jpeg",
            engine="pypdf",
            operation="pdf_to_jpeg",
            lossy=True,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "dpi": {"type": "int", "min": 72, "max": 600, "default": 300, "label": "Render DPI"},
                "quality": {"type": "int", "min": 1, "max": 100, "default": 100, "label": "JPEG Quality"}
            }
        ))

        self.register(Capability(
            id="pdf.to_html",
            display_name="Convert PDF to HTML",
            description="Export PDF layout and text into a styled HTML document.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="document",
            output_format="html",
            engine="pypdf",
            operation="pdf_to_html",
            lossy=False
        ))

        self.register(Capability(
            id="pdf.to_md",
            display_name="Convert PDF to Markdown (.md)",
            description="Export PDF pages and headings into clean Markdown.",
            input_categories=["document"],
            input_formats=["pdf"],
            output_category="text",
            output_format="md",
            engine="pypdf",
            operation="pdf_to_md",
            lossy=False
        ))

        self.register(Capability(
            id="image.to_pdf",
            display_name="Wrap Image into PDF",
            description="Convert and embed image into a print-ready PDF page.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "bmp", "tiff", "tif", "heic", "heif"],
            output_category="document",
            output_format="pdf",
            engine="pypdf",
            operation="image_to_pdf",
            lossy=False,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "dpi": {"type": "int", "min": 72, "max": 600, "default": 300, "label": "PDF Resolution (DPI)"}
            }
        ))

        self.register(Capability(
            id="image.batch_to_pdf",
            display_name="Combine Multiple Images into 1 Multi-Page PDF (.pdf)",
            description="Merge a batch of images into a single multi-page PDF where each image is a full page.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "bmp", "tiff", "tif", "heic", "heif", "gif"],
            output_category="document",
            output_format="pdf",
            engine="pypdf",
            operation="images_to_pdf",
            lossy=False,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "dpi": {"type": "int", "min": 72, "max": 600, "default": 300, "label": "PDF Resolution (DPI)"}
            }
        ))


        self.register(Capability(
            id="office.to_txt",
            display_name="Convert Document to Plain Text (.txt)",
            description="Extract raw text from Word, PowerPoint, Excel, HTML, or RTF document.",
            input_categories=["document", "text"],
            input_formats=["docx", "doc", "odt", "rtf", "pptx", "xlsx", "html", "markdown"],
            output_category="text",
            output_format="txt",
            engine="libreoffice",
            operation="office_to_txt",
            lossy=True,
            limitations=["Formatting and embedded images are stripped."]
        ))

        self.register(Capability(
            id="office.docx_to_html",
            display_name="Convert Document to HTML (.html)",
            description="Convert Word (.docx), Excel (.xlsx), or Markdown into clean HTML.",
            input_categories=["document", "text"],
            input_formats=["docx", "xlsx", "markdown"],
            output_category="document",
            output_format="html",
            engine="libreoffice",
            operation="to_html",
            lossy=False
        ))

        self.register(Capability(
            id="office.docx_to_md",
            display_name="Convert Document to Markdown (.md)",
            description="Convert Word (.docx) or HTML document into structured Markdown.",
            input_categories=["document"],
            input_formats=["docx", "html"],
            output_category="text",
            output_format="md",
            engine="libreoffice",
            operation="to_md",
            lossy=False
        ))

        self.register(Capability(
            id="office.xlsx_to_csv",
            display_name="Convert Excel (.xlsx) to CSV",
            description="Export active Excel worksheet rows into standard CSV format.",
            input_categories=["document"],
            input_formats=["xlsx"],
            output_category="data",
            output_format="csv",
            engine="libreoffice",
            operation="xlsx_to_csv",
            lossy=False
        ))

        self.register(Capability(
            id="office.xlsx_to_json",
            display_name="Convert Excel (.xlsx) to JSON",
            description="Serialize Excel worksheet rows into a structured JSON array.",
            input_categories=["document"],
            input_formats=["xlsx"],
            output_category="data",
            output_format="json",
            engine="libreoffice",
            operation="xlsx_to_json",
            lossy=False
        ))

        self.register(Capability(
            id="office.to_xlsx",
            display_name="Convert Tabular Data to Excel (.xlsx)",
            description="Create an Excel (.xlsx) workbook from CSV, TSV, or JSON records.",
            input_categories=["data"],
            input_formats=["csv", "tsv", "json"],
            output_category="document",
            output_format="xlsx",
            engine="libreoffice",
            operation="to_xlsx",
            lossy=False
        ))

        # =====================================================================
        # 3. Structured Data & Text (Data Engine)
        # =====================================================================
        self.register(Capability(
            id="data.csv_to_json",
            display_name="Convert CSV to JSON",
            description="Parse tabular CSV and output structured JSON array.",
            input_categories=["data"],
            input_formats=["csv", "tsv"],
            output_category="data",
            output_format="json",
            engine="data",
            operation="csv_to_json",
            lossy=False
        ))

        self.register(Capability(
            id="data.json_to_csv",
            display_name="Convert JSON to CSV",
            description="Serialize JSON object list into tabular CSV rows.",
            input_categories=["data"],
            input_formats=["json"],
            output_category="data",
            output_format="csv",
            engine="data",
            operation="json_to_csv",
            lossy=True,
            limitations=["Deeply nested keys are flattened into JSON-encoded strings."]
        ))

        self.register(Capability(
            id="data.json_to_yaml",
            display_name="Convert JSON to YAML",
            description="Serialize JSON structure to clean, human-readable YAML.",
            input_categories=["data"],
            input_formats=["json"],
            output_category="data",
            output_format="yaml",
            engine="data",
            operation="json_to_yaml",
            lossy=False
        ))

        self.register(Capability(
            id="data.yaml_to_json",
            display_name="Convert YAML to JSON",
            description="Parse YAML configuration into standard JSON.",
            input_categories=["data"],
            input_formats=["yaml", "yml"],
            output_category="data",
            output_format="json",
            engine="data",
            operation="yaml_to_json",
            lossy=False
        ))

        self.register(Capability(
            id="data.xml_to_json",
            display_name="Convert XML to JSON",
            description="Safely parse XML document into nested JSON structure.",
            input_categories=["data"],
            input_formats=["xml"],
            output_category="data",
            output_format="json",
            engine="data",
            operation="xml_to_json",
            lossy=False
        ))

        self.register(Capability(
            id="data.json_to_xml",
            display_name="Convert JSON to XML",
            description="Serialize JSON object hierarchy into standard XML elements.",
            input_categories=["data"],
            input_formats=["json"],
            output_category="data",
            output_format="xml",
            engine="data",
            operation="json_to_xml",
            lossy=False
        ))

        self.register(Capability(
            id="text.to_crlf",
            display_name="Convert Line Endings to Windows (CRLF)",
            description="Convert Unix (LF) newlines to Windows standard (CRLF).",
            input_categories=["text", "data"],
            input_formats=["txt", "csv", "json", "yaml", "xml", "markdown"],
            output_category="text",
            output_format="txt",
            engine="data",
            operation="to_crlf",
            lossy=False
        ))

        self.register(Capability(
            id="text.to_lf",
            display_name="Convert Line Endings to Unix (LF)",
            description="Convert Windows (CRLF) newlines to Unix standard (LF).",
            input_categories=["text", "data"],
            input_formats=["txt", "csv", "json", "yaml", "xml", "markdown"],
            output_category="text",
            output_format="txt",
            engine="data",
            operation="to_lf",
            lossy=False
        ))

        self.register(Capability(
            id="text.convert_encoding",
            display_name="Convert Character Encoding (UTF-8 / UTF-16 / Latin-1)",
            description="Normalize text file encoding to UTF-8, UTF-16, or ASCII.",
            input_categories=["text", "data"],
            input_formats=["txt", "csv", "json", "yaml", "xml", "markdown"],
            output_category="text",
            output_format="txt",
            engine="data",
            operation="convert_encoding",
            lossy=False,
            settings_schema={
                "encoding": {"type": "choice", "values": ["utf-8", "utf-16", "ascii", "latin-1"], "default": "utf-8", "label": "Target Encoding"}
            }
        ))

        # =====================================================================
        # 4. Media: Audio & Video (FFmpeg Engine)
        # =====================================================================
        all_video_inputs = ["mp4", "mkv", "avi", "mov", "webm", "wmv", "flv", "mpeg", "hevc", "h265"]
        all_audio_inputs = ["wav", "mp3", "flac", "aac", "ogg", "opus", "m4a", "aiff", "wma"]
        audio_settings = {
            "quality_preset": QUALITY_PRESET_SCHEMA,
            "bitrate": {"type": "choice", "values": ["320k", "256k", "192k", "128k", "96k"], "default": "320k", "label": "Audio Bitrate"},
            "sample_rate": {"type": "choice", "values": ["0", "48000", "44100", "22050", "16000"], "default": "0", "label": "Sample Rate (0=Original)"},
            "channels": {"type": "choice", "values": ["0", "2", "1"], "default": "0", "label": "Channels (0=Original, 2=Stereo, 1=Mono)"}
        }
        lossless_audio_settings = {
            "quality_preset": QUALITY_PRESET_SCHEMA,
            "bit_depth": {"type": "choice", "values": ["16", "24", "32"], "default": "24", "label": "PCM Bit Depth"},
            "sample_rate": {"type": "choice", "values": ["0", "48000", "44100", "22050", "16000"], "default": "0", "label": "Sample Rate (0=Original)"},
            "channels": {"type": "choice", "values": ["0", "2", "1"], "default": "0", "label": "Channels (0=Original)"}
        }

        # Video -> Audio extraction
        self.register(Capability(
            id="video.extract_mp3",
            display_name="Extract Audio to MP3 (Up to 320 kbps)",
            description="Extract audio track from video and encode to MP3.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="audio",
            output_format="mp3",
            engine="ffmpeg",
            operation="extract_audio",
            lossy=True,
            settings_schema=audio_settings,
            limitations=["Source video must have an audio stream."]
        ))

        self.register(Capability(
            id="video.extract_wav",
            display_name="Extract Audio to WAV (Lossless PCM)",
            description="Extract uncompressed studio-grade PCM audio from video.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="audio",
            output_format="wav",
            engine="ffmpeg",
            operation="extract_audio",
            lossy=False,
            settings_schema=lossless_audio_settings
        ))

        self.register(Capability(
            id="video.extract_flac",
            display_name="Extract Audio to FLAC (Lossless)",
            description="Extract audio stream from video into lossless FLAC format.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="audio",
            output_format="flac",
            engine="ffmpeg",
            operation="extract_audio",
            lossy=False,
            settings_schema=lossless_audio_settings
        ))

        self.register(Capability(
            id="video.extract_m4a",
            display_name="Extract Audio to M4A / AAC",
            description="Extract audio stream from video into M4A container.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="audio",
            output_format="m4a",
            engine="ffmpeg",
            operation="extract_audio",
            lossy=True,
            settings_schema=audio_settings
        ))

        # Audio -> Audio conversions (all formats)
        self.register(Capability(
            id="audio.to_mp3",
            display_name="Convert Audio to MP3 (Up to 320 kbps CBR)",
            description="Transcode audio to universally compatible MP3 with configurable bitrate and sample rate.",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="mp3",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=True,
            settings_schema=audio_settings
        ))

        self.register(Capability(
            id="audio.to_wav",
            display_name="Convert Audio to WAV (Lossless PCM)",
            description="Decode audio to uncompressed lossless PCM WAV format (16/24/32-bit).",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="wav",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=False,
            settings_schema=lossless_audio_settings
        ))

        self.register(Capability(
            id="audio.to_flac",
            display_name="Convert Audio to FLAC (Lossless Audio)",
            description="Encode audio to lossless FLAC format with zero fidelity loss.",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="flac",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=False,
            settings_schema=lossless_audio_settings
        ))

        self.register(Capability(
            id="audio.to_aac",
            display_name="Convert Audio to AAC (.aac)",
            description="Encode audio to Advanced Audio Coding (.aac) with up to 320 kbps quality.",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="aac",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=True,
            settings_schema=audio_settings
        ))

        self.register(Capability(
            id="audio.to_m4a",
            display_name="Convert Audio to M4A (AAC or Apple Lossless ALAC)",
            description="Encode audio to M4A container with high-bitrate AAC or lossless ALAC.",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="m4a",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=False,
            settings_schema={
                **audio_settings,
                "lossless_alac": {"type": "bool", "default": False, "label": "Use Apple Lossless (ALAC)"}
            }
        ))

        self.register(Capability(
            id="audio.to_ogg",
            display_name="Convert Audio to OGG Vorbis (.ogg)",
            description="Encode audio into open-source OGG Vorbis container.",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="ogg",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=True,
            settings_schema=audio_settings
        ))

        self.register(Capability(
            id="audio.to_opus",
            display_name="Convert Audio to Opus (.opus)",
            description="Encode audio to high-efficiency modern Opus codec.",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="opus",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=True,
            settings_schema=audio_settings
        ))

        self.register(Capability(
            id="audio.to_aiff",
            display_name="Convert Audio to AIFF (Lossless Uncompressed)",
            description="Encode audio to Apple Interchange File Format (uncompressed PCM).",
            input_categories=["audio"],
            input_formats=all_audio_inputs,
            output_category="audio",
            output_format="aiff",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=False,
            settings_schema=lossless_audio_settings
        ))

        # Video -> Video & Metadata
        video_settings = {
            "quality_preset": QUALITY_PRESET_SCHEMA,
            "crf": {"type": "int", "min": 0, "max": 51, "default": 18, "label": "Video CRF (0=Lossless, 18=High, 23=Std)"},
            "preset": {"type": "choice", "values": ["ultrafast", "fast", "medium", "slow", "veryslow"], "default": "medium", "label": "Encoder Speed Preset"},
            "scale_height": {"type": "choice", "values": ["0", "2160", "1080", "720", "480"], "default": "0", "label": "Scale Height (0=Original)"},
            "bitrate": {"type": "choice", "values": ["320k", "256k", "192k", "128k"], "default": "256k", "label": "Audio Bitrate"}
        }

        self.register(Capability(
            id="video.to_mp4",
            display_name="Transcode Video to MP4 (H.264/AAC)",
            description="Re-encode video into universally compatible MP4 container.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="video",
            output_format="mp4",
            engine="ffmpeg",
            operation="transcode_video",
            lossy=True,
            settings_schema=video_settings
        ))

        self.register(Capability(
            id="video.to_mkv",
            display_name="Transcode Video to MKV (Matroska)",
            description="Transcode video into Matroska MKV container.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="video",
            output_format="mkv",
            engine="ffmpeg",
            operation="transcode_video",
            lossy=True,
            settings_schema=video_settings
        ))

        self.register(Capability(
            id="video.to_webm",
            display_name="Transcode Video to WebM (VP9/Opus)",
            description="Transcode video to open WebM format.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="video",
            output_format="webm",
            engine="ffmpeg",
            operation="transcode_video",
            lossy=True,
            settings_schema=video_settings
        ))

        self.register(Capability(
            id="video.to_mov",
            display_name="Transcode Video to QuickTime MOV",
            description="Transcode video into Apple QuickTime MOV container.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="video",
            output_format="mov",
            engine="ffmpeg",
            operation="transcode_video",
            lossy=True,
            settings_schema=video_settings
        ))

        self.register(Capability(
            id="video.to_avi",
            display_name="Transcode Video to AVI",
            description="Transcode video into AVI container.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="video",
            output_format="avi",
            engine="ffmpeg",
            operation="transcode_video",
            lossy=True,
            settings_schema=video_settings
        ))

        self.register(Capability(
            id="video.to_gif",
            display_name="Convert Video to Animated GIF",
            description="Extract and optimize video frames into an animated GIF.",
            input_categories=["video"],
            input_formats=all_video_inputs,
            output_category="image",
            output_format="gif",
            engine="ffmpeg",
            operation="video_to_gif",
            lossy=True,
            settings_schema={
                "quality_preset": QUALITY_PRESET_SCHEMA,
                "fps": {"type": "int", "min": 5, "max": 30, "default": 15, "label": "Frame Rate (FPS)"},
                "width": {"type": "int", "min": 120, "max": 1920, "default": 640, "label": "Width (px)"}
            },
            limitations=["GIF format is limited to 256 colors."]
        ))

        self.register(Capability(
            id="video.extract_subtitles",
            display_name="Extract Subtitles to SRT",
            description="Extract text subtitle track from video container.",
            input_categories=["video"],
            input_formats=["mkv", "mp4", "mov", "webm"],
            output_category="text",
            output_format="srt",
            engine="ffmpeg",
            operation="extract_subtitles",
            lossy=False,
            limitations=["Source video must contain an embedded subtitle track."]
        ))

        self.register(Capability(
            id="video.metadata_to_json",
            display_name="Export Media Streams & Metadata to JSON",
            description="Inspect video/audio streams, codecs, resolution, and tags into structured JSON.",
            input_categories=["video", "audio"],
            input_formats=all_video_inputs + all_audio_inputs,
            output_category="data",
            output_format="json",
            engine="ffmpeg",
            operation="metadata_to_json",
            lossy=False
        ))

        self.register(Capability(
            id="data.csv_to_mp4",
            display_name="Generate Data Visualization Video (.mp4)",
            description="Render tabular CSV rows into an animated chart visualization video.",
            input_categories=["data"],
            input_formats=["csv"],
            output_category="video",
            output_format="mp4",
            engine="ffmpeg",
            operation="csv_to_mp4",
            lossy=False
        ))

        # =====================================================================
        # 5. Archives & Compression (Archive Engine)
        # =====================================================================
        self.register(Capability(
            id="archive.extract_zip",
            display_name="Extract ZIP Archive",
            description="Safely extract files from ZIP archive with path-traversal and zip-bomb protection.",
            input_categories=["archive"],
            input_formats=["zip"],
            output_category="directory",
            output_format="dir",
            engine="archive",
            operation="extract_archive",
            lossy=False
        ))

        self.register(Capability(
            id="archive.extract_tar",
            display_name="Extract TAR / TAR.GZ Archive",
            description="Safely extract files from TAR or TAR.GZ archive to target folder.",
            input_categories=["archive"],
            input_formats=["tar", "tgz"],
            output_category="directory",
            output_format="dir",
            engine="archive",
            operation="extract_archive",
            lossy=False
        ))

        self.register(Capability(
            id="archive.extract_gz",
            display_name="Decompress GZip (.gz) File",
            description="Safely decompress GZ stream with size limit safeguards.",
            input_categories=["archive"],
            input_formats=["gz"],
            output_category="directory",
            output_format="dir",
            engine="archive",
            operation="extract_archive",
            lossy=False
        ))

        self.register(Capability(
            id="archive.extract_7z",
            display_name="Extract 7-Zip (.7z) Archive",
            description="Safely extract files from 7z archive.",
            input_categories=["archive"],
            input_formats=["7z"],
            output_category="directory",
            output_format="dir",
            engine="archive",
            operation="extract_archive",
            lossy=False
        ))

        self.register(Capability(
            id="archive.extract_iso",
            display_name="Extract ISO Disc Image (.iso)",
            description="Safely extract all files and directory structure from an ISO 9660 / Joliet disc image.",
            input_categories=["archive"],
            input_formats=["iso"],
            output_category="directory",
            output_format="dir",
            engine="archive",
            operation="extract_archive",
            lossy=False
        ))

        self.register(Capability(
            id="archive.list_to_json",
            display_name="Export Archive File Manifest to JSON",
            description="Inspect archive entries, sizes, and safety status without extracting files.",
            input_categories=["archive"],
            input_formats=["zip", "tar", "tgz", "gz", "7z", "iso"],
            output_category="data",
            output_format="json",
            engine="archive",
            operation="list_to_json",
            lossy=False
        ))

        packable_inputs = [
            "pdf", "docx", "doc", "xlsx", "pptx", "odt", "rtf", "txt", "markdown", "md", "html",
            "csv", "tsv", "json", "yaml", "yml", "xml",
            "png", "jpeg", "jpg", "webp", "bmp", "tiff", "tif", "gif", "ico", "svg", "heic", "heif",
            "mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "aiff", "wma",
            "mp4", "mkv", "avi", "mov", "webm", "wmv", "flv", "mpeg", "hevc", "h265", "dir"
        ]

        self.register(Capability(
            id="archive.to_zip",
            display_name="Package / Repack into ZIP Archive (.zip)",
            description="Compress file, folder, or repack existing archive into a validated ZIP archive.",
            input_categories=["archive", "document", "image", "data", "text", "audio", "video", "directory"],
            input_formats=["tar", "tgz", "gz", "7z", "iso"] + packable_inputs,
            output_category="archive",
            output_format="zip",
            engine="archive",
            operation="create_zip",
            lossy=False,
            settings_schema={
                "compresslevel": {"type": "int", "min": 0, "max": 9, "default": 6, "label": "Compression Level (0-9)"}
            }
        ))

        self.register(Capability(
            id="archive.to_7z",
            display_name="Package / Repack into 7-Zip Archive (.7z)",
            description="Compress or repack into high-ratio 7z archive.",
            input_categories=["archive", "document", "image", "data", "text", "audio", "video", "directory"],
            input_formats=["zip", "tar", "tgz", "gz", "iso"] + packable_inputs,
            output_category="archive",
            output_format="7z",
            engine="archive",
            operation="create_7z",
            lossy=False
        ))

        self.register(Capability(
            id="archive.to_tar",
            display_name="Package / Repack into TAR Archive (.tar)",
            description="Package file, folder, or repack existing archive into a TAR archive.",
            input_categories=["archive", "document", "image", "data", "text", "audio", "video", "directory"],
            input_formats=["zip", "tgz", "gz", "7z", "iso"] + packable_inputs,
            output_category="archive",
            output_format="tar",
            engine="archive",
            operation="create_tar",
            lossy=False
        ))

        self.register(Capability(
            id="archive.to_iso",
            display_name="Burn / Package to ISO Disc Image (.iso)",
            description="Master and package files, folders, or existing archives into a mountable ISO 9660 / Joliet disc image.",
            input_categories=["archive", "document", "image", "data", "text", "audio", "video", "directory"],
            input_formats=["zip", "tar", "tgz", "gz", "7z"] + packable_inputs,
            output_category="archive",
            output_format="iso",
            engine="archive",
            operation="create_iso",
            lossy=False
        ))

        self.register(Capability(
            id="archive.to_gz",
            display_name="Compress into GZip Stream (.gz)",
            description="Compress single file into a GZip (.gz) archive.",
            input_categories=["document", "image", "data", "text", "audio", "video"],
            input_formats=[f for f in packable_inputs if f != "dir"],
            output_category="archive",
            output_format="gz",
            engine="archive",
            operation="create_gz",
            lossy=False,
            settings_schema={
                "compresslevel": {"type": "int", "min": 1, "max": 9, "default": 6, "label": "Compression Level (1-9)"}
            }
        ))

        self.register(Capability(
            id="workflow.archive_to_pdf",
            display_name="Combine Archive Contents into Single PDF (Workflow)",
            description="Extract archive safely and merge all eligible images, documents, and PDFs into one combined PDF.",
            input_categories=["archive"],
            input_formats=["zip", "tar", "tgz", "7z"],
            output_category="document",
            output_format="pdf",
            engine="workflow",
            operation="archive_to_pdf",
            lossy=False
        ))

        # =====================================================================
        # 6. Local Speech (TTS / ASR) & Local OCR
        # =====================================================================
        self.register(Capability(
            id="speech.text_to_wav",
            display_name="Convert Text to Spoken Audio (.wav via Local TTS)",
            description="Synthesize natural spoken audio offline using local Windows SAPI5 speech engine.",
            input_categories=["text"],
            input_formats=["txt", "markdown"],
            output_category="audio",
            output_format="wav",
            engine="tts",
            operation="text_to_speech",
            lossy=False,
            settings_schema={
                "rate": {"type": "int", "min": 80, "max": 300, "default": 175, "label": "Speech Speed (WPM)"}
            }
        ))

        self.register(Capability(
            id="ocr.image_to_txt",
            display_name="Extract Text from Image (Local OCR)",
            description="Recognize text in images offline using local Tesseract OCR.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "bmp", "tiff", "tif"],
            output_category="text",
            output_format="txt",
            engine="ocr",
            operation="ocr_image",
            lossy=True,
            settings_schema={
                "language": {"type": "choice", "values": ["eng", "fra", "deu", "spa", "jpn"], "default": "eng", "label": "OCR Language"}
            },
            limitations=["Requires local Tesseract OCR installation."]
        ))

        self.register(Capability(
            id="speech.audio_to_txt",
            display_name="Transcribe Audio to Text (Local Whisper ASR)",
            description="Transcribe spoken audio offline using local faster-whisper model.",
            input_categories=["audio"],
            input_formats=["wav", "mp3", "flac", "m4a", "ogg"],
            output_category="text",
            output_format="txt",
            engine="asr",
            operation="transcribe_audio",
            lossy=True,
            limitations=["Requires optional local faster-whisper package and downloaded model weights."]
        ))

        # =====================================================================
        # 7. Static Binary Inspection (Binary Engine)
        # =====================================================================
        self.register(Capability(
            id="binary.extract_strings",
            display_name="Extract Printable Strings to TXT (Static Analysis)",
            description="Extract readable ASCII and UTF-16 strings without executing the binary.",
            input_categories=["binary"],
            input_formats=["exe", "dll", "sys", "bin", "*"],
            output_category="text",
            output_format="txt",
            engine="binary",
            operation="extract_strings",
            lossy=True,
            settings_schema={
                "min_length": {"type": "int", "min": 3, "max": 32, "default": 4, "label": "Min String Length"}
            },
            limitations=["Static string extraction only; never executes or emulates the file."]
        ))

        self.register(Capability(
            id="binary.inspect_to_json",
            display_name="Export Cryptographic Hashes & PE Metadata to JSON",
            description="Compute MD5/SHA1/SHA256 hashes, Shannon entropy, and static PE headers into JSON.",
            input_categories=["binary", "document", "image", "audio", "video", "archive", "data", "text"],
            input_formats=["exe", "dll", "sys", "bin", "*"],
            output_category="data",
            output_format="json",
            engine="binary",
            operation="inspect_to_json",
            lossy=False
        ))

        self.register(Capability(
            id="binary.hex_dump",
            display_name="Generate Hexadecimal + ASCII Dump (.txt)",
            description="Export a structured 16-byte-per-line hex and ASCII inspection dump.",
            input_categories=["binary"],
            input_formats=["exe", "dll", "sys", "bin"],
            output_category="text",
            output_format="txt",
            engine="binary",
            operation="hex_dump",
            lossy=False
        ))
