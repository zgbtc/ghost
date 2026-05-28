# ============================================================================
# Ghost Agent — Local Install (no internet needed for clone)
# ============================================================================
# Use this when GitHub HTTPS is blocked.
# Copy the ghost source folder to the target machine first, then run this.
#
# Usage (from inside the ghost source folder):
#   .\scripts\install-ghost-local.ps1
#
# Or specify source path:
#   .\scripts\install-ghost-local.ps1 -SourceDir "D:\ghost-source"
# ============================================================================

param(
    [string]$SourceDir = (Split-Path $PSScriptRoot -Parent),
    [string]$GhostHome = "$env:USERPROFILE\.ghost",
    [string]$InstallDir = "$env:LOCALAPPDATA\ghost\ghost-agent",
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new() } catch {}

function Info($msg)    { Write-Host "✓ $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Section($msg) { Write-Host "`n── $msg ──" -ForegroundColor Cyan }

Write-Host ""
Write-Host "  Ghost Agent — Local Install" -ForegroundColor Green
Write-Host "  Source: $SourceDir" -ForegroundColor Cyan
Write-Host ""

# ── Check uv ─────────────────────────────────────────────────────────
Section "Checking dependencies"

$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Info "Installing uv..."
    $uvInstaller = "$env:TEMP\uv-installer.ps1"
    Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $uvInstaller
    & $uvInstaller
    $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:LOCALAPPDATA\uv\bin;$env:PATH"
}
Info "uv: $(uv --version)"

# ── Copy source to install dir ────────────────────────────────────────
Section "Installing Ghost"

if ($SourceDir -eq $InstallDir) {
    Info "Already in install directory, skipping copy"
} else {
    $installParent = Split-Path $InstallDir -Parent
    New-Item -ItemType Directory -Path $installParent -Force | Out-Null

    if (Test-Path $InstallDir) {
        Info "Removing old installation..."
        Remove-Item -Recurse -Force $InstallDir
    }

    Info "Copying Ghost source to $InstallDir"
    Copy-Item -Recurse -Path $SourceDir -Destination $InstallDir
    Info "Copy complete"
}

Set-Location $InstallDir

# ── Create venv + install ─────────────────────────────────────────────
Section "Setting up Python environment"

uv venv .venv --python 3.11 --quiet
Info "Python 3.11 venv created"

Info "Installing Ghost + dependencies (this takes ~2 min, needs internet for pip)..."
uv pip install -e ".[cron,cli,pty,mcp]" --quiet
Info "Core dependencies installed"

# Desktop control
uv pip install pyautogui mss pyperclip pygetwindow --quiet
Info "Desktop control: pyautogui + mss + pygetwindow"

try {
    uv pip install pywin32 --quiet
    Info "pywin32 installed"
} catch {
    Warn "pywin32 optional — skipped"
}

# ── Playwright browser ────────────────────────────────────────────────
if (-not $SkipBrowser) {
    Section "Setting up stealth browser"
    uv pip install playwright --quiet
    Info "Playwright installed. To install Chromium browser later, run:"
    Info "  playwright install chromium"
    Info "  (or use a mirror: PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright playwright install chromium)"
}

# ── Create ghost.cmd ──────────────────────────────────────────────────
Section "Creating ghost command"

$ghostBinDir = "$env:LOCALAPPDATA\ghost\bin"
New-Item -ItemType Directory -Path $ghostBinDir -Force | Out-Null

@"
@echo off
set GHOST_HOME=%GHOST_HOME%
if "%GHOST_HOME%"=="" set GHOST_HOME=$GhostHome
cd /d "$InstallDir"
.venv\Scripts\python.exe -m hermes_cli.main %*
"@ | Out-File -FilePath "$ghostBinDir\ghost.cmd" -Encoding ASCII

@"
@echo off
set GHOST_HOME=%GHOST_HOME%
if "%GHOST_HOME%"=="" set GHOST_HOME=$GhostHome
cd /d "$InstallDir"
.venv\Scripts\python.exe -m hermes_cli.main %*
"@ | Out-File -FilePath "$ghostBinDir\hermes.cmd" -Encoding ASCII

Info "ghost.cmd created"

# ── PATH + env vars ───────────────────────────────────────────────────
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$ghostBinDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$ghostBinDir;$userPath", "User")
    $env:PATH = "$ghostBinDir;$env:PATH"
    Info "Added to PATH"
}
[Environment]::SetEnvironmentVariable("GHOST_HOME", $GhostHome, "User")
$env:GHOST_HOME = $GhostHome

# ── Ghost data dirs ───────────────────────────────────────────────────
foreach ($d in @("skills","failures","sessions","demonstrations")) {
    New-Item -ItemType Directory -Path "$GhostHome\$d" -Force | Out-Null
}

# ── Done ──────────────────────────────────────────────────────────────
Section "Done"
Write-Host ""
Write-Host "Ghost installed!" -ForegroundColor Green
Write-Host ""
Write-Host "Restart PowerShell, then:" -ForegroundColor Cyan
Write-Host "  1. Set API key:  `$env:ANTHROPIC_API_KEY = 'sk-ant-...'"
Write-Host "  2. Run setup:    ghost setup"
Write-Host "  3. Start Ghost:  ghost"
Write-Host ""
