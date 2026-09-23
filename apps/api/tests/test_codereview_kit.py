"""Pure-function tests for the consultant scan kit (no DB needed)."""
from __future__ import annotations

import hashlib
import re
import zipfile
from io import BytesIO
from pathlib import Path

from app.codereview.kit import KIT_DIR, build_kit_zip, kit_version

try:
    import yaml
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False

DETECTION_ROLES = (
    "autoexclude", "graph_annotate", "preprocess", "threatmodel",
    "decompose", "deepdive", "verify", "dedup", "chain",
)


def test_kit_zip_contains_expected_files_and_wheel_hash():
    data = build_kit_zip()
    zf = zipfile.ZipFile(BytesIO(data))
    names = set(zf.namelist())
    expected = {
        "scopewise-scan-kit/README.md",
        "scopewise-scan-kit/config.yaml",
        "scopewise-scan-kit/setup.cmd",
        "scopewise-scan-kit/setup.sh",
        "scopewise-scan-kit/scopewise-scan.cmd",
        "scopewise-scan-kit/scopewise-scan.sh",
        "scopewise-scan-kit/bin/setup.ps1",
        "scopewise-scan-kit/bin/scopewise-scan.ps1",
        "scopewise-scan-kit/bin/KIT_VERSION.json",
        "scopewise-scan-kit/vendor/vvaharness-1.3.0-py3-none-any.whl",
        "scopewise-scan-kit/vendor/LICENSE",
        "scopewise-scan-kit/vendor/NOTICE",
    }
    assert expected.issubset(names)

    version = kit_version()
    wheel_bytes = zf.read("scopewise-scan-kit/vendor/vvaharness-1.3.0-py3-none-any.whl")
    assert hashlib.sha256(wheel_bytes).hexdigest() == version["wheel_sha256"]


def test_kit_shell_scripts_have_lf_line_endings():
    # kit.py zips files byte-for-byte from disk; a CRLF checkout (Windows
    # autocrlf) would ship setup.sh with "#!/usr/bin/env bash\r", which fails
    # on macOS/Linux. .gitattributes pins eol=lf; this catches an override.
    zf = zipfile.ZipFile(BytesIO(build_kit_zip()))
    shell_scripts = [n for n in zf.namelist() if n.endswith(".sh")]
    assert shell_scripts
    for name in shell_scripts:
        assert b"\r" not in zf.read(name), f"{name} has CRLF line endings"


def test_config_yaml_sanity():
    config_path = KIT_DIR / "config.yaml"
    text = config_path.read_text()

    if HAVE_YAML:
        config = yaml.safe_load(text)
        models = config["models"]
        for role in DETECTION_ROLES + ("remediate",):
            entry = models[role]
            assert "id" in entry and "via" in entry
            assert "claude" not in entry["id"]
        assert config["step_remediate"]["enabled"] is False
        assert config["step_validate"]["enabled"] is False
        assert "openrouter" in config["openai"]["base_url"]
    else:
        for role in DETECTION_ROLES + ("remediate",):
            assert re.search(role + r":\s*\{id: [^,}]+, via: [^,}]+", text)
        assert "claude" not in text
        assert re.search(r"step_remediate:\s*\n\s*enabled: false", text)
        assert re.search(r"step_validate:\s*\n\s*enabled: false", text)
        assert "openrouter" in text


def test_scripts_reference_stop_after_s9_and_estimate_and_no_leaked_key():
    # one visible entry per platform at the kit root; no stray setup files
    root_names = {n.split("/", 1)[1] for n in zipfile.ZipFile(BytesIO(build_kit_zip())).namelist() if n.count("/") == 1}
    assert {n for n in root_names if n.startswith("setup")} == {"setup.cmd", "setup.sh"}
    for name in ("scopewise-scan.sh", "bin/scopewise-scan.ps1"):
        text = (KIT_DIR / name).read_text()
        assert "--stop-after s9" in text
        assert "estimate" in text
        assert "sk-or-" not in text
