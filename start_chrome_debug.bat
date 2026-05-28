@echo off
echo 关闭所有 Chrome 进程...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 /nobreak >nul

echo 以调试模式启动 Chrome...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --no-first-run

echo Chrome 已启动，调试端口: 9222
echo 请在 Chrome 里打开 Twitter 并确认已登录
pause
