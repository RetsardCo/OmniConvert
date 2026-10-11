"""Pillow Image Engine for format conversion, transformations, and ICO generation."""

from pathlib import Path
import logging
from typing import Callable, Optional, Dict, Any, List
from PIL import Image, ImageOps

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress

logger = logging.getLogger(__name__)

class ImageEngine(BaseEngine):
    """Executes raster image conversions and transformations using Pillow."""

    def __init__(self):
        self._supported_formats = {"png", "jpeg", "jpg", "webp", "bmp", "tiff", "tif", "ico", "gif"}

    @property
    def name(self) -> str:
        return "pillow"

    def is_available(self) -> bool:
        try:
            import PIL
            return True
        except ImportError:
            return False

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if not self.is_available():
            raise RuntimeError("Pillow library is not installed or available.")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Job cancelled before start.")

        source = job.source_path
        target_format = job.target_format.lower().lstrip(".")
        settings = job.settings or {}

        if progress_callback:
            progress_callback(JobProgress(percentage=10.0, stage="Opening image", detail=f"Loading {source.name}"))

        # Map target format to Pillow format names
        fmt_map = {
            "jpg": "JPEG",
            "jpeg": "JPEG",
            "png": "PNG",
            "webp": "WEBP",
            "bmp": "BMP",
            "ico": "ICO",
            "tiff": "TIFF",
            "tif": "TIFF",
            "gif": "GIF"
        }
        pillow_fmt = fmt_map.get(target_format, target_format.upper())

        try:
            with Image.open(source) as img:
                # 1. Check for GIF frame extraction
                if job.operation_id == "image.extract_frames" and getattr(img, "is_animated", False):
                    return self._extract_gif_frames(img, workspace_dir, source.stem, progress_callback, is_cancelled)

                # 2. Check for multi-resolution Windows Icon generation
                if target_format == "ico" or job.operation_id == "image.to_ico":
                    return self._generate_ico(img, workspace_dir, source.stem, settings, progress_callback, is_cancelled)

                # Convert to memory copy so we can process freely
                image = img.copy()

        except Exception as e:
            raise ValueError(f"Could not open source image: {e}")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Job cancelled.")

        # 3. Apply optional transformations (Resize, Rotate, Flip)
        image = self._apply_transformations(image, settings, progress_callback)

        # 4. Handle Transparency / Color Modes
        image, save_kwargs = self._prepare_color_mode(image, pillow_fmt, settings, job)

        if is_cancelled and is_cancelled():
            raise InterruptedError("Job cancelled.")

        if progress_callback:
            progress_callback(JobProgress(percentage=70.0, stage="Encoding", detail=f"Saving as .{target_format.upper()}"))

        target_file = workspace_dir / f"{source.stem}.{target_format}"

        # 5. Metadata handling (preserve or strip EXIF)
        preserve_metadata = settings.get("preserve_metadata", True)
        if preserve_metadata and "exif" in image.info and pillow_fmt in ("JPEG", "WEBP", "PNG"):
            save_kwargs["exif"] = image.info["exif"]

        # Quality / Compression settings
        if pillow_fmt == "JPEG":
            save_kwargs["quality"] = int(settings.get("quality", 85))
            save_kwargs["optimize"] = True
        elif pillow_fmt == "WEBP":
            save_kwargs["quality"] = int(settings.get("quality", 80))
            save_kwargs["lossless"] = bool(settings.get("lossless", False))
        elif pillow_fmt == "PNG":
            save_kwargs["optimize"] = True

        image.save(target_file, format=pillow_fmt, **save_kwargs)

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Image written successfully"))

        return target_file

    def _prepare_color_mode(
        self,
        image: Image.Image,
        target_fmt: str,
        settings: Dict[str, Any],
        job: ConversionJob
    ) -> tuple[Image.Image, Dict[str, Any]]:
        """Handles alpha transparency flattening and color space conversion."""
        save_kwargs = {}

        # Formats that do not support transparency (JPEG, BMP)
        if target_fmt in ("JPEG", "BMP"):
            if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                job.warnings.append("Transparency was flattened because target format does not support alpha.")
                bg_color = settings.get("background_color", "#FFFFFF")
                # Parse hex or tuple color
                fill_color = (255, 255, 255)
                if isinstance(bg_color, str) and bg_color.startswith("#") and len(bg_color) == 7:
                    fill_color = (
                        int(bg_color[1:3], 16),
                        int(bg_color[3:5], 16),
                        int(bg_color[5:7], 16)
                    )

                background = Image.new("RGB", image.size, fill_color)
                if image.mode != "RGBA":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[3]) # 3 is alpha channel
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

        elif target_fmt == "PNG":
            if image.mode not in ("RGB", "RGBA", "L", "LA", "P"):
                image = image.convert("RGBA")

        return image, save_kwargs

    def _apply_transformations(
        self,
        image: Image.Image,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable]
    ) -> Image.Image:
        """Applies resize, rotation, and auto-orientation."""
        # Auto-orient based on EXIF tag
        try:
            image = ImageOps.exif_transpose(image) or image
        except Exception:
            pass

        # Resize (scale or explicit dimensions) first
        width = settings.get("width")
        height = settings.get("height")
        if width and height:
            image = image.resize((int(width), int(height)), Image.Resampling.LANCZOS)
        elif width:
            ratio = width / image.width
            new_h = int(image.height * ratio)
            image = image.resize((int(width), new_h), Image.Resampling.LANCZOS)
        elif height:
            ratio = height / image.height
            new_w = int(image.width * ratio)
            image = image.resize((new_w, int(height)), Image.Resampling.LANCZOS)

        # Rotation after resize
        rotate_angle = settings.get("rotate", 0)
        if rotate_angle in (90, 180, 270):
            image = image.rotate(360 - rotate_angle, expand=True)

        return image

    def _generate_ico(
        self,
        image: Image.Image,
        workspace_dir: Path,
        stem: str,
        settings: Dict[str, Any],
        progress_callback: Optional[Callable],
        is_cancelled: Optional[Callable]
    ) -> Path:
        """Generate multi-resolution Windows .ico icon file."""
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        target_file = workspace_dir / f"{stem}.ico"
        sizes = settings.get("sizes", [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

        if progress_callback:
            progress_callback(JobProgress(percentage=60.0, stage="Generating Icon", detail="Packaging multiple icon resolutions"))

        image.save(target_file, format="ICO", sizes=sizes)
        return target_file

    def _extract_gif_frames(
        self,
        image: Image.Image,
        workspace_dir: Path,
        stem: str,
        progress_callback: Optional[Callable],
        is_cancelled: Optional[Callable]
    ) -> Path:
        """Extract all frames of an animated image to a folder, or first frame."""
        frames_dir = workspace_dir / f"{stem}_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        total_frames = getattr(image, "n_frames", 1)
        for idx in range(total_frames):
            if is_cancelled and is_cancelled():
                raise InterruptedError("Cancelled during frame extraction.")
            image.seek(idx)
            frame = image.copy()
            frame.save(frames_dir / f"frame_{idx:03d}.png", format="PNG")
            if progress_callback:
                progress_callback(JobProgress(
                    percentage=int((idx / total_frames) * 90),
                    stage="Extracting Frames",
                    detail=f"Frame {idx+1}/{total_frames}"
                ))

        return frames_dir
