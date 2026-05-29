# Octane Light Denoiser - web installer (Windows)
# Run:  powershell -ep bypass -c "iwr -useb https://raw.githubusercontent.com/thanadet1539/OctaneLightDenoiser/main/web_install.ps1 | iex"
# Downloads the repo zip from GitHub (no git client required) and copies the
# plugin into every detected Cinema 4D user plugins folder under %APPDATA%\Maxon.

$ErrorActionPreference = 'Stop'
$repo   = 'thanadet1539/OctaneLightDenoiser'
$branch = 'main'

Write-Host "============================================================"
Write-Host "  Octane Light Denoiser - web installer"
Write-Host "============================================================"

$tmp = Join-Path $env:TEMP ("OLD_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force $tmp | Out-Null
$zip = Join-Path $tmp 'src.zip'
try {
    Write-Host "Downloading $repo ($branch) ..."
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -UseBasicParsing "https://codeload.github.com/$repo/zip/refs/heads/$branch" -OutFile $zip
    Expand-Archive $zip -DestinationPath $tmp -Force

    $src = Get-ChildItem $tmp -Directory | Where-Object {
        Test-Path (Join-Path $_.FullName 'OctaneLightDenoiser\octanelightdenoiser.pyp')
    } | Select-Object -First 1
    if (-not $src) { Write-Host "[!] Plugin not found in the downloaded archive."; return }
    $plugin = Join-Path $src.FullName 'OctaneLightDenoiser'

    $maxon = Join-Path $env:APPDATA 'Maxon'
    if (-not (Test-Path $maxon)) {
        Write-Host "[!] '$maxon' not found. Is Cinema 4D installed for this user?"
        Write-Host "    Copy the OctaneLightDenoiser folder into your C4D plugins folder manually."
        return
    }

    $count = 0
    Get-ChildItem $maxon -Directory | Where-Object {
        (Test-Path (Join-Path $_.FullName 'plugins')) -or (Test-Path (Join-Path $_.FullName 'prefs'))
    } | ForEach-Object {
        $pluginsDir = Join-Path $_.FullName 'plugins'
        New-Item -ItemType Directory -Force $pluginsDir | Out-Null
        $dest = Join-Path $pluginsDir 'OctaneLightDenoiser'
        if (Test-Path $dest) { Remove-Item $dest -Recurse -Force }
        Copy-Item $plugin $dest -Recurse -Force
        Write-Host " installed -> $pluginsDir"
        $count++
    }

    Write-Host ""
    if ($count -gt 0) {
        Write-Host "[OK] Installed into $count Cinema 4D location(s)."
        Write-Host "     Restart Cinema 4D -> Extensions menu -> Octane Light Denoiser"
    } else {
        Write-Host "[!] No Cinema 4D folders detected under '$maxon'."
        Write-Host "    Copy the OctaneLightDenoiser folder into your C4D plugins folder manually."
    }
}
finally {
    Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue
}
