# ============================================================================
# Ghost Agent Installer for Windows (PowerShell)
# ============================================================================
#
# One-line install (run in PowerShell as Administrator or normal user):
#   iex (irm https://raw.githubusercontent.com/zgbtc/ghost/main/scripts/install-ghost.ps1)
#
# ============================================================================

param(
    [string]$GhostHome = "$env:USERPROFILE\.ghost",
    [string]$InstallDir = "$env:LOCALAPPDATA\ghost\ghost-agent",
    [switch]$SkipSetup,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Force UTF-8 output
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new() } catch {}

# ── Config ──────────────────────────────────────────────────────────
$RepoUrl = "https://github.com/zgbtc/ghost.git"
$PythonVersion = "3.11"

# ── Banner ───────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ██████╗ ██╗  ██╗ ██████╗ ███████╗████████╗" -ForegroundColor Green
Write-Host " ██╔════╝ ██║  ██║██╔═══██╗██╔════╝╚══██╔══╝" -ForegroundColor Green
Write-Host " ██║  ███╗███████║██║   ██║███████╗   ██║   " -ForegroundColor Green
Write-Host " ██║   ██║██╔══██║██║   ██║╚════██║   ██║   " -ForegroundColor Green
Write-Host " ╚██████╔╝██║  ██║╚██████╔╝███████║   ██║   " -ForegroundColor Green
Write-Host "  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   " -ForegroundColor Green
Write-Host ""
Write-Host "  Your digital twin with full computer control" -ForegroundColor Cyan
Write-Host ""

function Info($msg)    { Write-Host "✓ $msg" -ForegroundColor Green }
function Warn($msg)    { Write-Host "⚠ $msg" -ForegroundColor Yellow }
function Section($msg) { Write-Host "`n── $msg ──" -ForegroundColor Cyan }

# ── Check Windows version ────────────────────────────────────────────
$winVer = [System.Environment]::OSVersion.Version
Info "Windows $($winVer.Major).$($winVer.Minor) detected"

# ── Install uv ───────────────────────────────────────────────────────
Section "Checking dependencies"

$uvPath = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uvPath) {
    Info "Installing uv (fast Python package manager)..."
    $uvInstaller = "$env:TEMP\uv-installer.ps1"
    Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -OutFile $uvInstaller
    & $uvInstaller
    # Add uv to PATH for this session
    $env:PATH = "$env:USERPROFILE\.cargo\bin;$env:LOCALAPPDATA\uv\bin;$env:PATH"
}
$uvVersion = uv --version 2>&1
Info "uv: $uvVersion"

# ── Check git ────────────────────────────────────────────────────────
$gitPath = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitPath) {
    Info "Installing Git for Windows (portable)..."
    $gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.47.0.windows.1/MinGit-2.47.0-64-bit.zip"
    $gitZip = "$env:TEMP\mingit.zip"
    $gitDir = "$env:LOCALAPPDATA\ghost\git"
    Invoke-WebRequest -Uri $gitUrl -OutFile $gitZip
    Expand-Archive -Path $gitZip -DestinationPath $gitDir -Force
    $env:PATH = "$gitDir\cmd;$env:PATH"
    Info "Git installed (portable)"
}
$gitVersion = git --version 2>&1
Info "git: $gitVersion"

# ── Clone / update repo ──────────────────────────────────────────────
Section "Installing Ghost"

$installParent = Split-Path $InstallDir -Parent
if (-not (Test-Path $installParent)) {
    New-Item -ItemType Directory -Path $installParent -Force | Out-Null
}

if (Test-Path "$InstallDir\.git") {
    Info "Updating existing installation at $InstallDir"
    git -C $InstallDir pull --ff-only origin main 2>&1 | Out-Null
} else {
    Info "Cloning Ghost to $InstallDir"
    git clone --depth=1 $RepoUrl $InstallDir
}

Set-Location $InstallDir

# ── Create venv + install ────────────────────────────────────────────
Section "Setting up Python environment"

uv venv .venv --python $PythonVersion --quiet
Info "Python venv created"

Info "Installing Ghost + dependencies (this takes ~2 min)..."
uv pip install -e ".[all,ghost-desktop-windows]" --quiet

# Windows-specific desktop extras
uv pip install pyautogui mss pyperclip pygetwindow --quiet
Info "Windows desktop control: pyautogui + mss + pygetwindow installed"

# Try pywin32 for advanced window control
try {
    uv pip install pywin32 --quiet
    Info "pywin32 installed (advanced window control)"
} catch {
    Warn "pywin32 install failed — basic window control only"
}

# ── Install Playwright (stealth browser) ─────────────────────────────
if (-not $SkipBrowser) {
    Section "Setting up stealth browser"
    uv pip install playwright --quiet
    try {
        .\.venv\Scripts\python.exe -m playwright install chromium 2>&1 | Out-Null
        Info "Stealth browser (Playwright + Chromium) ready"
    } catch {
        Warn "Playwright browser install failed — browser tools will be unavailable"
    }
}

# ── Create ghost command ──────────────────────────────────────────────
Section "Creating ghost command"

# Create launcher script in a directory on PATH
$ghostBinDir = "$env:LOCALAPPDATA\ghost\bin"
New-Item -ItemType Directory -Path $ghostBinDir -Force | Out-Null

$launcherContent = @"
@echo off
set GHOST_HOME=%GHOST_HOME%
if "%GHOST_HOME%"=="" set GHOST_HOME=$GhostHome
cd /d "$InstallDir"
.venv\Scripts\python.exe -m hermes_cli.main %*
"@
$launcherContent | Out-File -FilePath "$ghostBinDir\ghost.cmd" -Encoding ASCII

# Also create hermes.cmd alias
$launcherContent -replace "ghost", "hermes" | Out-File -FilePath "$ghostBinDir\hermes.cmd" -Encoding ASCII

Info "ghost.cmd created at $ghostBinDir"

# ── Add to PATH ───────────────────────────────────────────────────────
Section "Configuring PATH"

$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$ghostBinDir*") {
    [Environment]::SetEnvironmentVariable(
        "PATH",
        "$ghostBinDir;$userPath",
        "User"
    )
    $env:PATH = "$ghostBinDir;$env:PATH"
    Info "Added $ghostBinDir to user PATH"
}

# Set GHOST_HOME
[Environment]::SetEnvironmentVariable("GHOST_HOME", $GhostHome, "User")
$env:GHOST_HOME = $GhostHome
Info "GHOST_HOME set to $GhostHome"

# ── Create .ghost directory ───────────────────────────────────────────
$dirs = @("skills", "failures", "sessions", "demonstrations")
foreach ($d in $dirs) {
    New-Item -ItemType Directory -Path "$GhostHome\$d" -Force | Out-Null
}
Info "Ghost data directory: $GhostHome"

# ── Done ──────────────────────────────────────────────────────────────
Section "Installation complete"

Write-Host ""
Write-Host "Ghost is installed!" -ForegroundColor Green -NoNewline
Write-Host " Restart your terminal, then:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Set your API key:" -ForegroundColor Cyan
Write-Host "     `$env:ANTHROPIC_API_KEY = 'sk-ant-...'" -ForegroundColor White
Write-Host "     Or add it to: $GhostHome\.env" -ForegroundColor White
Write-Host ""
Write-Host "  2. Run setup:" -ForegroundColor Cyan
Write-Host "     ghost setup" -ForegroundColor White
Write-Host ""
Write-Host "  3. Start Ghost:" -ForegroundColor Cyan
Write-Host "     ghost" -ForegroundColor White
Write-Host ""

if (-not $SkipSetup -and [Environment]::UserInteractive) {
    $answer = Read-Host "Run 'ghost setup' now? [Y/n]"
    if ($answer -eq "" -or $answer -match "^[Yy]") {
        & "$ghostBinDir\ghost.cmd" setup
    }
}
