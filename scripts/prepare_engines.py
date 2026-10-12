"""Engine and model asset staging script for OmniConvert.

Prepares:
- bin/tesseract/: Portable Tesseract OCR binary and traineddata (eng, osd)
- resources/models/whisper/: Offline CTranslate2 Whisper model weights (tiny.en)
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def prepare_tesseract(root: Path) -> Path:
    tess_dir = root / "bin" / "tesseract"
    tess_dir.mkdir(parents=True, exist_ok=True)
    tess_exe = tess_dir / "tesseract.exe"

    if tess_exe.exists() and (tess_dir / "tessdata" / "eng.traineddata").exists():
        print(f"[OK] Tesseract already prepared at: {tess_dir}")
        return tess_dir

    staging_tess = root / "staging_tess"
    if (staging_tess / "tesseract.exe").exists():
        print(f"[+] Copying staged Tesseract from {staging_tess} to {tess_dir}...")
        for item in staging_tess.iterdir():
            if item.name.startswith("$"):
                continue
            dest = tess_dir / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        print(f"[OK] Tesseract staged into: {tess_dir}")
        return tess_dir

    # Fallback: check 7z and installer
    winget_cache = Path(os.environ.get("LOCALAPPDATA", "")) / "Temp" / "WinGet"
    found_installer = list(winget_cache.glob("**/tesseract-ocr-w64-setup*.exe"))
    seven_zip = Path("C:/Program Files/7-Zip/7z.exe")

    if found_installer and seven_zip.exists():
        installer = found_installer[0]
        print(f"[+] Extracting {installer} to {tess_dir} using 7-Zip...")
        cmd = [
            str(seven_zip), "x", str(installer),
            f"-o{tess_dir}",
            "tesseract.exe", "*.dll", "tessdata\\eng.traineddata", "tessdata\\osd.traineddata", "tessdata\\pdf.ttf",
            "-r", "-y"
        ]
        subprocess.run(cmd, check=True)
        plugins_dir = tess_dir / "$PLUGINSDIR"
        if plugins_dir.exists():
            shutil.rmtree(plugins_dir)
        print(f"[OK] Tesseract extracted into: {tess_dir}")
        return tess_dir

    print("[!] Warning: Could not locate Tesseract binary to stage.")
    return tess_dir


def prepare_whisper(root: Path) -> Path:
    model_dir = root / "resources" / "models" / "whisper"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_bin = model_dir / "model.bin"

    if model_bin.exists():
        print(f"[OK] Whisper model already prepared at: {model_dir}")
        return model_dir

    # Check huggingface hub cache first
    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    whisper_caches = list(hf_cache.glob("models--Systran--faster-whisper-tiny.en/snapshots/*"))
    if whisper_caches:
        src_snap = whisper_caches[0]
        print(f"[+] Copying Whisper tiny.en from {src_snap} to {model_dir}...")
        for item in src_snap.iterdir():
            shutil.copy2(item, model_dir / item.name)
        print(f"[OK] Whisper model staged into: {model_dir}")
        return model_dir

    # Download via faster_whisper
    try:
        from faster_whisper import download_model  # type: ignore
        print("[+] Downloading faster-whisper tiny.en model...")
        dl_path = download_model("tiny.en")
        for item in Path(dl_path).iterdir():
            shutil.copy2(item, model_dir / item.name)
        print(f"[OK] Whisper model downloaded and staged into: {model_dir}")
        return model_dir
    except Exception as exc:
        print(f"[!] Warning: Could not prepare Whisper model: {exc}")
        return model_dir


def main():
    root = get_project_root()
    print("=== OmniConvert Engine Asset Preparation ===")
    prepare_tesseract(root)
    prepare_whisper(root)
    print("=== Staging Complete ===")


if __name__ == "__main__":
    main()
