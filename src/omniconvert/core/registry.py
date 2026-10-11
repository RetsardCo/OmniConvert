"""Central Capability Registry and operation discovery."""

from typing import List, Dict, Optional, Set
import shutil
from omniconvert.models.capability import Capability
from omniconvert.core.file_detector import FileMetadata

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

        # Check FFmpeg
        if shutil.which("ffmpeg") is not None:
            self._installed_engines.add("ffmpeg")

        # Check LibreOffice
        if shutil.which("soffice") is not None or shutil.which("libreoffice") is not None:
            self._installed_engines.add("libreoffice")

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
        for cap in self._capabilities.values():
            if only_available and not self.is_engine_available(cap.engine):
                continue
            if cap.matches_input(meta.detected_format, meta.category):
                matches.append(cap)
        return matches

    def _register_default_capabilities(self):
        """Populate initial registered capabilities across all categories."""

        # 1. Images (Pillow Engine)
        self.register(Capability(
            id="image.to_jpeg",
            display_name="Convert to JPEG",
            description="Convert raster image to JPEG format.",
            input_categories=["image"],
            input_formats=["png", "webp", "bmp", "tiff", "gif"],
            output_category="image",
            output_format="jpeg",
            engine="pillow",
            operation="convert_image",
            lossy=True,
            settings_schema={
                "quality": {"type": "int", "min": 1, "max": 100, "default": 85},
                "background_color": {"type": "color", "default": "#FFFFFF"}
            },
            limitations=["Transparency will be flattened against background color."]
        ))

        self.register(Capability(
            id="image.to_png",
            display_name="Convert to PNG",
            description="Convert raster image to lossless PNG format.",
            input_categories=["image"],
            input_formats=["jpeg", "jpg", "webp", "bmp", "tiff", "ico", "gif"],
            output_category="image",
            output_format="png",
            engine="pillow",
            operation="convert_image",
            lossy=False
        ))

        self.register(Capability(
            id="image.to_webp",
            display_name="Convert to WebP",
            description="Convert raster image to modern WebP format.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "bmp", "tiff"],
            output_category="image",
            output_format="webp",
            engine="pillow",
            operation="convert_image",
            lossy=True,
            settings_schema={
                "lossless": {"type": "bool", "default": False},
                "quality": {"type": "int", "min": 1, "max": 100, "default": 80}
            }
        ))

        self.register(Capability(
            id="image.to_bmp",
            display_name="Convert to BMP",
            description="Convert raster image to uncompressed Windows Bitmap.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "tiff"],
            output_category="image",
            output_format="bmp",
            engine="pillow",
            operation="convert_image",
            lossy=True,
            limitations=["BMP does not preserve transparency."]
        ))

        self.register(Capability(
            id="image.to_tiff",
            display_name="Convert to TIFF",
            description="Convert raster image to TIFF format.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "bmp"],
            output_category="image",
            output_format="tiff",
            engine="pillow",
            operation="convert_image",
            lossy=False
        ))

        self.register(Capability(
            id="image.to_ico",
            display_name="Generate Windows Icon (.ico)",
            description="Create multi-resolution Windows icon file.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "bmp"],
            output_category="image",
            output_format="ico",
            engine="pillow",
            operation="generate_ico",
            lossy=False
        ))

        # 2. Documents & PDF (pypdf & office Engines)
        self.register(Capability(
            id="pdf.extract_text",
            display_name="Extract Text to TXT",
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
            display_name="Extract Text & Metadata to JSON",
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
            id="image.to_pdf",
            display_name="Wrap Image into PDF",
            description="Convert and embed image into a PDF page.",
            input_categories=["image"],
            input_formats=["png", "jpeg", "jpg", "webp", "bmp", "tiff"],
            output_category="document",
            output_format="pdf",
            engine="pypdf",
            operation="image_to_pdf",
            lossy=False
        ))

        self.register(Capability(
            id="office.to_pdf",
            display_name="Convert Office Document to PDF",
            description="Render office document (Word, PowerPoint, Excel) to PDF.",
            input_categories=["document"],
            input_formats=["docx", "doc", "pptx", "xlsx", "odt", "rtf"],
            output_category="document",
            output_format="pdf",
            engine="libreoffice",
            operation="office_to_pdf",
            lossy=False,
            limitations=["Requires local LibreOffice installation."]
        ))

        self.register(Capability(
            id="office.to_txt",
            display_name="Convert Office Document to Plain Text",
            description="Extract raw text from office document.",
            input_categories=["document"],
            input_formats=["docx", "doc", "odt", "rtf"],
            output_category="text",
            output_format="txt",
            engine="libreoffice",
            operation="office_to_txt",
            lossy=True,
            limitations=["Formatting and embedded images are stripped."]
        ))

        # 3. Structured Data (Data Engine)
        self.register(Capability(
            id="data.csv_to_json",
            display_name="Convert CSV to JSON",
            description="Parse tabular CSV and output structured JSON array.",
            input_categories=["data"],
            input_formats=["csv"],
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
            limitations=["Deeply nested keys are flattened or converted to strings."]
        ))

        # 4. Media (FFmpeg Engine)
        self.register(Capability(
            id="video.extract_mp3",
            display_name="Extract Audio to MP3",
            description="Extract audio track from video and encode to MP3.",
            input_categories=["video"],
            input_formats=["mp4", "mkv", "avi", "mov", "webm"],
            output_category="audio",
            output_format="mp3",
            engine="ffmpeg",
            operation="extract_audio",
            lossy=True,
            settings_schema={
                "bitrate": {"type": "choice", "values": ["128k", "192k", "256k", "320k"], "default": "192k"}
            },
            limitations=["Source video must have an audio stream."]
        ))

        self.register(Capability(
            id="video.extract_wav",
            display_name="Extract Audio to WAV",
            description="Extract uncompressed PCM audio from video.",
            input_categories=["video"],
            input_formats=["mp4", "mkv", "avi", "mov", "webm"],
            output_category="audio",
            output_format="wav",
            engine="ffmpeg",
            operation="extract_audio",
            lossy=False
        ))

        self.register(Capability(
            id="audio.to_mp3",
            display_name="Convert Audio to MP3",
            description="Transcode audio to widely compatible MP3 format.",
            input_categories=["audio"],
            input_formats=["wav", "flac", "aac", "ogg", "m4a"],
            output_category="audio",
            output_format="mp3",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=True
        ))

        self.register(Capability(
            id="audio.to_wav",
            display_name="Convert Audio to WAV",
            description="Decode audio to uncompressed PCM WAV format.",
            input_categories=["audio"],
            input_formats=["mp3", "flac", "aac", "ogg", "m4a"],
            output_category="audio",
            output_format="wav",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=False
        ))

        self.register(Capability(
            id="audio.to_flac",
            display_name="Convert Audio to FLAC",
            description="Encode audio to lossless FLAC format.",
            input_categories=["audio"],
            input_formats=["wav", "mp3", "aac", "ogg"],
            output_category="audio",
            output_format="flac",
            engine="ffmpeg",
            operation="convert_audio",
            lossy=False
        ))

        self.register(Capability(
            id="video.to_mp4",
            display_name="Transcode to MP4 (H.264/AAC)",
            description="Re-encode video into standard MP4 container.",
            input_categories=["video"],
            input_formats=["mkv", "avi", "mov", "webm"],
            output_category="video",
            output_format="mp4",
            engine="ffmpeg",
            operation="transcode_video",
            lossy=True
        ))

        self.register(Capability(
            id="video.to_mkv",
            display_name="Transcode to MKV",
            description="Transcode video into Matroska container.",
            input_categories=["video"],
            input_formats=["mp4", "avi", "mov", "webm"],
            output_category="video",
            output_format="mkv",
            engine="ffmpeg",
            operation="transcode_video",
            lossy=True
        ))

        self.register(Capability(
            id="video.to_gif",
            display_name="Convert Video to Animated GIF",
            description="Extract and optimize frames into an animated GIF.",
            input_categories=["video"],
            input_formats=["mp4", "mkv", "avi", "mov", "webm"],
            output_category="image",
            output_format="gif",
            engine="ffmpeg",
            operation="video_to_gif",
            lossy=True,
            limitations=["GIF format is limited to 256 colors."]
        ))

        self.register(Capability(
            id="video.extract_subtitles",
            display_name="Extract Subtitles to SRT",
            description="Extract text subtitle track from video container.",
            input_categories=["video"],
            input_formats=["mkv", "mp4"],
            output_category="text",
            output_format="srt",
            engine="ffmpeg",
            operation="extract_subtitles",
            lossy=False,
            limitations=["Source video must contain an embedded subtitle track."]
        ))

        # 5. Archive (Archive Engine)
        self.register(Capability(
            id="archive.extract_zip",
            display_name="Extract ZIP Archive",
            description="Safely extract files from ZIP archive to target directory.",
            input_categories=["archive"],
            input_formats=["zip"],
            output_category="directory",
            output_format="dir",
            engine="archive",
            operation="extract_archive",
            lossy=False
        ))
