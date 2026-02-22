#!/usr/bin/env bash
# build_binary.sh — Build a single-file graphbus CLI binary for the current machine.
#
# Usage:
#   ./scripts/build_binary.sh              # auto-detect arch
#   ./scripts/build_binary.sh x86_64       # force x86_64 (macOS only)
#   ./scripts/build_binary.sh arm64        # force arm64  (macOS only)
#
# Output: dist/graphbus  (or dist/graphbus.exe on Windows)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ARCH="${1:-}"
OS="$(uname -s)"

echo "── GraphBus binary builder ──────────────────────────────────"
echo "  OS:   $OS"
echo "  Arch: ${ARCH:-$(uname -m)}"
echo ""

# ── Prerequisites ──────────────────────────────────────────────────────────────
if ! command -v pyinstaller &>/dev/null; then
  echo "PyInstaller not found — installing…"
  pip install pyinstaller
fi

# ── Build flags ────────────────────────────────────────────────────────────────
ARCH_FLAG=""
if [[ "$OS" == "Darwin" && -n "$ARCH" ]]; then
  ARCH_FLAG="--target-arch $ARCH"
fi

# ── Run PyInstaller ────────────────────────────────────────────────────────────
echo "Running PyInstaller…"
pyinstaller graphbus.spec \
  $ARCH_FLAG \
  --distpath dist \
  --workpath build/_pyinstaller \
  --noconfirm

# ── Result ─────────────────────────────────────────────────────────────────────
BINARY="dist/graphbus"
[[ "$OS" == "MINGW"* || "$OS" == "CYGWIN"* || "$OS" == "Windows"* ]] && BINARY="dist/graphbus.exe"

if [[ -f "$BINARY" ]]; then
  echo ""
  echo "✓  Binary built: $BINARY"
  ls -lh "$BINARY"
  echo ""
  echo "Smoke test:"
  "$BINARY" --version
else
  echo "✗  Build failed — binary not found at $BINARY"
  exit 1
fi
