#!/bin/bash
# Octane Light Denoiser - installer (macOS).
# If double-click is blocked: right-click > Open, or run:
#   chmod +x install.command && ./install.command
DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/OctaneLightDenoiser"
PREFS="$HOME/Library/Preferences/Maxon"

echo "============================================================"
echo "  Octane Light Denoiser - Installer (macOS)"
echo "============================================================"

if [ ! -f "$SRC/light_denoiser.pyp" ]; then
  echo "[!] OctaneLightDenoiser folder not found next to this script."
  exit 1
fi
if [ ! -d "$PREFS" ]; then
  echo "[!] $PREFS not found. Copy OctaneLightDenoiser into your C4D plugins folder manually."
  exit 1
fi

count=0
for d in "$PREFS"/*/ ; do
  if [ -d "${d}plugins" ] || [ -d "${d}prefs" ]; then
    mkdir -p "${d}plugins"
    rm -rf "${d}plugins/OctaneLightDenoiser"
    cp -R "$SRC" "${d}plugins/OctaneLightDenoiser"
    echo " installed -> ${d}plugins"
    count=$((count+1))
  fi
done

if [ "$count" -eq 0 ]; then
  echo "[!] No Cinema 4D folders found under $PREFS — copy manually."
else
  echo "[OK] Installed into $count location(s). Restart Cinema 4D."
fi
