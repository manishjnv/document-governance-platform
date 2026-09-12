"""Consultant scan kit: build the downloadable zip served at GET /kit.zip."""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

KIT_DIR = Path(__file__).parent / "kit"
# Kit root shows one entry per platform (setup.cmd / setup.sh, scopewise-scan.cmd / .sh);
# the PowerShell internals live under bin/ so users are not offered three "setup" files.
KIT_FILES = (
    "README.md",
    "config.yaml",
    "setup.cmd",
    "setup.sh",
    "scopewise-scan.cmd",
    "scopewise-scan.sh",
    "bin/setup.ps1",
    "bin/scopewise-scan.ps1",
    "bin/KIT_VERSION.json",
)


def build_kit_zip() -> bytes:
    """Zip the kit files + vendor/ into an in-memory buffer, rooted at scopewise-scan-kit/."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in KIT_FILES:
            zf.write(KIT_DIR / name, f"scopewise-scan-kit/{name}")
        for path in (KIT_DIR / "vendor").iterdir():
            if path.is_file():
                zf.write(path, f"scopewise-scan-kit/vendor/{path.name}")
    return buf.getvalue()


def kit_version() -> dict:
    return json.loads((KIT_DIR / "bin" / "KIT_VERSION.json").read_text())
