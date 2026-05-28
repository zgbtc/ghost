# 强制关闭所有 Chrome，然后以调试模式启动
Write-Host "关闭所有 Chrome 进程..." -ForegroundColor Yellow
Get-Process -Name "chrome" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# 确认已关闭
$remaining = Get-Process -Name "chrome" -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "强制终止残留进程..." -ForegroundColor Yellow
    $remaining | Stop-Process -Force
    Start-Sleep -Seconds 2
}

Write-Host "以调试模式启动 Chrome..." -ForegroundColor Green
$chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
$args = "--remote-debugging-port=9222 --no-first-run --no-default-browser-check --disable-background-networking"
Start-Process -FilePath $chromePath -ArgumentList $args

Start-Sleep -Seconds 4

# 验证端口
$port = netstat -ano | Select-String "9222"
if ($port) {
    Write-Host "✓ 调试端口 9222 已开启！" -ForegroundColor Green
    Write-Host $port
} else {
    Write-Host "✗ 端口未开启，尝试直接访问..." -ForegroundColor Red
    try {
        $resp = Invoke-WebRequest -Uri "http://127.0.0.1:9222/json" -TimeoutSec 3
        Write-Host "✓ Chrome 调试接口响应正常" -ForegroundColor Green
        Write-Host $resp.Content
    } catch {
        Write-Host "✗ 无法连接调试接口: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "请在打开的 Chrome 里访问 x.com 并确认已登录" -ForegroundColor Cyan
Write-Host "然后运行: python twitter_chrome.py" -ForegroundColor Cyan
