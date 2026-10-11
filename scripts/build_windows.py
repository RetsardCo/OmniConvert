"""Windows packaging script using PyInstaller with custom icon and resource bundling."""

import subprocess
import sys
from pathlib import Path


def build_package(dry_run: bool = False) -> list[str]:
    root = Path(__file__).resolve().parent.parent
    icon_ico = root / "src" / "omniconvert" / "resources" / "icon.ico"
    resources_dir = root / "src" / "omniconvert" / "resources"
    app_entry = root / "app.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", "OmniConvert",
        "--paths", str(root / "src"),
        "--add-data", f"{resources_dir};omniconvert/resources",
    ]
    if icon_ico.exists():
        cmd.extend(["--icon", str(icon_ico)])

    cmd.append(str(app_entry))

    if not dry_run:
        subprocess.run(cmd, cwd=str(root), check=True)

    return cmd


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    args = build_package(dry_run=dry)
    print("PyInstaller command:", " ".join(args))
