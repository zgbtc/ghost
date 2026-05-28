# Ghost Agent 一键安装脚本
# 用法：在源码目录里右键 -> 用 PowerShell 运行
# 或者 PowerShell 里执行：.\安装.ps1

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# 源码目录 = 本脚本所在目录
$SrcDir = $PSScriptRoot

Write-Host ""
Write-Host "  Ghost Agent 一键安装" -ForegroundColor Cyan
Write-Host "  源码目录: $SrcDir" -ForegroundColor DarkGray
Write-Host ""

# ── 1. 允许脚本执行 ──────────────────────────────────────────
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
Write-Host "✓ 脚本执行权限已开启" -ForegroundColor Green

# ── 2. 安装 Ghost ─────────────────────────────────────────────
Write-Host "→ 开始安装（约 3-5 分钟，需要联网）..." -ForegroundColor Cyan
& "$SrcDir\scripts\install-ghost-local.ps1" -SourceDir $SrcDir
Write-Host "✓ Ghost 安装完成" -ForegroundColor Green

# ── 3. 复制配置文件 ───────────────────────────────────────────
$hermesHome = "$env:USERPROFILE\.hermes"
New-Item -ItemType Directory -Path $hermesHome -Force | Out-Null

Copy-Item "$SrcDir\ghost_hermes.env"  "$hermesHome\.env"   -Force
Copy-Item "$SrcDir\ghost_config.yaml" "$hermesHome\config.yaml" -Force
Write-Host "✓ 配置文件已复制到 $hermesHome" -ForegroundColor Green

# ── 4. 创建快捷命令 g ─────────────────────────────────────────
$binDir = "$env:USERPROFILE\bin"
New-Item -ItemType Directory -Path $binDir -Force | Out-Null

@"
@echo off
cd /d "$SrcDir"
.venv\Scripts\python.exe -m hermes_cli.main %*
"@ | Out-File "$binDir\g.cmd" -Encoding ASCII

# 加入 PATH（如果还没有）
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if ($userPath -notlike "*$binDir*") {
    [Environment]::SetEnvironmentVariable("PATH", "$binDir;$userPath", "User")
}
Write-Host "✓ 快捷命令 g 已创建" -ForegroundColor Green

# ── 完成 ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "══════════════════════════════════" -ForegroundColor Cyan
Write-Host "  安装完成！" -ForegroundColor Green
Write-Host "══════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "  重新打开 PowerShell，然后输入：" -ForegroundColor White
Write-Host ""
Write-Host "      g" -ForegroundColor Yellow
Write-Host ""
Write-Host "  即可启动 Ghost" -ForegroundColor White
Write-Host ""

Read-Host "按回车键关闭"
