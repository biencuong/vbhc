# ===========================================================================
# vbhc local thin-MCP uninstaller (Phase 3 — v1.0)
# ===========================================================================
# Usage:
#   1-liner:    iwr https://mcp.hagiang.edu.vn/uninstall.ps1 | iex
#   Params:     & ([scriptblock]::Create((iwr https://mcp.hagiang.edu.vn/uninstall.ps1).Content)) `
#                   -KeepConfig
#   Local file: powershell -ExecutionPolicy Bypass -File uninstall.ps1
#
# What it does:
#   1. Remove entry MCP `vbhc` từ Claude Code (claude mcp remove)
#   2. Xoá $env:LOCALAPPDATA\vbhc\ (venv + repo)
#   3. Tùy chọn xoá $env:USERPROFILE\.vbhc\ (config + cache) — mặc định GIỮ
#
# Sử dụng -KeepConfig để giữ ~/.vbhc/ (config + cache) khi gỡ.
# Sử dụng -PurgeAll  để xoá luôn ~/.vbhc/.
# ===========================================================================

[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "vbhc"),
    [string]$McpName    = "vbhc",
    [switch]$KeepConfig,
    [switch]$PurgeAll,
    [switch]$NonInteractive
)

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}
function Write-Ok([string]$msg)   { Write-Host "    [OK]   $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg){ Write-Host "    [WARN] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg)  { Write-Host "    [ERR]  $msg" -ForegroundColor Red }

function Test-CommandExists([string]$name) {
    $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host " vbhc local thin-MCP uninstaller" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

# --- Step 1: gỡ entry MCP với Claude Code --------------------------------

Write-Step "1. Gỡ MCP '$McpName' khỏi Claude Code"
if (Test-CommandExists "claude") {
    & claude mcp remove $McpName -s user 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Đã gỡ entry MCP"
    } else {
        Write-Warn2 "claude mcp remove báo non-zero exit (có thể entry không tồn tại — OK)"
    }
} else {
    Write-Warn2 "claude CLI không có — bỏ qua. Gỡ thủ công nếu cần (chỉnh ~/.claude.json)"
}

# --- Step 2: xoá install dir ---------------------------------------------

Write-Step "2. Xoá install dir"
Write-Host "    Target: $InstallDir"
if (Test-Path $InstallDir) {
    if (-not $NonInteractive) {
        $confirm = Read-Host "    Xoá '$InstallDir'? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Warn2 "Người dùng huỷ — giữ $InstallDir"
        } else {
            Remove-Item -Recurse -Force $InstallDir
            Write-Ok "Đã xoá $InstallDir"
        }
    } else {
        Remove-Item -Recurse -Force $InstallDir
        Write-Ok "Đã xoá $InstallDir"
    }
} else {
    Write-Warn2 "$InstallDir không tồn tại — bỏ qua"
}

# --- Step 3: xử lý ~/.vbhc/ (config + cache) -----------------------------

Write-Step "3. Xử lý ~/.vbhc/ (config + cache)"
$vbhcHome = Join-Path $env:USERPROFILE ".vbhc"
Write-Host "    Target: $vbhcHome"

if (-not (Test-Path $vbhcHome)) {
    Write-Warn2 "$vbhcHome không tồn tại — bỏ qua"
} elseif ($KeepConfig) {
    Write-Ok "Giữ $vbhcHome (-KeepConfig)"
} elseif ($PurgeAll) {
    Remove-Item -Recurse -Force $vbhcHome
    Write-Ok "Đã xoá $vbhcHome (-PurgeAll)"
} elseif (-not $NonInteractive) {
    Write-Host "    $vbhcHome chứa: config.yaml + cache (templates, rules)"
    $confirm = Read-Host "    Xoá luôn? (y/N — mặc định giữ để cài lại nhanh)"
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        Remove-Item -Recurse -Force $vbhcHome
        Write-Ok "Đã xoá $vbhcHome"
    } else {
        Write-Ok "Giữ $vbhcHome"
    }
} else {
    Write-Ok "Giữ $vbhcHome (mặc định cho non-interactive — dùng -PurgeAll để xoá)"
}

# --- Done ----------------------------------------------------------------

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " ✓ Đã gỡ vbhc" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Restart Claude Code để hoàn tất gỡ MCP entry." -ForegroundColor Cyan
Write-Host ""
