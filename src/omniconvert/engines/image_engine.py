"""Pillow Image Engine for format conversion, lossless/detail presets, transformations, SVG rasterization, and ICO generation."""

from pathlib import Path
import logging
from typing import Callable, Optional, Dict, Any, List
from PIL import Image, ImageOps

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress

logger = logging.getLogger(__name__)

QUALITY_PRESET_MAP = {
    "lossless": {"quality": 100, "subsampling": 0, "lossless": True},
    "exact": {"quality": 100, "subsampling": 0, "lossless": True},
    "high": {"quality": 95, "subsampling": 0, "lossless": False},
    "balanced": {"quality": 85, "subsampling": 2, "lossless": False},
    "compact": {"quality": 70, "subsampling": 2, "lossless": False},
}


try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass


class ImageEngine(BaseEngine):
    """Executes raster and vector image conversions and transformations using Pillow, pillow-heif, and PyMuPDF."""

    def __init__(self):
        self._supported_formats = {"png", "jpeg", "jpg", "webp", "heic", "heif", "bmp", "tiff", "tif", "ico", "gif", "svg"}

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

        # 0. Batch Images to Animated GIF
        if job.operation_id == "image.batch_to_gif" or (target_format == "gif" and settings.get("batch_image_paths")):
            raw_paths = settings.get("batch_image_paths", [])
            paths = [Path(p) for p in raw_paths] if raw_paths else [source]
            target_name = settings.get("output_filename", f"{source.stem}_animation.gif")
            return self.images_to_gif(paths, workspace_dir / target_name, settings, progress_callback, is_cancelled)

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
            if source.suffix.lower() == ".svg":
                image = self._rasterize_svg(source, settings)
            else:
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

        if target_format == "ico" or job.operation_id == "image.to_ico":
            return self._generate_ico(image, workspace_dir, source.stem, settings, progress_callback, is_cancelled)

        # 3. Apply optional transformations (Resize, Rotate, Crop)
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

        # 6. Quality / Detail Preset & Fine-grained Compression settings
        preset_key = str(settings.get("quality_preset", "")).lower()
        preset_defaults = QUALITY_PRESET_MAP.get(preset_key, {})

        if pillow_fmt == "JPEG":
            default_q = preset_defaults.get("quality", 100 if settings.get("lossless") else 95)
            quality = max(1, min(100, int(settings.get("quality", default_q))))
            save_kwargs["quality"] = quality
            save_kwargs["optimize"] = True

            # Chroma subsampling: 0 = 4:4:4 (no color subsampling / exact color fidelity), 1 = 4:2:2, 2 = 4:2:0
            subsampling_setting = settings.get("subsampling", preset_defaults.get("subsampling", 0 if quality >= 95 else 2))
            if isinstance(subsampling_setting, str):
                if "4:4:4" in subsampling_setting or subsampling_setting == "0":
                    save_kwargs["subsampling"] = 0
                elif "4:2:2" in subsampling_setting or subsampling_setting == "1":
                    save_kwargs["subsampling"] = 1
                else:
                    save_kwargs["subsampling"] = 2
            else:
                save_kwargs["subsampling"] = int(subsampling_setting)

        elif pillow_fmt == "WEBP":
            default_lossless = preset_defaults.get("lossless", True)
            default_q = preset_defaults.get("quality", 100 if default_lossless else 90)
            is_lossless = bool(settings.get("lossless", default_lossless))
            quality = max(1, min(100, int(settings.get("quality", 100 if is_lossless else default_q))))
            save_kwargs["lossless"] = is_lossless
            save_kwargs["quality"] = quality
            save_kwargs["method"] = 6

        elif pillow_fmt == "PNG":
            save_kwargs["optimize"] = True
            save_kwargs["compress_level"] = int(settings.get("compress_level", 6))

        elif pillow_fmt == "TIFF":
            save_kwargs["compression"] = settings.get("compression", "tiff_lzw")

        image.save(target_file, format=pillow_fmt, **save_kwargs)

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Image written successfully"))

        return target_file

    def _rasterize_svg(self, svg_path: Path, settings: Dict[str, Any]) -> Image.Image:
        """Rasterize an SVG vector file into an RGBA PIL Image using PyMuPDF."""
        import fitz
        dpi = int(settings.get("dpi", 300))
        doc = fitz.open(str(svg_path))
        if len(doc) == 0:
            doc.close()
            raise ValueError("SVG file contains no drawable page.")
        try:
            page = doc[0]
            pix = page.get_pixmap(dpi=dpi, alpha=True)
            img = Image.frombytes("RGBA", [pix.width, pix.height], pix.samples)
            return img
        finally:
            doc.close()

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
                fill_color = (255, 255, 255)
                if isinstance(bg_color, str) and bg_color.startswith("#") and len(bg_color) == 7:
                    try:
                        fill_color = (
                            int(bg_color[1:3], 16),
                            int(bg_color[3:5], 16),
                            int(bg_color[5:7], 16)
                        )
                    except ValueError:
                        pass

                background = Image.new("RGB", image.size, fill_color)
                if image.mode != "RGBA":
                    image = image.convert("RGBA")
                background.paste(image, mask=image.split()[3])
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
        """Applies crop, resize, rotation, and auto-orientation."""
        try:
            image = ImageOps.exif_transpose(image) or image
        except Exception:
            pass

        # Optional Crop (left, top, right, bottom)
        crop_box = settings.get("crop_box")
        if crop_box and isinstance(crop_box, (list, tuple)) and len(crop_box) == 4:
            image = image.crop(tuple(int(x) for x in crop_box))

        # Resize (scale or explicit dimensions) first
        width = settings.get("width")
        height = settings.get("height")
        try:
            width = int(width) if width else 0
            height = int(height) if height else 0
        except (ValueError, TypeError):
            width, height = 0, 0

        if width > 0 and height > 0:
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        elif width > 0:
            ratio = width / image.width
            new_h = max(1, int(image.height * ratio))
            image = image.resize((width, new_h), Image.Resampling.LANCZOS)
        elif height > 0:
            ratio = height / image.height
            new_w = max(1, int(image.width * ratio))
            image = image.resize((new_w, height), Image.Resampling.LANCZOS)

        # Rotation after resize
        try:
            rotate_angle = int(settings.get("rotate", 0))
        except (ValueError, TypeError):
            rotate_angle = 0

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
        """Extract all frames of an animated image to a folder."""
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

    def images_to_gif(
        self,
        image_paths: List[Path],
        output_path: Path,
        settings: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        """Combine multiple images into an animated GIF."""
        if not image_paths:
            raise ValueError("No images provided for GIF creation.")

        settings = settings or {}
        fps = int(settings.get("fps", 2))
        loop = int(settings.get("loop", 0))  # 0 = infinite loop
        duration_ms = int(settings.get("duration", 1000 // max(1, fps)))

        total = len(image_paths)
        frames = []
        try:
            for idx, p in enumerate(image_paths):
                if is_cancelled and is_cancelled():
                    raise InterruptedError("Cancelled during batch image-to-GIF conversion.")
                if progress_callback:
                    progress_callback(JobProgress(
                        percentage=int((idx / max(1, total)) * 80),
                        stage="Processing Frames",
                        detail=f"Loading frame {idx + 1}/{total}: {p.name}"
                    ))
                with Image.open(p) as img:
                    # Convert to RGBA for consistent handling
                    frame = img.convert("RGBA")
                    frames.append(frame)

            if is_cancelled and is_cancelled():
                raise InterruptedError("Cancelled before saving GIF.")

            if progress_callback:
                progress_callback(JobProgress(percentage=85.0, stage="Encoding GIF", detail=f"Assembling {total} frames into animated GIF"))

            output_path.parent.mkdir(parents=True, exist_ok=True)
            if frames:
                first = frames[0]
                rest = frames[1:]
                first.save(
                    output_path,
                    format="GIF",
                    save_all=True,
                    append_images=rest,
                    duration=duration_ms,
                    loop=loop,
                    optimize=True
                )

            if progress_callback:
                progress_callback(JobProgress(percentage=100.0, stage="Complete", detail=f"Created animated GIF from {total} images"))

            return output_path
        finally:
            for f in frames:
                f.close()

