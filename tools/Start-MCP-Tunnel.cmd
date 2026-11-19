@echo off
title MCP Tunnel - Agent Studio
color 0A
echo.
echo  ========================================
echo   Agent Studio - MCP Tunnel
echo  ========================================
echo.
echo  Token lay trong studio.json  ^>  mcp_server.token
echo.

set "CLOUDFLARED=%~dp0cloudflared.exe"

if not exist "%CLOUDFLARED%" (
    echo  [!] Chua co cloudflared.exe - dang tu dong tai ve...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe' -OutFile '%CLOUDFLARED%' -UseBasicParsing; Write-Host 'Tai xong.'"
    echo.
)

if not exist "%CLOUDFLARED%" (
    echo  [LOI] Tai that bai. Kiem tra mang va thu lai.
    pause
    exit /b 1
)

echo  Dang mo tunnel... cho URL hien ra o dong:
echo  "Your quick Tunnel has been created! Visit it at..."
echo.
echo  Copy URL do vao Gemini / Claude Desktop.
echo  De dung: Ctrl+C
echo.

"%CLOUDFLARED%" tunnel --url http://127.0.0.1:8765
pause
