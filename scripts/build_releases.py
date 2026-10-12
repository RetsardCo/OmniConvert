"""OmniConvert Release Packaging Automation.

Builds and packages all 5 release targets into dist/releases/:
1. OmniConvert-Portable-Lite.zip      (~110 MB): Core app only (70+ formats)
2. OmniConvert-Portable-OCR.zip       (~145 MB): Core app + bundled Tesseract in bin/tesseract/
3. OmniConvert-Portable-Whisper.zip   (~185 MB): Core app + bundled Whisper model in resources/models/
4. OmniConvert-Portable-Full.zip      (~240 MB): Core app + both OCR & Whisper
5. OmniConvert-Setup.exe              (~110 MB): Smart Inno Setup installer with component selection
"""

import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def find_iscc() -> Path | None:
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
    ]
    for c in candidates:
        if c.exists():
            return c
    found = shutil.which("ISCC.exe") or shutil.which("iscc")
    return Path(found) if found else None


def build_pyinstaller_bundle(root: Path, skip_pyinstaller: bool = False) -> Path:
    dist_app = root / "dist" / "OmniConvert"
    app_exe = dist_app / "OmniConvert.exe"

    if skip_pyinstaller and app_exe.exists():
        print(f"[SKIP] PyInstaller build skipped; using existing {app_exe}")
        return dist_app

    print("\n========================================================")
    print("Step 1: Compiling Base Application with PyInstaller")
    print("========================================================")

    icon_ico = root / "src" / "omniconvert" / "resources" / "icon.ico"
    resources_dir = root / "src" / "omniconvert" / "resources"
    app_entry = root / "app.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "OmniConvert",
        "--paths", str(root / "src"),
        "--add-data", f"{resources_dir};omniconvert/resources",
        "--collect-all", "pillow_heif",
        "--collect-all", "pycdlib",
        "--collect-all", "py7zr",
        "--collect-all", "pdf2docx",
        "--collect-all", "faster_whisper",
        "--collect-all", "ctranslate2",
        "--collect-all", "pyttsx3",
        "--collect-submodules", "omniconvert",
    ]

    if icon_ico.exists():
        cmd.extend(["--icon", str(icon_ico)])

    cmd.append(str(app_entry))

    print(f"Running command:\n{' '.join(cmd)}\n")
    subprocess.run(cmd, cwd=str(root), check=True)

    if not app_exe.exists():
        raise RuntimeError(f"PyInstaller build finished but {app_exe} was not found!")

    print(f"[OK] PyInstaller build succeeded at: {dist_app}")
    return dist_app


def create_portable_zip(
    zip_dest: Path,
    base_dir: Path,
    extra_mappings: list[tuple[Path, str]],
    label: str,
):
    print(f"\n[+] Packaging {label} -> {zip_dest.name}...")
    start = time.time()
    zip_dest.parent.mkdir(parents=True, exist_ok=True)

    if zip_dest.exists():
        zip_dest.unlink()

    with zipfile.ZipFile(zip_dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        # 1. Base PyInstaller directory
        for file_path in base_dir.rglob("*"):
            if file_path.is_file():
                arcname = Path("OmniConvert") / file_path.relative_to(base_dir)
                zf.write(file_path, str(arcname))

        # 2. Extra mapped directories (e.g. bin/tesseract or resources/models)
        for src_dir, target_rel in extra_mappings:
            if src_dir.exists():
                for file_path in src_dir.rglob("*"):
                    if file_path.is_file():
                        rel = file_path.relative_to(src_dir)
                        arcname = Path("OmniConvert") / target_rel / rel
                        zf.write(file_path, str(arcname))

    size_mb = zip_dest.stat().st_size / (1024 * 1024)
    elapsed = time.time() - start
    print(f"[OK] Created {zip_dest.name} ({size_mb:.1f} MB in {elapsed:.1f}s)")


def compile_inno_setup(root: Path, iscc_exe: Path | None) -> Path | None:
    print("\n========================================================")
    print("Step 3: Compiling Inno Setup Smart Installer")
    print("========================================================")

    iss_file = root / "scripts" / "installer.iss"
    out_installer = root / "dist" / "releases" / "OmniConvert-Setup.exe"

    if not iss_file.exists():
        print(f"[!] Warning: {iss_file} not found.")
        return None

    if not iscc_exe or not iscc_exe.exists():
        print("[!] ISCC.exe not found. Skipping Inno Setup compilation.")
        return None

    print(f"[+] Compiling installer using {iscc_exe}...")
    subprocess.run([str(iscc_exe), str(iss_file)], cwd=str(root / "scripts"), check=True)

    if out_installer.exists():
        size_mb = out_installer.stat().st_size / (1024 * 1024)
        print(f"[OK] Inno Setup installer compiled: {out_installer.name} ({size_mb:.1f} MB)")
        return out_installer

    print("[!] Warning: Inno Setup ran but output file not found.")
    return None


def main():
    root = get_project_root()
    releases_dir = root / "dist" / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)

    # Check for arguments
    skip_pyinstaller = "--skip-build" in sys.argv

    # Ensure engine staging is completed
    from prepare_engines import prepare_tesseract, prepare_whisper
    prepare_tesseract(root)
    prepare_whisper(root)

    tess_dir = root / "bin" / "tesseract"
    whisper_dir = root / "resources" / "models" / "whisper"

    # 1. Build PyInstaller base
    base_dist = build_pyinstaller_bundle(root, skip_pyinstaller=skip_pyinstaller)

    # 2. Package 4 Portable Zips
    print("\n========================================================")
    print("Step 2: Creating 4 Portable Release Zip Archives")
    print("========================================================")

    # 1. Portable Lite
    create_portable_zip(
        releases_dir / "OmniConvert-Portable-Lite.zip",
        base_dist,
        [],
        "OmniConvert-Portable-Lite",
    )

    # 2. Portable OCR
    create_portable_zip(
        releases_dir / "OmniConvert-Portable-OCR.zip",
        base_dist,
        [(tess_dir, "bin/tesseract")],
        "OmniConvert-Portable-OCR",
    )

    # 3. Portable Whisper
    create_portable_zip(
        releases_dir / "OmniConvert-Portable-Whisper.zip",
        base_dist,
        [(whisper_dir, "resources/models/whisper")],
        "OmniConvert-Portable-Whisper",
    )

    # 4. Portable Full
    create_portable_zip(
        releases_dir / "OmniConvert-Portable-Full.zip",
        base_dist,
        [
            (tess_dir, "bin/tesseract"),
            (whisper_dir, "resources/models/whisper"),
        ],
        "OmniConvert-Portable-Full",
    )

    # 3. Compile Installer
    iscc_path = find_iscc()
    compile_inno_setup(root, iscc_path)

    # Summary
    print("\n========================================================")
    print("OmniConvert Export & Release Summary (Folder: dist/releases/)")
    print("========================================================")
    expected_files = [
        "OmniConvert-Portable-Lite.zip",
        "OmniConvert-Portable-OCR.zip",
        "OmniConvert-Portable-Whisper.zip",
        "OmniConvert-Portable-Full.zip",
        "OmniConvert-Setup.exe",
    ]
    for filename in expected_files:
        fpath = releases_dir / filename
        if fpath.exists():
            mb = fpath.stat().st_size / (1024 * 1024)
            print(f"  [OK]      {filename:<35} : {mb:>6.1f} MB  (Ready)")
        else:
            print(f"  [MISSING] {filename:<35} : Missing")
    print("========================================================\n")


if __name__ == "__main__":
    main()
