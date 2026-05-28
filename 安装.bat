@echo off
chcp 65001 >nul
echo.
echo   Ghost Agent 一键安装
echo   双击运行即可
echo.
powershell -ExecutionPolicy Bypass -File "%~dp0安装.ps1"
