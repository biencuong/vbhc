# ===========================================================================
# vbhc local thin-MCP installer (Phase 3 — v1.0)
# ===========================================================================
# Usage:
#   1-liner:    iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
#   Params:     & ([scriptblock]::Create((iwr https://mcp.hagiang.edu.vn/install.ps1).Content)) `
#                   -CloudUrl https://mcp.hagiang.edu.vn -ApiKey vbhc_xxx -OrgId so-gddt-tuyen-quang
#   Local file: powershell -ExecutionPolicy Bypass -File install.ps1 -ApiKey vbhc_xxx
#
# What it does:
#   1. Verify Python 3.10+ (gợi ý cài nếu thiếu)
#   2. Tạo install dir tại $env:LOCALAPPDATA\vbhc\ (mặc định)
#   3. git clone https://github.com/biencuong/vbhc.git (fallback: tarball zip)
#   4. python -m venv + pip install mcp python-docx openpyxl pyyaml
#   5. Prompt URL/key/org (hoặc nhận qua params)
#   6. python -m mcp.bootstrap --url ... --key ... --org ...
#   7. Đăng ký MCP `vbhc` với Claude Code (claude mcp add) — overwrite entry cũ
#   8. Smoke test: bootstrap --status
# ===========================================================================

[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "vbhc"),
    [string]$CloudUrl   = "",
    [string]$ApiKey     = "",
    [string]$OrgId      = "",
    [string]$RepoUrl    = "https://github.com/biencuong/vbhc.git",
    [string]$Branch     = "main",
    [string]$McpName    = "vbhc",
    [switch]$NonInteractive,
    [switch]$SkipMcpRegister
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# --- Helpers ---------------------------------------------------------------

function Write-Step([string]$msg) {
    Write-Host ""
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Write-Ok([string]$msg)  { Write-Host "    [OK]   $msg" -ForegroundColor Green }
function Write-Warn2([string]$msg){ Write-Host "    [WARN] $msg" -ForegroundColor Yellow }
function Write-Err([string]$msg) { Write-Host "    [ERR]  $msg" -ForegroundColor Red }

function Test-CommandExists([string]$name) {
    $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Test-PythonOk([string]$exe, [string[]]$prefixArgs = @()) {
    # Trả về absolute path nếu $exe (với optional prefix args, vd 'py -3') là Python >= 3.10
    try {
        $verArgs = $prefixArgs + @("--version")
        $out = & $exe @verArgs 2>&1
        if ($out -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]; $minor = [int]$Matches[2]
            if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                $execArgs = $prefixArgs + @("-c", "import sys; print(sys.executable)")
                $resolved = (& $exe @execArgs 2>$null | Out-String).Trim()
                if ($resolved -and (Test-Path $resolved)) { return $resolved }
            }
        }
    } catch { }
    return $null
}

function Get-PythonExe {
    # Thử py -3, python, python3 — trả về absolute path đầu tiên là Python >= 3.10
    if (Test-CommandExists "py") {
        $p = Test-PythonOk -exe "py" -prefixArgs @("-3")
        if ($p) { return $p }
    }
    foreach ($cmd in @("python", "python3")) {
        if (Test-CommandExists $cmd) {
            $p = Test-PythonOk -exe $cmd
            if ($p) { return $p }
        }
    }
    return $null
}

function Read-PromptDefault([string]$label, [string]$default = "") {
    if ($NonInteractive) {
        if (-not $default) { throw "Non-interactive mode but no default for '$label'" }
        return $default
    }
    $suffix = if ($default) { " [$default]" } else { "" }
    $val = Read-Host "$label$suffix"
    if (-not $val) { return $default }
    return $val
}

# --- Step 1: banner + prereq --------------------------------------------

Write-Host ""
Write-Host "============================================================" -ForegroundColor Magenta
Write-Host " vbhc local thin-MCP installer" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Magenta

Write-Step "1. Kiểm tra Python 3.10+"
$pythonExe = Get-PythonExe
if (-not $pythonExe) {
    Write-Err "Không tìm thấy Python >= 3.10."
    Write-Host ""
    Write-Host "Cài Python:" -ForegroundColor Yellow
    Write-Host "  - Tải từ https://www.python.org/downloads/  (≥ 3.10)" -ForegroundColor Yellow
    Write-Host "  - Hoặc: winget install Python.Python.3.12" -ForegroundColor Yellow
    Write-Host "  - Nhớ tick 'Add python.exe to PATH' khi cài." -ForegroundColor Yellow
    exit 1
}
Write-Ok "Python: $pythonExe"
$pyVer = (& $pythonExe --version 2>&1).Trim()
Write-Ok $pyVer

# --- Step 2: install dir -------------------------------------------------

Write-Step "2. Chuẩn bị thư mục cài"
$repoDir = Join-Path $InstallDir "repo"
$venvDir = Join-Path $InstallDir "venv"
Write-Host "    InstallDir = $InstallDir"
Write-Host "    repoDir    = $repoDir"
Write-Host "    venvDir    = $venvDir"

if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    Write-Ok "Tạo $InstallDir"
} else {
    Write-Ok "$InstallDir đã tồn tại — sẽ update"
}

# --- Step 3: lấy repo (git clone hoặc tarball) ---------------------------

Write-Step "3. Lấy code repo"
$useGit = Test-CommandExists "git"

if (Test-Path $repoDir) {
    if ($useGit -and (Test-Path (Join-Path $repoDir ".git"))) {
        Write-Host "    Đã có repo, chạy git pull"
        Push-Location $repoDir
        try {
            git fetch --quiet origin $Branch
            git reset --hard "origin/$Branch" --quiet
            Write-Ok "Pulled $Branch tới HEAD origin"
        } finally { Pop-Location }
    } else {
        Write-Warn2 "$repoDir có sẵn nhưng không phải git repo — xoá để tải mới"
        Remove-Item -Recurse -Force $repoDir
    }
}

if (-not (Test-Path $repoDir)) {
    if ($useGit) {
        Write-Host "    git clone $RepoUrl"
        git clone --branch $Branch --depth 1 $RepoUrl $repoDir
        if ($LASTEXITCODE -ne 0) { throw "git clone thất bại" }
        Write-Ok "Cloned"
    } else {
        Write-Host "    git không có sẵn — tải tarball zip"
        $zipUrl = ($RepoUrl -replace "\.git$","") + "/archive/refs/heads/$Branch.zip"
        $tmpZip = Join-Path $env:TEMP "vbhc-$Branch.zip"
        Write-Host "    GET $zipUrl"
        Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip
        $tmpExtract = Join-Path $env:TEMP "vbhc-extract"
        if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract }
        Expand-Archive -Path $tmpZip -DestinationPath $tmpExtract
        # GitHub zip extracts to <repo>-<branch>/...
        $extractedRoot = Get-ChildItem $tmpExtract -Directory | Select-Object -First 1
        Move-Item -Path $extractedRoot.FullName -Destination $repoDir
        Remove-Item -Recurse -Force $tmpExtract, $tmpZip -ErrorAction SilentlyContinue
        Write-Ok "Đã giải nén tarball"
    }
}

# --- Step 4: venv + pip install ------------------------------------------

Write-Step "4. Tạo venv + cài dependencies"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $pythonExe -m venv $venvDir
    if ($LASTEXITCODE -ne 0) { throw "Tạo venv thất bại" }
    Write-Ok "venv tạo tại $venvDir"
} else {
    Write-Ok "venv đã có — bỏ qua"
}

Write-Host "    pip install (mcp, python-docx, openpyxl, pyyaml)..."
& $venvPython -m pip install --quiet --disable-pip-version-check --upgrade pip
& $venvPython -m pip install --quiet --disable-pip-version-check `
    "mcp" "python-docx" "openpyxl" "pyyaml" "uvicorn" "starlette"
if ($LASTEXITCODE -ne 0) { throw "pip install thất bại" }
Write-Ok "Dependencies installed"

# --- Step 5: prompt config -----------------------------------------------

Write-Step "5. Cấu hình kết nối cloud Knowledge Hub"
if (-not $CloudUrl) {
    $CloudUrl = Read-PromptDefault "Cloud URL" "https://mcp.hagiang.edu.vn"
}
if (-not $ApiKey)   {
    if ($NonInteractive) { throw "Non-interactive mode cần -ApiKey" }
    $ApiKey = Read-Host "API key (Bearer, định dạng vbhc_<64hex>)"
}
if (-not $OrgId)    {
    $OrgId = Read-PromptDefault "Org ID (tùy chọn, vd: so-gddt-tuyen-quang)" ""
}

Write-Host "    Cloud URL = $CloudUrl"
Write-Host "    Org ID    = $(if ($OrgId) { $OrgId } else { '(none)' })"
Write-Host "    API key   = $($ApiKey.Substring(0, [Math]::Min(12, $ApiKey.Length)))..."

# --- Step 6: bootstrap ----------------------------------------------------

Write-Step "6. Chạy bootstrap (ghi ~/.vbhc/config.yaml + sync assets)"
$bootstrapPy = Join-Path $repoDir "mcp\bootstrap.py"
if (-not (Test-Path $bootstrapPy)) { throw "Không tìm thấy $bootstrapPy" }
$bootstrapArgs = @($bootstrapPy, "--url", $CloudUrl, "--key", $ApiKey)
if ($OrgId) { $bootstrapArgs += @("--org", $OrgId) }

Push-Location $repoDir
try {
    $env:PYTHONIOENCODING = "utf-8"
    & $venvPython @bootstrapArgs
    if ($LASTEXITCODE -ne 0) { throw "Bootstrap thất bại — xem log ở trên" }
} finally { Pop-Location }
Write-Ok "Bootstrap done"

# --- Step 7: đăng ký MCP với Claude Code ---------------------------------

if (-not $SkipMcpRegister) {
    Write-Step "7. Đăng ký MCP '$McpName' với Claude Code"
    $serverPy = Join-Path $repoDir "mcp\server.py"
    if (-not (Test-Path $serverPy)) { throw "Không tìm thấy $serverPy" }

    if (Test-CommandExists "claude") {
        # Idempotent: gỡ entry cũ (nếu có) rồi add mới
        Write-Host "    claude mcp remove $McpName -s user  (idempotent)"
        & claude mcp remove $McpName -s user 2>$null | Out-Null

        Write-Host "    claude mcp add $McpName -s user -- $venvPython $serverPy"
        & claude mcp add $McpName -s user -- $venvPython $serverPy
        if ($LASTEXITCODE -ne 0) {
            Write-Warn2 "claude mcp add báo lỗi — bạn có thể đăng ký thủ công (xem cuối)"
        } else {
            Write-Ok "MCP '$McpName' đăng ký với Claude Code"
        }
    } else {
        Write-Warn2 "claude CLI không có — bỏ qua đăng ký tự động"
        Write-Host ""
        Write-Host "  Đăng ký thủ công cho Claude Desktop:" -ForegroundColor Yellow
        $cfgPath = Join-Path $env:APPDATA "Claude\claude_desktop_config.json"
        Write-Host "  Edit $cfgPath và thêm:" -ForegroundColor Yellow
        Write-Host @"
    {
      "mcpServers": {
        "$McpName": {
          "command": "$($venvPython -replace '\\','\\\\')",
          "args": ["$($serverPy -replace '\\','\\\\')"]
        }
      }
    }
"@ -ForegroundColor Yellow
    }
} else {
    Write-Warn2 "Bỏ qua đăng ký MCP (-SkipMcpRegister)"
}

# --- Step 8: smoke test ---------------------------------------------------

Write-Step "8. Smoke test"
Push-Location $repoDir
try {
    & $venvPython $bootstrapPy --status
} finally { Pop-Location }

Write-Host ""
Write-Host "============================================================" -ForegroundColor Green
Write-Host " ✓ Cài đặt vbhc hoàn tất" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Bước tiếp theo:" -ForegroundColor Cyan
Write-Host "  1. Restart Claude Code (đóng + mở lại) để load MCP mới"
Write-Host "  2. Trong chat thử: 'phân loại văn bản: báo cáo quý I'"
Write-Host "  3. Update knowledge: chạy 'claude mcp call vbhc vbhc_sync_knowledge'"
Write-Host ""
Write-Host "Gỡ cài đặt:  iwr $CloudUrl/uninstall.ps1 | iex"
Write-Host "Hoặc:        powershell -ExecutionPolicy Bypass -File '$repoDir\cloud\uninstall.ps1'"
Write-Host ""
