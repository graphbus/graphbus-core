"""
UI Command - Download and launch GraphBus Desktop UI
"""

import click
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, DownloadColumn

console = Console()

# GitHub release info
GITHUB_REPO = "graphbus/graphbus-ui"
UI_VERSION = "1.0.0"
CACHE_DIR = Path.home() / ".graphbus" / "ui"


def _get_platform_asset():
    """Determine the correct asset name for this platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        # macOS - detect ARM vs Intel
        if machine in ("arm64", "aarch64"):
            return f"GraphBus.UI-{UI_VERSION}-arm64-mac.zip", "mac-arm64"
        else:
            return f"GraphBus.UI-{UI_VERSION}-mac.zip", "mac-x64"
    elif system == "linux":
        return f"GraphBus.UI-{UI_VERSION}.AppImage", "linux"
    elif system == "windows":
        return f"GraphBus.UI-{UI_VERSION}-win.zip", "windows"
    else:
        return None, None


def _get_download_url(asset_name):
    """Get GitHub release download URL."""
    return f"https://github.com/{GITHUB_REPO}/releases/latest/download/{asset_name}"


def _download_with_progress(url, dest_path):
    """Download a file with a progress bar."""
    req = urllib.request.Request(url, headers={"User-Agent": "graphbus-cli"})

    # Follow redirects and get content length
    response = urllib.request.urlopen(req)
    total_size = int(response.headers.get("Content-Length", 0))

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
    ) as progress:
        task = progress.add_task("Downloading GraphBus UI...", total=total_size)
        with open(dest_path, "wb") as f:
            while True:
                chunk = response.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                progress.update(task, advance=len(chunk))


def _install_mac(zip_path, install_dir):
    """Extract and install macOS app."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(install_dir)

    # Find the .app bundle
    for item in install_dir.iterdir():
        if item.suffix == ".app":
            # Make the binary executable
            binary = item / "Contents" / "MacOS" / "GraphBus UI"
            if binary.exists():
                binary.chmod(0o755)
            return item
    return None


def _install_linux(appimage_path, install_dir):
    """Install Linux AppImage."""
    dest = install_dir / "GraphBus-UI.AppImage"
    shutil.copy2(appimage_path, dest)
    dest.chmod(0o755)
    return dest


def _install_windows(zip_path, install_dir):
    """Extract and install Windows app."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(install_dir)

    # Find the .exe
    for item in install_dir.rglob("GraphBus UI.exe"):
        return item
    for item in install_dir.rglob("*.exe"):
        return item
    return None


def _launch(executable, platform_id):
    """Launch the UI application."""
    if platform_id.startswith("mac"):
        subprocess.Popen(["open", str(executable)])
    elif platform_id == "linux":
        subprocess.Popen([str(executable)], start_new_session=True)
    elif platform_id == "windows":
        subprocess.Popen([str(executable)], start_new_session=True)


def _get_installed_executable():
    """Check if UI is already installed and return the executable path."""
    if not CACHE_DIR.exists():
        return None, None

    system = platform.system().lower()

    if system == "darwin":
        for item in CACHE_DIR.iterdir():
            if item.suffix == ".app":
                binary = item / "Contents" / "MacOS" / "GraphBus UI"
                if binary.exists():
                    return item, "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
    elif system == "linux":
        appimage = CACHE_DIR / "GraphBus-UI.AppImage"
        if appimage.exists():
            return appimage, "linux"
    elif system == "windows":
        for item in CACHE_DIR.rglob("GraphBus UI.exe"):
            return item, "windows"
        for item in CACHE_DIR.rglob("*.exe"):
            return item, "windows"

    return None, None


@click.command()
@click.option("--reinstall", is_flag=True, help="Force re-download and reinstall")
@click.option("--path", is_flag=True, help="Print install path instead of launching")
def ui(reinstall, path):
    """
    Launch GraphBus Desktop UI

    Downloads the native desktop application on first run and caches it
    locally. Subsequent runs launch the cached version instantly.

    \b
    The desktop app provides:
    - Visual agent graph editor
    - Real-time build monitoring
    - Natural language control
    - Interactive negotiation viewer

    \b
    Examples:
      graphbus ui                # Launch (downloads on first run)
      graphbus ui --reinstall    # Force re-download
      graphbus ui --path         # Show install location
    """
    asset_name, platform_id = _get_platform_asset()

    if not asset_name:
        console.print("[red]Unsupported platform.[/red] GraphBus UI is available for macOS, Linux, and Windows.")
        sys.exit(1)

    # Check for existing installation
    executable, _ = _get_installed_executable()

    if executable and not reinstall:
        if path:
            console.print(str(executable))
            return
        console.print(f"[green]Launching GraphBus UI...[/green]")
        _launch(executable, platform_id)
        return

    # Download and install
    console.print(f"[bold]Installing GraphBus UI for {platform_id}...[/bold]")

    url = _get_download_url(asset_name)

    # Clean old install
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Download to temp file
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(asset_name)[1], delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        _download_with_progress(url, tmp_path)

        # Install based on platform
        console.print("[bold]Installing...[/bold]")
        if platform_id.startswith("mac"):
            executable = _install_mac(tmp_path, CACHE_DIR)
        elif platform_id == "linux":
            executable = _install_linux(tmp_path, CACHE_DIR)
        elif platform_id == "windows":
            executable = _install_windows(tmp_path, CACHE_DIR)

        if not executable:
            console.print("[red]Installation failed — could not find executable in archive.[/red]")
            sys.exit(1)

    finally:
        tmp_path.unlink(missing_ok=True)

    console.print(f"[green]✓ Installed to {CACHE_DIR}[/green]")

    if path:
        console.print(str(executable))
        return

    console.print(f"[green]Launching GraphBus UI...[/green]")
    _launch(executable, platform_id)
