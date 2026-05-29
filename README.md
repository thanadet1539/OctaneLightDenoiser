# ZHiCK Tool — Octane Light Denoiser

Two Cinema 4D plugins that automate Octane's **per-light OIDN denoise** workflow.
After installing, both appear under **Extensions ▸ ZHiCK Tool**:

- **Octane Light ID Manager** — group lights by Light Pass ID (same ID = one pass)
- **Octane Light Denoiser** — pick passes, auto-name them, and build Octane Render AOVs

## Install — Windows (one line)

Open **PowerShell** and run:

```powershell
powershell -ep bypass -c "iwr -useb https://raw.githubusercontent.com/thanadet1539/OctaneLightDenoiser/main/web_install.ps1 | iex"
```

It downloads this repo and copies the plugins into your Cinema 4D plugins folder
(no git client needed). Then **restart Cinema 4D → Extensions ▸ ZHiCK Tool**
(Light ID Manager + Light Denoiser). Run the same command again any time to update.

## Install — clone

```bash
git clone https://github.com/thanadet1539/OctaneLightDenoiser
OctaneLightDenoiser\install.bat      # Windows
```

## Install — macOS

Run `install.command` (right-click → Open if blocked), or copy the
`OctaneLightDenoiser` folder into `~/Library/Preferences/Maxon/<version>/plugins/`.

## Uninstall

Windows: run `uninstall.bat`.

## Requirements

- Cinema 4D **2024+** (Python 3.11)
- Octane (`c4doctane`) **2024.x / 24.x** (24.12 R+ recommended; per-light OIDN needs 2024.1 Alpha4+)

## Usage & notes

See [`OctaneLightDenoiser/README.md`](OctaneLightDenoiser/README.md) for the
Manage/Build workflow and the first-run **Inspector** note (Octane has no
official Python API, so a couple of parameter IDs may need confirming on your
build — the Inspector prints them).
