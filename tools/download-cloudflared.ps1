# Download cloudflared.exe vao thu muc tools/
# Chay: powershell -ExecutionPolicy Bypass -File tools\download-cloudflared.ps1

$dest = Join-Path $PSScriptRoot "cloudflared.exe"

if (Test-Path $dest) {
    Write-Host "Da co: $dest"
    Write-Host "Muon tai lai thi xoa file cu roi chay lai script nay."
    exit 0
}

$url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
Write-Host "Dang tai cloudflared tu GitHub..."
Write-Host "  URL : $url"
Write-Host "  Luu : $dest"

try {
    Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
    Write-Host "Hoan tat! Da luu tai: $dest"
} catch {
    Write-Error "Tai that bai: $_"
    exit 1
}
