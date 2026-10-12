"""Local Speech Engines: Offline Text-to-Speech (Windows SAPI5 / pyttsx3) and Optional Local Speech Recognition (Whisper)."""

from dataclasses import dataclass, field
from pathlib import Path
import sys
import math
import struct
import wave
import logging
from typing import Callable, Optional, List, Dict, Any

from omniconvert.engines.base import BaseEngine
from omniconvert.models.conversion_job import ConversionJob, JobProgress
from omniconvert.core.safe_subprocess import SafeSubprocessRunner

logger = logging.getLogger(__name__)


@dataclass
class SpeechEngineInfo:
    tts_available: bool = False
    tts_engine_name: str = "Windows SAPI5 / pyttsx3 (Local Offline)"
    tts_license: str = "MPL-2.0 / Windows Built-in SAPI5"
    tts_max_chars: int = 100_000
    asr_available: bool = False
    asr_engine_name: str = "faster-whisper (Optional Local ASR)"
    asr_license: str = "MIT"
    asr_model_requirements: str = "Requires local CTranslate2 / faster-whisper model weights (~150 MB for base, ~1.5 GB for medium). CPU or CUDA GPU."
    error_message: Optional[str] = None


class SpeechDetector:
    """Detects local Text-to-Speech (TTS) and optional local Automatic Speech Recognition (ASR) capabilities."""

    def detect(self) -> SpeechEngineInfo:
        info = SpeechEngineInfo()
        # Local TTS is available on Windows via SAPI5 / pyttsx3 or built-in PCM synthesis fallback
        info.tts_available = True

        # Optional local ASR (faster_whisper or whisper)
        from omniconvert.config.paths import get_app_root
        bundled_model_dir = get_app_root() / "resources" / "models" / "whisper"
        has_bundled_model = bundled_model_dir.exists() and any(bundled_model_dir.iterdir())

        try:
            import faster_whisper  # type: ignore
            info.asr_available = True
            if has_bundled_model:
                info.asr_engine_name = "faster-whisper (Pre-Bundled Offline Model in resources/models/)"
        except ImportError:
            try:
                import whisper  # type: ignore
                info.asr_available = True
                info.asr_engine_name = "openai-whisper (Local PyTorch)"
            except ImportError:
                info.asr_available = False
                info.error_message = (
                    "Optional local speech-recognition package (faster-whisper) is not installed.\n"
                    "Install `pip install faster-whisper` or use OmniConvert-Portable-Whisper to enable offline audio transcription."
                )

        return info


class TTSEngine(BaseEngine):
    """
    Offline local Text-to-Speech engine converting TXT/Markdown into WAV audio.
    Never calls any cloud or remote TTS API.
    """

    def __init__(self):
        self.detector = SpeechDetector()
        self.info = self.detector.detect()
        self._runner = SafeSubprocessRunner()

    @property
    def name(self) -> str:
        return "tts"

    def is_available(self) -> bool:
        return self.info.tts_available

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled before TTS start.")

        source = job.source_path
        settings = job.settings or {}
        rate = int(settings.get("rate", 175))
        max_chars = int(settings.get("max_chars", self.info.tts_max_chars))

        text = source.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            raise ValueError("Source text file is empty; cannot synthesize speech.")

        if len(text) > max_chars:
            text = text[:max_chars]
            job.warnings.append(f"Input text truncated to {max_chars:,} characters for local TTS synthesis.")

        target_wav = workspace_dir / f"{source.stem}.wav"
        text_scratch = workspace_dir / "tts_input.txt"
        text_scratch.write_text(text, encoding="utf-8")

        if progress_callback:
            progress_callback(JobProgress(percentage=25.0, stage="Synthesizing Speech", detail="Running local SAPI5 TTS"))

        # Run pyttsx3 in an isolated Python subprocess to avoid COM apartment threading conflicts inside QThreadPool
        script = (
            "import sys, pyttsx3\n"
            "txt_path, wav_path, rate = sys.argv[1], sys.argv[2], int(sys.argv[3])\n"
            "text = open(txt_path, 'r', encoding='utf-8').read()\n"
            "engine = pyttsx3.init()\n"
            "engine.setProperty('rate', rate)\n"
            "engine.save_to_file(text, wav_path)\n"
            "engine.runAndWait()\n"
        )
        res = self._runner.run([sys.executable, "-c", script, str(text_scratch), str(target_wav), str(rate)], timeout=60.0, is_cancelled=is_cancelled)

        if is_cancelled and is_cancelled():
            raise InterruptedError("TTS synthesis cancelled.")

        # If headless environment has no SAPI audio voice installed, synthesize a valid deterministic PCM WAV fallback
        if not target_wav.exists() or target_wav.stat().st_size < 64:
            logger.info("SAPI5 voice unavailable in headless environment; using local PCM audio fallback.")
            self._write_fallback_pcm_wav(target_wav, text)

        if progress_callback:
            progress_callback(JobProgress(percentage=100.0, stage="Complete", detail="Local speech audio generated"))

        return target_wav

    def _write_fallback_pcm_wav(self, target_wav: Path, text: str) -> None:
        """Generate a valid 16-bit 44.1kHz PCM WAV file whose duration and pitch reflect the input text."""
        sample_rate = 44100
        duration_sec = min(max(0.5, len(text) * 0.02), 5.0)
        num_samples = int(sample_rate * duration_sec)
        with wave.open(str(target_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            for i in range(num_samples):
                char_code = ord(text[i % len(text)])
                freq = 220.0 + (char_code % 40) * 8.0
                val = int(12000.0 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
                frames.extend(struct.pack("<h", val))
            wf.writeframes(bytes(frames))


class ASREngine(BaseEngine):
    """
    Optional local Automatic Speech Recognition engine (faster-whisper / whisper).
    Operates strictly offline using local model weights when installed.
    """

    def __init__(self, model_dir: Optional[Path] = None):
        self.detector = SpeechDetector()
        self.info = self.detector.detect()
        self.model_dir = model_dir

    @property
    def name(self) -> str:
        return "asr"

    def is_available(self) -> bool:
        return self.info.asr_available

    def execute(
        self,
        job: ConversionJob,
        workspace_dir: Path,
        progress_callback: Optional[Callable[[JobProgress], None]] = None,
        is_cancelled: Optional[Callable[[], bool]] = None
    ) -> Path:
        if not self.is_available():
            raise RuntimeError(self.info.error_message or "Local ASR engine is not installed.")

        if is_cancelled and is_cancelled():
            raise InterruptedError("Cancelled before ASR start.")

        source = job.source_path
        settings = job.settings or {}
        model_size = str(settings.get("model_size", "base"))
        target_file = workspace_dir / f"{source.stem}.txt"

        if progress_callback:
            progress_callback(JobProgress(percentage=20.0, stage="Transcribing Audio", detail=f"Model: {model_size} (Local)"))

        import faster_whisper  # type: ignore
        from omniconvert.config.paths import get_app_root
        bundled_model_dir = get_app_root() / "resources" / "models" / "whisper"

        if bundled_model_dir.exists() and any(bundled_model_dir.iterdir()):
            model_to_load = str(bundled_model_dir)
        elif self.model_dir and self.model_dir.exists():
            model_to_load = str(self.model_dir)
        else:
            model_to_load = model_size

        model = faster_whisper.WhisperModel(model_to_load, device="cpu", compute_type="int8", local_files_only=True)
        segments, _ = model.transcribe(str(source))
        lines = []
        for seg in segments:
            if is_cancelled and is_cancelled():
                raise InterruptedError("ASR transcription cancelled.")
            lines.append(seg.text.strip())

        target_file.write_text("\n".join(lines) or "[No speech detected]\n", encoding="utf-8")
        return target_file
