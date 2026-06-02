# Twitter X 增长引擎 - 一键安装脚本
# 适用于 Windows 10/11
# 运行方式：右键 -> 用 PowerShell 运行

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "🤖 Twitter X 增长引擎 - 一键安装" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# 设置错误处理
$ErrorActionPreference = "Stop"

# 1. 检查 Python
Write-Host "[1/7] 检查 Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.(1[0-9]|[2-9][0-9])") {
        Write-Host "✅ Python 已安装: $pythonVersion" -ForegroundColor Green
    } else {
        throw "Python 版本过低"
    }
} catch {
    Write-Host "❌ Python 未安装或版本过低（需要 3.10+）" -ForegroundColor Red
    Write-Host "请访问: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "下载并安装，记得勾选 'Add Python to PATH'" -ForegroundColor Yellow
    pause
    exit 1
}

# 2. 检查 Git
Write-Host "[2/7] 检查 Git..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    Write-Host "✅ Git 已安装: $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Git 未安装" -ForegroundColor Red
    Write-Host "请访问: https://git-scm.com/download/win" -ForegroundColor Yellow
    Write-Host "下载并安装" -ForegroundColor Yellow
    pause
    exit 1
}

# 3. 克隆项目
Write-Host "[3/7] 克隆项目..." -ForegroundColor Yellow
$installPath = "$env:USERPROFILE\ghost"

if (Test-Path $installPath) {
    Write-Host "⚠️  目录已存在: $installPath" -ForegroundColor Yellow
    $response = Read-Host "是否删除并重新安装? (y/n)"
    if ($response -eq 'y' -or $response -eq 'Y') {
        Remove-Item -Recurse -Force $installPath
    } else {
        Write-Host "取消安装" -ForegroundColor Red
        exit 0
    }
}

try {
    Write-Host "正在克隆 GitHub 仓库..." -ForegroundColor Cyan
    git clone https://github.com/zgbtc/ghost.git $installPath
    Write-Host "✅ 项目克隆完成" -ForegroundColor Green
} catch {
    Write-Host "❌ 克隆失败: $_" -ForegroundColor Red
    Write-Host "提示: 可能是网络问题，可以手动下载ZIP：" -ForegroundColor Yellow
    Write-Host "https://github.com/zgbtc/ghost/archive/refs/heads/master.zip" -ForegroundColor Yellow
    pause
    exit 1
}

# 4. 运行安装脚本
Write-Host "[4/7] 安装依赖..." -ForegroundColor Yellow
$projectPath = "$installPath\NousResearch-hermes-agent-4117fc3"

if (-not (Test-Path $projectPath)) {
    Write-Host "❌ 项目目录不存在: $projectPath" -ForegroundColor Red
    exit 1
}

Set-Location $projectPath

try {
    Write-Host "正在安装 Ghost（需要3-5分钟）..." -ForegroundColor Cyan
    powershell -ExecutionPolicy Bypass -File ".\安装.ps1"
    Write-Host "✅ Ghost 安装完成" -ForegroundColor Green
} catch {
    Write-Host "❌ 安装失败: $_" -ForegroundColor Red
    pause
    exit 1
}

# 5. 配置 API Key
Write-Host "[5/7] 配置 API Key..." -ForegroundColor Yellow
$envFile = "$env:USERPROFILE\.hermes\.env"

if (Test-Path $envFile) {
    Write-Host "⚠️  配置文件已存在" -ForegroundColor Yellow
    $response = Read-Host "是否覆盖? (y/n)"
    if ($response -ne 'y' -and $response -ne 'Y') {
        Write-Host "跳过配置" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        Write-Host "⚠️  请手动配置 API Key" -ForegroundColor Yellow
        Write-Host "编辑文件: $envFile" -ForegroundColor Yellow
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        goto SkipAPIConfig
    }
}

# 复制配置模板
Copy-Item ".\ghost_hermes.env" $envFile -Force

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "📝 选择 AI 模型提供商" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "1. Groq（推荐，免费最快）"
Write-Host "   https://console.groq.com"
Write-Host ""
Write-Host "2. 阿里云百炼（国内稳定）"
Write-Host "   https://bailian.console.aliyun.com"
Write-Host ""
Write-Host "3. 智谱GLM（免费）"
Write-Host "   https://open.bigmodel.cn"
Write-Host ""
$provider = Read-Host "请选择 (1/2/3)"

$apiKey = Read-Host "请输入 API Key"

if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "⚠️  未输入 API Key，需要稍后手动配置" -ForegroundColor Yellow
    Write-Host "编辑文件: $envFile" -ForegroundColor Yellow
} else {
    $envContent = Get-Content $envFile

    switch ($provider) {
        "1" {
            $envContent = $envContent -replace "GROQ_API_KEY=.*", "GROQ_API_KEY=$apiKey"
            $envContent = $envContent -replace "DEFAULT_MODEL=.*", "DEFAULT_MODEL=groq/llama-3.3-70b-versatile"
            $envContent = $envContent -replace "# GROQ_API_BASE=.*", "GROQ_API_BASE=https://api.groq.com/openai/v1"
        }
        "2" {
            $envContent = $envContent -replace "OPENAI_API_KEY=.*", "OPENAI_API_KEY=$apiKey"
            $envContent = $envContent -replace "DEFAULT_MODEL=.*", "DEFAULT_MODEL=qwen-turbo"
            $envContent = $envContent -replace "# OPENAI_API_BASE=.*", "OPENAI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1"
        }
        "3" {
            $envContent = $envContent -replace "OPENAI_API_KEY=.*", "OPENAI_API_KEY=$apiKey"
            $envContent = $envContent -replace "DEFAULT_MODEL=.*", "DEFAULT_MODEL=glm-4-flash"
            $envContent = $envContent -replace "# OPENAI_API_BASE=.*", "OPENAI_API_BASE=https://open.bigmodel.cn/api/paas/v4/"
        }
        default {
            Write-Host "⚠️  无效选择，使用默认配置" -ForegroundColor Yellow
        }
    }

    $envContent | Set-Content $envFile
    Write-Host "✅ API Key 配置完成" -ForegroundColor Green
}

:SkipAPIConfig

# 6. 创建 Chrome 调试快捷方式
Write-Host "[6/7] 配置 Chrome 调试模式..." -ForegroundColor Yellow

$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chromePath)) {
    $chromePath = "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
}

if (Test-Path $chromePath) {
    $shortcutPath = "$env:USERPROFILE\Desktop\Chrome调试模式.lnk"
    
    $WScriptShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WScriptShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = $chromePath
    $Shortcut.Arguments = "--remote-debugging-port=9222 --user-data-dir=`"$env:USERPROFILE\ChromeDebug`""
    $Shortcut.Save()
    
    Write-Host "✅ 已创建桌面快捷方式: Chrome调试模式.lnk" -ForegroundColor Green
    Write-Host "   请使用此快捷方式启动 Chrome 并登录 Twitter" -ForegroundColor Yellow
} else {
    Write-Host "⚠️  未找到 Chrome，请手动安装" -ForegroundColor Yellow
    Write-Host "   下载: https://www.google.com/chrome/" -ForegroundColor Yellow
}

# 7. 完成
Write-Host "[7/7] 安装完成！" -ForegroundColor Yellow
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✅ 安装成功！" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "📝 下一步操作：" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. 启动 Chrome 调试模式" -ForegroundColor White
Write-Host "   双击桌面快捷方式: Chrome调试模式.lnk" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 登录 Twitter/X" -ForegroundColor White
Write-Host "   访问: https://x.com/login" -ForegroundColor Gray
Write-Host "   ⚠️  必须开通 Premium 蓝V（8美元/月）" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. 配置 Twitter 引擎" -ForegroundColor White
Write-Host "   打开 PowerShell，运行：" -ForegroundColor Gray
Write-Host "   ghost 配置推特引擎" -ForegroundColor Cyan
Write-Host ""
Write-Host "4. 启动引擎" -ForegroundColor White
Write-Host "   ghost 启动推特引擎" -ForegroundColor Cyan
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Host "💡 提示：需要重启 PowerShell 才能使用 ghost 命令" -ForegroundColor Yellow
Write-Host ""

# 询问是否立即配置
$response = Read-Host "是否现在配置 Twitter 引擎? (y/n)"
if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host ""
    Write-Host "正在启动配置向导..." -ForegroundColor Cyan
    
    # 刷新环境变量
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","Machine")
    
    # 启动配置
    & python -m hermes 配置推特引擎
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
