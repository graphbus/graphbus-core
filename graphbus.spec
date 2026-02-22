# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for the GraphBus CLI binary.

Produces a single-file executable: dist/graphbus (or dist/graphbus.exe on Windows).

Build:
    pip install pyinstaller
    pyinstaller graphbus.spec
"""

import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

# ─── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(SPECPATH)  # noqa: F821 – PyInstaller global


# ─── Data files to bundle ─────────────────────────────────────────────────────
datas = []

# litellm: model pricing JSON + any other data files it ships
datas += collect_data_files("litellm")

# graphbus_cli: Jinja/text templates used by `graphbus init`
templates_dir = ROOT / "graphbus_cli" / "templates"
if templates_dir.exists():
    datas.append((str(templates_dir), "graphbus_cli/templates"))

# graphbus_core: any bundled data (e.g. JSON schemas)
datas += collect_data_files("graphbus_core")

# click: locale files
datas += collect_data_files("click")

# ─── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = [
    # graphbus packages
    "graphbus_cli",
    "graphbus_cli.main",
    "graphbus_cli.commands",
    "graphbus_cli.repl",
    "graphbus_cli.utils",
    "graphbus_cli.hooks",
    "graphbus_core",
    "graphbus_core.build",
    "graphbus_core.runtime",
    "graphbus_core.agents",
    "graphbus_core.model",
    "graphbus_core.backends",

    # CLI + output
    "click",
    "rich",
    "rich.console",
    "rich.table",
    "rich.panel",
    "rich.syntax",
    "rich.progress",
    "rich.markdown",

    # Config + env
    "yaml",
    "dotenv",

    # HTTP + async
    "httpx",
    "httpx._transports.default",
    "anyio",
    "anyio._backends._asyncio",
    "anyio._backends._trio",

    # litellm core (it lazy-loads a lot of provider clients)
    "litellm",
    "litellm.utils",
    "litellm.main",

    # Networking
    "websockets",
    "networkx",
    "networkx.algorithms",
    "networkx.classes",

    # Standard lib extras sometimes missed
    "importlib.metadata",
    "importlib.resources",
    "json",
    "pathlib",
    "textwrap",
    "typing",
    "dataclasses",
]

# Collect all submodules for graphbus packages so dynamically-loaded commands work
hiddenimports += collect_submodules("graphbus_cli")
hiddenimports += collect_submodules("graphbus_core")

# ─── Analysis ─────────────────────────────────────────────────────────────────
a = Analysis(
    [str(ROOT / "graphbus_cli" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Heavy optional deps that aren't needed in the binary
        "textual",          # TUI (textual is optional — skip to keep binary small)
        "firebase_admin",   # Optional multi-tenant auth
        "pytest",
        "pytest_cov",
        "coverage",
        "IPython",
        "notebook",
        "jupyter",
        "matplotlib",
        "pandas",
        "numpy",
        "scipy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)  # noqa: F821

# ─── Single-file executable ────────────────────────────────────────────────────
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="graphbus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,        # compress if UPX is available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,    # CLI tool — keep console window
    disable_windowed_traceback=False,
    target_arch=None,   # set via --target-arch at build time
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
