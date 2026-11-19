<#
.SYNOPSIS
  Đồng bộ các bản chép PROMPT-CHUNG.md trong repo với bản chuẩn (canonical) mà agent đọc thật.

.DESCRIPTION
  Bản chuẩn nằm ngoài repo (thư mục prompt của Agent Studio). Hai bản chép trong repo (docs\ và NhatKyCongViec\promt\) chỉ để lưu
  lịch sử bằng git; sửa bản chuẩn xong thì chạy script này, rồi commit nếu có thay đổi.
  -Check: chỉ so sánh, không ghi; thoát mã 1 nếu có bản lệch.
#>
param(
    [string]$Source = 'C:\AgentControl\studio-state\prompts\PROMPT-CHUNG.md',
    [switch]$Check
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$copies = @('docs\PROMPT-CHUNG.md', 'NhatKyCongViec\promt\PROMPT-CHUNG.md') | ForEach-Object { Join-Path $repo $_ }
if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Không thấy bản chuẩn: $Source" }
$want = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
$drift = 0
foreach ($copy in $copies) {
    $have = if (Test-Path -LiteralPath $copy) { (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash } else { '' }
    if ($have -eq $want) { Write-Host "ĐÚNG  $copy"; continue }
    $drift++
    if ($Check) { Write-Host "LỆCH  $copy"; continue }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $copy) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $copy -Force
    Write-Host "ĐÃ CHÉP  $copy"
}
if ($Check -and $drift) { exit 1 }
