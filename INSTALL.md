# Cài đặt & Triển khai MCP `vbhc`

Hướng dẫn từ máy chưa có gì → MCP `vbhc` chạy được trong AI agent (Claude Code, qwenpaw, Cursor, Cline...).

## Mục lục

- [Yêu cầu hệ thống](#yêu-cầu-hệ-thống)
- [Kiến trúc 3 tier](#kiến-trúc-3-tier-storage)
- [**Scenario A** — Cài cho cá nhân / 1 máy (đơn giản nhất)](#scenario-a--cài-cho-cá-nhân--1-máy)
- [**Scenario B** — Triển khai cho phòng/Sở dùng chung 1 server](#scenario-b--triển-khai-cho-phòngsở-dùng-chung-1-server)
  - [4A. LAN-only](#4a-lan-only-đơn-giản)
  - [**4B. Public domain qua aaPanel** (chi tiết, cho người mới)](#4b-public-domain-qua-aapanel-chi-tiết-cho-người-mới)
  - [4C. Manual nginx + Let's Encrypt](#4c-manual-nginx--lets-encrypt-advanced-không-dùng-aapanel)
- [**Scenario C** — Cho developer (dev mode)](#scenario-c--cho-developer-dev-mode)
- [Cấu hình client (JSON cho từng agent)](#cấu-hình-client)
- [Verify đã cài đúng](#verify-đã-cài-đúng)
- [Troubleshooting](#troubleshooting)
- [Cập nhật khi có version mới](#cập-nhật-khi-có-version-mới)

---

## Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|---|---|
| Python | ≥ 3.10 (kiểm tra: `python --version`) |
| OS | Windows 10/11, macOS, Linux |
| RAM/Disk | < 100MB cho server (lightweight) |
| Network | Chỉ cần khi deploy HTTP server (Scenario B) |
| Microsoft Word | Không bắt buộc (server chỉ tạo .docx; nếu cần mở/sửa file đang mở → cần Word + word-mcp-live) |

Cài thư viện Python (1 lần):

```bash
pip install mcp python-docx openpyxl pyyaml
```

Verify:
```bash
python -c "import mcp, docx, openpyxl, yaml; print('OK')"
```

> **Linux (Debian/Ubuntu 23.04+, Python 3.11+):** lệnh `pip install` thẳng sẽ báo lỗi
> `error: externally-managed-environment` (PEP 668). **Phải dùng venv** — xem
> [Scenario B](#scenario-b--triển-khai-cho-phòngsở-dùng-chung-1-server) hoặc:
>
> ```bash
> sudo apt install -y python3-full python3-venv
> python3 -m venv ~/.vbhc-venv
> ~/.vbhc-venv/bin/pip install mcp python-docx openpyxl pyyaml
> # Sau đó chạy server bằng ~/.vbhc-venv/bin/python thay vì python3
> ```
>
> macOS/Windows thường không có ràng buộc này; nếu gặp tương tự thì cũng dùng venv.

---

## Kiến trúc 3 tier storage

MCP `vbhc` chia dữ liệu thành 3 tier riêng biệt — quan trọng để hiểu trước khi cài:

```
┌──────────────────────────────────────────────────────┐
│ TIER 1: SKILL (code, read-only, share trên git)      │
│   D:\SKILL_AI\skills\soan-thao-vbhc\                 │
│   ├── SKILL.md, scripts/, mcp/, resources/           │
│   └── tri-thuc-template/  ← template cho ORG dir     │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ TIER 2: ORG (cấu hình chung cơ quan, share nội bộ)   │
│   $VBHC_ORG_DIR (default: ~/.vbhc/org/)              │
│   ├── 05-thong-tin-co-quan.yaml  (tên, người ký...)  │
│   ├── phan-cong-nhiem-vu.yaml    (gợi ý nơi nhận)    │
│   └── can-cu-phap-ly-mau.yaml    (VB pháp lý mẫu)    │
└──────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────┐
│ TIER 3: USER (file công việc, riêng từng máy)        │
│   <user chọn>\cong-viec\<NNNN>-<mô-tả>\              │
│   ├── 0-ky-thuat\   (1-yeu-cau.md, 2-du-lieu.yaml)   │
│   ├── 1-tham-chieu\ (file PDF/docx user đưa vào)     │
│   └── <san-pham>.docx                                │
└──────────────────────────────────────────────────────┘
```

**Tại sao tách 3 tier?**

| Vấn đề | Cách giải quyết |
|---|---|
| Update skill mà không đụng dữ liệu user | Skill dir read-only |
| Nhiều cán bộ cùng cơ quan dùng chung config | ORG dir share trên file server hoặc git |
| Đa cơ quan dùng cùng 1 codebase | Mỗi cơ quan có ORG dir riêng (env var) |
| Bảo mật file công việc cá nhân | USER dir trên máy user, không upload server |

---

## Scenario A — Cài cho cá nhân / 1 máy

**Phù hợp khi:** 1 cán bộ dùng MCP trên máy cá nhân, không share.

### Bước 1 — Tải skill về máy

```powershell
# Windows
git clone <repo-url> D:\SKILL_AI\skills\soan-thao-vbhc
# Hoặc download zip → giải nén vào D:\SKILL_AI\skills\soan-thao-vbhc\
```

### Bước 2 — Cài Python deps

```powershell
pip install mcp python-docx openpyxl pyyaml
```

### Bước 3 — Tạo ORG dir + copy template

```powershell
# Windows PowerShell
New-Item -ItemType Directory -Path "$HOME\.vbhc\org" -Force
Copy-Item "D:\SKILL_AI\skills\soan-thao-vbhc\tri-thuc-template\*.yaml" `
          -Destination "$HOME\.vbhc\org\"
```

```bash
# macOS / Linux
mkdir -p ~/.vbhc/org
cp /path/to/skills/soan-thao-vbhc/tri-thuc-template/*.yaml ~/.vbhc/org/
```

### Bước 4 — Sửa file YAML cho cơ quan của bạn

Mở 3 file trong ORG dir bằng VS Code/Notepad++ và điền:

| File | Nội dung cần sửa |
|---|---|
| `05-thong-tin-co-quan.yaml` | Tên cơ quan, chủ quản, địa danh, danh sách người ký, danh sách phòng |
| `phan-cong-nhiem-vu.yaml` | Danh sách phòng/đơn vị + chức năng nhiệm vụ (để AI gợi ý nơi nhận) |
| `can-cu-phap-ly-mau.yaml` | (Tùy chọn) Liệt kê các Luật/NĐ/TT cơ quan thường viện dẫn |

> **Quan trọng:** Trong YAML, tên cơ quan UPPERCASE đúng quy ước NĐ 30 (vd: `"SỞ GIÁO DỤC VÀ ĐÀO TẠO"`). Người ký nhập đầy đủ họ tên có dấu.

### Bước 5 — Đăng ký MCP với agent

Xem [Cấu hình client](#cấu-hình-client) bên dưới để chọn agent cụ thể.

Quick: Claude Code:
```bash
claude mcp add vbhc -s user -- python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"
```

### Bước 6 — Restart agent + test

```
User: "Liệt kê các tool MCP vbhc"
AI: vbhc_classify, vbhc_create_workfolder, vbhc_reorganize, vbhc_fill_template,
    vbhc_validate, vbhc_aggregate_survey, vbhc_regenerate_check,
    vbhc_load_org_config, vbhc_suggest_noi_nhan
```

Nếu thấy 9 tools → **Cài thành công.**

---

## Scenario B — Triển khai cho phòng/Sở dùng chung 1 server

**Phù hợp khi:** Nhiều cán bộ trong 1 cơ quan cùng dùng MCP, muốn:
- Chia sẻ ORG config (sửa 1 lần, mọi user thấy)
- Cập nhật code tập trung
- Mỗi user vẫn giữ file công việc trên máy mình

### Mô hình

```
        ┌─────────────────────────┐
        │  Server nội bộ          │
        │  - Chạy MCP HTTP server │
        │  - Lưu code skill       │
        │  - Lưu ORG dir          │
        └────────┬────────────────┘
                 │ http://server:8765/mcp
       ┌─────────┼─────────┬─────────┐
       ▼         ▼         ▼         ▼
   User1     User2     User3     User4
   (máy)    (máy)     (máy)     (máy)
   - cong-viec/ trên máy user, KHÔNG đẩy lên server
```

### Bước 1 — Setup server

Trên máy server (Windows Server / Ubuntu Server / VPS).

**Trên Ubuntu/Debian — BẮT BUỘC dùng venv** (PEP 668 chặn pip install vào system Python):

```bash
# 1. Cài Python + venv
sudo apt update
sudo apt install -y python3-full python3-venv git

# 2. Clone skill vào /opt
sudo git clone <repo-url> /opt/vbhc
sudo chown -R $USER:$USER /opt/vbhc
cd /opt/vbhc

# 3. Tạo venv + cài deps
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install mcp python-docx openpyxl pyyaml

# 4. Verify
./venv/bin/python -c "import mcp, docx, openpyxl, yaml; print('OK')"

# 5. Tạo ORG dir
sudo mkdir -p /etc/vbhc-org
sudo cp /opt/vbhc/tri-thuc-template/*.yaml /etc/vbhc-org/
# Sửa /etc/vbhc-org/*.yaml cho cơ quan của bạn
sudo chown -R $USER:$USER /etc/vbhc-org   # nếu user thường edit
```

**Trên Windows Server:**

```cmd
:: Cài Python từ python.org → tick "Add to PATH"
git clone <repo-url> D:\vbhc
cd D:\vbhc
python -m venv venv
.\venv\Scripts\pip install --upgrade pip
.\venv\Scripts\pip install mcp python-docx openpyxl pyyaml
mkdir D:\vbhc-org
copy tri-thuc-template\*.yaml D:\vbhc-org\
```

### Bước 2 — Chạy MCP server (HTTP transport)

> **Lưu ý quan trọng:** từ đây trở đi luôn dùng `./venv/bin/python` (Linux)
> hoặc `.\venv\Scripts\python.exe` (Windows) — KHÔNG dùng `python3`/`python` system.

```bash
# Linux — test foreground
export VBHC_ORG_DIR=/etc/vbhc-org
/opt/vbhc/venv/bin/python /opt/vbhc/mcp/server.py --http --host 0.0.0.0 --port 8765
```

```cmd
:: Windows
set VBHC_ORG_DIR=D:\vbhc-org
D:\vbhc\venv\Scripts\python.exe D:\vbhc\mcp\server.py --http --host 0.0.0.0 --port 8765
```

Bạn sẽ thấy:
```
[vbhc] HTTP server: http://0.0.0.0:8765/mcp
[vbhc] SKILL_DIR = /opt/vbhc
[vbhc] ORG_DIR   = /etc/vbhc-org
INFO:     Started server process
INFO:     Application startup complete.
```

### Bước 3 — Chạy như service (production)

Chọn 1 trong 3 cách (đều OK, dùng cái nào quen):

| Cách | Phù hợp khi |
|---|---|
| **3A. systemd** | Linux thuần, không có control panel |
| **3B. aaPanel Python Project Manager** | Đã có aaPanel, muốn UI quản lý |
| **3C. NSSM** | Windows Server |

#### 3A. systemd (Linux)

Tạo file `/etc/systemd/system/vbhc-mcp.service`:

```ini
[Unit]
Description=VBHC MCP Server
After=network.target

[Service]
Type=simple
User=vbhc
WorkingDirectory=/opt/vbhc
Environment="VBHC_ORG_DIR=/etc/vbhc-org"
Environment="PYTHONIOENCODING=utf-8"
ExecStart=/opt/vbhc/venv/bin/python /opt/vbhc/mcp/server.py --http --host 127.0.0.1 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vbhc-mcp
sudo systemctl status vbhc-mcp
journalctl -u vbhc-mcp -f      # xem log realtime
```

> Bind `127.0.0.1` (không phải `0.0.0.0`) khi đứng sau reverse proxy — tránh bị bypass
> proxy. Dùng `0.0.0.0` chỉ khi không có reverse proxy phía trước.

#### 3B. aaPanel Python Project Manager (UI-based)

**B3B-1. Cài plugin**

aaPanel sidebar → **App Store** → tìm **"Python Project Manager"** (hoặc tên tiếng Việt **"Python Manager"**) → **Install**.

Sau khi cài, sidebar có thêm mục **Python Project**.

**B3B-2. Verify Python version**

Mục **Python Project** → tab **Python** / **Versions**. Nếu chưa có Python ≥ 3.10 → **Install** Python 3.12.

> Bạn đã có venv ở `/opt/vbhc/venv` (hoặc `/home/.../venv`) từ Bước 1, nên không cần để
> plugin tự tạo venv mới — chỉ cần plugin biết để gọi `python` từ venv này.

**B3B-3. Add Project**

Mục **Python Project** → tab **Project** → **Add Project**:

| Field | Giá trị |
|---|---|
| Project name | `vbhc-mcp` |
| Project path | Folder code (vd `/opt/vbhc` hoặc `/home/mcp-soan-thao-vbhc`) |
| Python version | 3.12 (match với venv) |
| Framework | **Other** / **Manual** / **None** ← KHÔNG chọn Flask/Django/FastAPI |
| Startup mode | **Manual** / **Custom command** |
| **Startup command** | `<đường dẫn>/venv/bin/python <đường dẫn>/mcp/server.py --http --host 127.0.0.1 --port 8765` |
| Port | `8765` |
| Map Domain | **Để trống** (sẽ setup riêng trong Website) |
| Auto restart | ✓ |

> **Bắt buộc gõ full path tới venv python** (vd `/opt/vbhc/venv/bin/python`). Nếu chỉ
> gõ `python ...`, plugin có thể dùng Python system → thiếu deps `mcp`, `docx`...

**B3B-4. Environment Variables**

Trong form Add Project có tab/section **Environment Variables** (hoặc **Add ENV**):

| Key | Value |
|---|---|
| `VBHC_ORG_DIR` | Path tới ORG dir, vd `/etc/vbhc-org` hoặc `/root/.vbhc/org` |
| `PYTHONIOENCODING` | `utf-8` |

Submit. Plugin sẽ tạo project + tự start.

**B3B-5. Verify**

Project list → hàng `vbhc-mcp` phải có badge **Running** (xanh).

Click **Log** xem output, phải thấy:
```
[vbhc] HTTP server: http://127.0.0.1:8765/mcp
[vbhc] SKILL_DIR = ...
[vbhc] ORG_DIR   = ...
INFO:     Application startup complete.
```

Test:
```bash
curl -i http://127.0.0.1:8765/mcp     # HTTP 405/406 → OK
```

**Quản lý project sau này:**
- **Restart** sau khi sửa code / sửa YAML trong ORG dir
- **Stop** khi cần bảo trì
- **Log** để debug (Plugin tự rotate log)
- Auto-start sau reboot: bật **Auto start on boot** trong settings của project

#### 3C. NSSM (Windows Server)

```cmd
:: Cài nssm từ https://nssm.cc
nssm install VBHC-MCP
:: Application: D:\vbhc\venv\Scripts\python.exe
:: Arguments: D:\vbhc\mcp\server.py --http --host 127.0.0.1 --port 8765
:: AppEnvironmentExtra: VBHC_ORG_DIR=D:\vbhc-org
nssm start VBHC-MCP
```

### Bước 4 — Chọn cách expose MCP cho client

> **CẢNH BÁO:** MCP HTTP transport mặc định KHÔNG có authentication. Bất kỳ ai gọi
> được URL `/mcp` đều dùng được tools. Phải bảo vệ bằng 1 trong 3 cách bên dưới.

| Lựa chọn | Phù hợp khi | Khó - dễ |
|---|---|---|
| **4A. LAN-only** | Mọi user trong cùng mạng nội bộ cơ quan | ⭐ Đơn giản nhất |
| **4B. Public domain qua aaPanel** | Có domain + cần truy cập từ xa (work from home) | ⭐⭐ Có UI, dễ cho người mới |
| **4C. Manual nginx + Let's Encrypt** | Đã quen Linux/nginx | ⭐⭐⭐ |

#### 4A. LAN-only (đơn giản)

Sửa `ExecStart` trong service file để bind IP LAN của server (vd `192.168.1.50`):

```ini
ExecStart=/opt/vbhc/venv/bin/python /opt/vbhc/mcp/server.py --http --host 192.168.1.50 --port 8765
```

```bash
systemctl daemon-reload && systemctl restart vbhc-mcp
ufw allow from 192.168.1.0/24 to any port 8765   # firewall: chỉ subnet
```

Client config: `"url": "http://192.168.1.50:8765/mcp"`. Bỏ qua Bước 4B, 4C.

---

#### 4B. Public domain qua aaPanel (chi tiết cho người mới)

> **Đã có file riêng cho cách này:** [**INSTALL-AAPANEL.md**](INSTALL-AAPANEL.md) — full A đến Z,
> verbose hơn nhiều, chỉ tập trung aaPanel. Nếu bạn cài trên VPS Ubuntu + aaPanel,
> đọc file đó tốt hơn. Phần dưới là tóm tắt.

**Tình huống:** server có domain (vd `mcp.hagiang.edu.vn`), đã cài aaPanel, muốn client truy cập qua HTTPS từ bất kỳ đâu, có Basic Auth chống bị gọi tools "chùa".

**Yêu cầu trước khi bắt đầu:**
- aaPanel đã cài + đăng nhập được vào dashboard
- MCP server đã chạy và bind `127.0.0.1:8765` (xem log `journalctl -u vbhc-mcp -n 5` thấy `Uvicorn running on http://127.0.0.1:8765` là OK)
- Domain `mcp.hagiang.edu.vn` đã có và bạn có quyền sửa DNS

##### B4B-1. Đảm bảo MCP bind 127.0.0.1 (KHÔNG bind 0.0.0.0)

Khi đứng sau reverse proxy, MCP CHỈ nên nghe localhost — tránh bị bypass proxy. Sửa service nếu cần:

```bash
systemctl cat vbhc-mcp | grep ExecStart
# Phải thấy: ... --host 127.0.0.1 --port 8765
```

Nếu đang bind `0.0.0.0`, sửa lại:
```bash
systemctl edit --full vbhc-mcp
# Đổi --host 0.0.0.0 thành --host 127.0.0.1, save
systemctl restart vbhc-mcp
```

Test:
```bash
curl -i http://127.0.0.1:8765/mcp
# Nhận HTTP 405/406/400 hay JSON error đều OK — server đã listen
# Nếu "Connection refused" → service chưa chạy, xem journalctl -u vbhc-mcp
```

##### B4B-2. Trỏ DNS

Vào trang quản trị DNS (Cloudflare / nhà cung cấp domain) của `hagiang.edu.vn`:
- Tạo A record: name = `mcp`, value = IP công khai của VPS (vd `123.45.67.89`)
- TTL: tối thiểu (vd 300s hoặc Auto)
- Nếu dùng Cloudflare: **TẮT proxy (đám mây xám)** trong giai đoạn đầu để Let's Encrypt issue cert dễ hơn. Bật lại sau khi xong.

Đợi 1-5 phút, kiểm tra:
```bash
dig +short mcp.hagiang.edu.vn
# Phải trả về IP server. Nếu trống → DNS chưa lan, đợi thêm.
```

##### B4B-3. Tạo site trong aaPanel

1. Đăng nhập aaPanel (URL kiểu `http://<server-ip>:8888`)
2. Sidebar trái → **Website** → nút **Add site**
3. Điền form:
   - **Domain name**: `mcp.hagiang.edu.vn` (chỉ 1 dòng, không thêm `www`)
   - **Note**: tùy chọn, vd "MCP soan thao VBHC"
   - **Root directory**: giữ mặc định (`/www/wwwroot/mcp.hagiang.edu.vn`) — sẽ không dùng nhưng aaPanel cần
   - **FTP**: No
   - **Database**: No
   - **PHP version**: chọn **Pure Static** (không cần PHP)
   - **SSL**: bỏ qua, sẽ cấu hình sau
4. Click **Submit**

Test có site chưa:
```bash
curl -I http://mcp.hagiang.edu.vn
# 200 hoặc 403 → site đã được tạo, nginx đã listen
```

##### B4B-4. Cài SSL Let's Encrypt

1. Trong **Website list**, click vào hàng `mcp.hagiang.edu.vn` → mở popup settings
2. Tab **SSL** ở thanh trái popup
3. Chọn **Let's Encrypt**
4. Tick checkbox `mcp.hagiang.edu.vn` (nếu có ô email, điền email admin)
5. Click **Apply**
6. Đợi 30-60s. Nếu thành công, nhìn thấy thông báo cert đã issue + ngày hết hạn
7. Bật toggle **Force HTTPS** (chuyển HTTP 301 → HTTPS tự động)

Nếu **Apply** lỗi:
- "Failed to verify domain": DNS chưa lan, hoặc Cloudflare đang proxy → tắt proxy + đợi thêm
- "Rate limit": Let's Encrypt giới hạn 5 lần/h cho 1 domain → đợi 1h rồi thử lại

Test SSL:
```bash
curl -I https://mcp.hagiang.edu.vn
# Phải thấy "HTTP/2 200" hoặc 403, KHÔNG có cert error
```

##### B4B-5. Cấu hình reverse proxy (BƯỚC QUAN TRỌNG NHẤT)

aaPanel có UI cho reverse proxy nhưng config mặc định **không hợp với streamable-http (SSE)** — phải sửa nginx config thủ công sau khi tạo.

**Phần 1 — Tạo proxy qua UI:**

1. Trong popup site settings, tab **Reverse proxy** ở thanh trái
2. Click **Add reverse proxy**
3. Form:
   - **Proxy name**: `mcp` (chỉ chữ thường, không dấu cách)
   - **Target URL**: `http://127.0.0.1:8765`
   - **Sending domain**: giữ `$host` (mặc định)
   - **Content replacement** / **Cache**: tắt hết
4. Submit

**Phần 2 — Sửa config cho streamable-http:**

aaPanel mặc định bật `proxy_buffering` → MCP streamable-http sẽ chunk lỗi (client treo). Cần tắt buffering + tăng timeout.

1. Tab **Configuration file** (ở thanh trái popup site settings)
2. Tìm block `location` có `proxy_pass http://127.0.0.1:8765` (do bước trên tạo). Block này thường nằm trong file đang xem
3. **Thay TOÀN BỘ block đó** bằng đoạn sau:

```nginx
location ^~ /mcp {
    proxy_pass http://127.0.0.1:8765;
    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection        "";

    # BẮT BUỘC cho streamable-http (SSE) — đừng buffer response
    proxy_buffering         off;
    proxy_request_buffering off;
    proxy_cache             off;
    chunked_transfer_encoding on;

    # Timeout dài để giữ session lâu (24h)
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

4. Click **Save**. aaPanel reload nginx tự động. Nếu lỗi syntax sẽ hiện thông báo đỏ.

> **Giải thích các flag:** `proxy_buffering off` để response chảy thẳng từ MCP sang
> client (không bị giữ đến khi đầy buffer). `chunked_transfer_encoding on` để giữ
> chunked HTTP. `proxy_read_timeout 86400s` để session không bị nginx ngắt giữa chừng.

Test (chưa có auth, ai cũng vào được):
```bash
curl -i https://mcp.hagiang.edu.vn/mcp
# 405/406/400 + body JSON-RPC → OK, proxy work
```

##### B4B-6. Bật Basic Auth (BẮT BUỘC khi public)

Tạo file password trên server (qua SSH, KHÔNG qua aaPanel UI):

```bash
apt install -y apache2-utils
htpasswd -c /www/server/nginx/conf/htpasswd-vbhc admin
# New password: (gõ password mạnh, ko hiện ra)
# Re-type: ...
```

> Muốn thêm user thứ 2: `htpasswd /www/server/nginx/conf/htpasswd-vbhc user2`
> (KHÔNG có `-c` — `-c` sẽ XÓA file cũ).

Quay lại aaPanel → site → **Configuration file** → **thêm 2 dòng** vào TRONG block `location ^~ /mcp` (ngay sau `proxy_pass ...`):

```nginx
    auth_basic           "VBHC MCP";
    auth_basic_user_file /www/server/nginx/conf/htpasswd-vbhc;
```

Block hoàn chỉnh sẽ trông như:

```nginx
location ^~ /mcp {
    auth_basic           "VBHC MCP";
    auth_basic_user_file /www/server/nginx/conf/htpasswd-vbhc;

    proxy_pass http://127.0.0.1:8765;
    proxy_http_version 1.1;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection        "";

    proxy_buffering         off;
    proxy_request_buffering off;
    proxy_cache             off;
    chunked_transfer_encoding on;

    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
```

**Save**. Test:

```bash
# Không có credentials → 401
curl -i https://mcp.hagiang.edu.vn/mcp
# HTTP/2 401
# www-authenticate: Basic realm="VBHC MCP"

# Có credentials → 405/406 (server reach được)
curl -i -u admin:YOUR_PASSWORD https://mcp.hagiang.edu.vn/mcp
# HTTP/2 405 hoặc 406
```

Cả 2 ra đúng → **xong!**

##### B4B-7. (Tùy chọn) Hạn chế chỉ vài IP truy cập

Nếu muốn thêm 1 lớp bảo vệ (chỉ IP cơ quan + nhà admin), thêm vào block:

```nginx
location ^~ /mcp {
    allow 123.45.67.89;        # IP cơ quan
    allow 98.76.54.32;         # IP nhà admin
    deny  all;

    auth_basic ...
    # ... phần còn lại giữ nguyên
}
```

##### B4B-8. (Tùy chọn) Tự renew SSL

Let's Encrypt cert chỉ valid 90 ngày. aaPanel có **Auto renew** tự động — kiểm tra:

Site settings → SSL tab → tick **Auto renew**.

---

#### 4C. Manual nginx + Let's Encrypt (advanced, không dùng aaPanel)

Dành cho người không dùng control panel. Tóm tắt:

```bash
# 1. Cài nginx + certbot
apt install -y nginx certbot python3-certbot-nginx

# 2. Tạo file site
cat > /etc/nginx/sites-available/mcp.hagiang.edu.vn <<'EOF'
server {
    listen 80;
    server_name mcp.hagiang.edu.vn;

    location ^~ /mcp {
        # auth_basic           "VBHC MCP";
        # auth_basic_user_file /etc/nginx/htpasswd-vbhc;

        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection        "";
        proxy_buffering         off;
        proxy_request_buffering off;
        chunked_transfer_encoding on;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }
}
EOF
ln -s /etc/nginx/sites-available/mcp.hagiang.edu.vn /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx   # nginx hệ thống. Nếu dùng aaPanel: /etc/init.d/nginx reload

# 3. SSL
certbot --nginx -d mcp.hagiang.edu.vn

# 4. Basic auth (uncomment 2 dòng auth_basic ở trên)
apt install -y apache2-utils
htpasswd -c /etc/nginx/htpasswd-vbhc admin
nginx -t && systemctl reload nginx   # nginx hệ thống. Nếu dùng aaPanel: /etc/init.d/nginx reload
```

---

### Bước 5 — Cấu hình client trên từng máy user

Tùy bạn chọn LAN-only hay public domain ở Bước 4, URL khác nhau.

**LAN-only (4A):**
```json
{
  "mcpServers": {
    "vbhc": {
      "url": "http://192.168.1.50:8765/mcp"
    }
  }
}
```

**Public domain + Basic Auth (4B/4C) — cách 1: nhúng credentials trong URL:**
```json
{
  "mcpServers": {
    "vbhc": {
      "url": "https://admin:YOUR_PASSWORD@mcp.hagiang.edu.vn/mcp"
    }
  }
}
```

**Public domain + Basic Auth — cách 2: dùng Authorization header (nếu agent hỗ trợ):**
```json
{
  "mcpServers": {
    "vbhc": {
      "url": "https://mcp.hagiang.edu.vn/mcp",
      "headers": {
        "Authorization": "Basic YWRtaW46WU9VUl9QQVNTV09SRA=="
      }
    }
  }
}
```

> Tạo chuỗi base64 credentials: `echo -n "admin:YOUR_PASSWORD" | base64` →
> dán kết quả vào sau `Basic `.

User KHÔNG cần cài Python/skill trên máy mình (server đã làm thay), chỉ cần config client.

> **Lưu ý về `parent_dir` trong tool calls:** Folder `cong-viec/` của user vẫn ở máy
> user. Khi gọi `vbhc_create_workfolder(parent_dir="C:/Users/me/Documents/cong-viec")`,
> server CHẠY trên máy server NHƯNG path `parent_dir` là path TRÊN MÁY SERVER, không
> phải máy user. Model B chỉ phù hợp khi:
> - User dùng path UNC (`\\fileserver\users\me\cong-viec`) cho server access được
> - HOẶC mỗi user có home dir mount lên server
>
> Nếu không thực hiện được → dùng **Scenario A** (mỗi máy chạy stdio local), chỉ
> share ORG dir qua mount/git.

---

### Bước 6 — Verify end-to-end

Trên máy 1 user (đã config client xong), trong agent:

> "Liệt kê các tool MCP vbhc bạn có"

Phải thấy 9 tools (`vbhc_classify`, `vbhc_create_workfolder`, ...). Nếu agent báo "MCP server vbhc connection failed":

```bash
# Trên máy user: test URL trực tiếp
curl -i -u admin:YOUR_PASSWORD https://mcp.hagiang.edu.vn/mcp
# Phải ra 405/406 — chứng tỏ network OK, auth OK

# Nếu 401 → password sai
# Nếu 502/504 → MCP server trên VPS chết, ssh vào kiểm tra:
#   journalctl -u vbhc-mcp -n 30
# Nếu timeout → firewall chặn / DNS chưa lan
```

---

## Scenario C — Cho developer (dev mode)

**Phù hợp khi:** Đang phát triển/sửa skill, muốn test nhanh.

### Setup

```bash
git clone <repo-url> ~/dev/vbhc
cd ~/dev/vbhc
pip install -e mcp/  # editable install nếu có pyproject

# Hoặc just run
pip install mcp python-docx openpyxl pyyaml

# Tạo ORG dir trỏ đến tri-thuc của 1 cơ quan thật để test
export VBHC_ORG_DIR=$HOME/dev/vbhc-tuyenquang-org
mkdir -p $VBHC_ORG_DIR
cp tri-thuc-template/*.yaml $VBHC_ORG_DIR/
```

### Test trực tiếp (không qua agent)

```bash
# Test stdio: gửi 1 JSON-RPC request, xem có nuốt không
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}' | python mcp/server.py
```

### Test individual tool (không qua MCP)

```bash
python -c "
import sys; sys.path.insert(0, 'mcp')
import importlib.util
spec = importlib.util.spec_from_file_location('s', 'mcp/server.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
print(m.vbhc_classify('soạn báo cáo góp ý dự thảo Thông tư'))
"
```

### Hot-reload khi sửa code

MCP server không hot-reload. Sau mỗi lần sửa `mcp/server.py`:
```
# stdio: agent tự restart server khi reconnect
# HTTP: kill process + chạy lại
```

Để dev nhanh hơn, dùng `watchexec` hoặc tương đương:
```bash
watchexec -e py -r -- python mcp/server.py --http --port 8765
```

---

## Cấu hình client

| Agent | File config | Format |
|---|---|---|
| Claude Code | `~/.claude.json` (hoặc `claude mcp add`) | stdio hoặc http |
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` (Win) / `~/Library/.../Claude/claude_desktop_config.json` (Mac) | stdio hoặc http |
| Cursor | `~/.cursor/mcp.json` | stdio hoặc http |
| Cline | UI Settings → MCP Servers | UI |
| Continue.dev | `~/.continue/config.json` | stdio |
| qwenpaw | (kiểm tra doc qwenpaw) | stdio |

### Stdio config (Scenario A)

```json
{
  "mcpServers": {
    "vbhc": {
      "command": "python",
      "args": ["D:\\SKILL_AI\\skills\\soan-thao-vbhc\\mcp\\server.py"],
      "env": {
        "VBHC_ORG_DIR": "C:\\Users\\me\\.vbhc\\org"
      }
    }
  }
}
```

> Trên Mac/Linux dùng `"python3"` thay `"python"`, path forward slash.

### HTTP config (Scenario B)

```json
{
  "mcpServers": {
    "vbhc": {
      "url": "http://vbhc.so-gddt.local:8765/mcp"
    }
  }
}
```

### Claude Code CLI shortcut

```bash
# Stdio
claude mcp add vbhc -s user -- python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"

# Stdio với env var
claude mcp add vbhc -s user -e VBHC_ORG_DIR="$HOME/.vbhc/org" -- python "..."

# HTTP (nếu Claude Code support — kiểm tra version)
claude mcp add vbhc -s user --transport http --url http://vbhc.local:8765/mcp
```

---

## Verify đã cài đúng

### 1. Test server start được

```bash
# Stdio
python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"
# → Process block chờ stdin (đúng). Ctrl+C dừng.

# HTTP
python "..." --http --port 8765
# → "Started server process" + "Application startup complete"
```

### 2. Test agent thấy tools

Trong agent, hỏi:
> "Liệt kê các tool MCP vbhc bạn có"

Phải thấy đủ **9 tools**:
1. `vbhc_classify`
2. `vbhc_create_workfolder`
3. `vbhc_reorganize`
4. `vbhc_fill_template`
5. `vbhc_validate`
6. `vbhc_aggregate_survey`
7. `vbhc_regenerate_check`
8. `vbhc_load_org_config`
9. `vbhc_suggest_noi_nhan`

### 3. Test ORG config load được

> "Gọi vbhc_load_org_config('05-thong-tin-co-quan.yaml')"

Trả về `exists: true` + `parsed` chứa `co_quan.ten_day_du` đúng tên cơ quan của bạn → **OK.**

Nếu `exists: false` → ORG dir chưa được set hoặc file chưa copy. Xem [Troubleshooting](#troubleshooting).

### 4. Test workflow end-to-end

> "Soạn 1 phiếu biểu quyết cho thành viên UBND tỉnh"

AI phải:
1. Gọi `vbhc_classify` → nhận diện đúng "Phiếu biểu quyết"
2. Hỏi user: người ký, đối tượng, quan điểm
3. Tạo folder `<NNNN>-...` chuẩn
4. Tạo file `.docx` với header chuẩn NĐ 30
5. Validate output

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'mcp'`

```bash
pip install mcp
# Hoặc nếu Python không phải python3:
python -m pip install mcp
```

Đảm bảo `python` là Python ≥ 3.10. Nếu hệ thống có cả Python 2/3:

```bash
python --version            # phải là 3.10+
where python                # Windows: xem path
which python3               # Mac/Linux
```

### `error: externally-managed-environment` (PEP 668)

Xảy ra trên Ubuntu 23.04+ / Debian 12+ / một số distro mới. Hệ thống chặn `pip install`
vào system Python để tránh phá apt. **Cách đúng — dùng venv:**

```bash
# 1. Cài venv tools
sudo apt install -y python3-full python3-venv

# 2. Tạo venv (đặt trong skill folder hoặc home)
cd /path/to/soan-thao-vbhc        # hoặc cd ~
python3 -m venv venv

# 3. Cài deps vào venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install mcp python-docx openpyxl pyyaml

# 4. Verify
./venv/bin/python -c "import mcp, docx, openpyxl, yaml; print('OK')"

# 5. Chạy server bằng python của venv (KHÔNG phải python3 system)
./venv/bin/python mcp/server.py --http --port 8765
```

Khi cấu hình systemd / NSSM / Task Scheduler → ExecStart phải trỏ đến `venv/bin/python`,
không phải `/usr/bin/python3`.

> **Đừng dùng `--break-system-packages`** trừ khi bạn hiểu rõ hậu quả — nó có thể phá
> các tool apt-managed (vd: cập nhật apt làm lỗi).
>
> Pipx (`pipx install`) là alternative khác cho từng app standalone, nhưng skill này
> không phải standalone app nên venv là cách phù hợp nhất.

### `ModuleNotFoundError: No module named 'docx'`

Sai package name. **Phải là `python-docx`**, không phải `docx`:
```bash
pip uninstall docx          # nếu lỡ cài sai
pip install python-docx
```

### Agent không thấy tools `vbhc_*`

1. **Server có start được không?**
   ```bash
   python "D:\...\mcp\server.py"
   # Phải block, không lỗi. Ctrl+C để thoát.
   ```
2. **Path trong config có đúng không?** Windows phải dùng `\\` (escape) hoặc `/`:
   - ✅ `"D:\\SKILL_AI\\skills\\..."`
   - ✅ `"D:/SKILL_AI/skills/..."`
   - ❌ `"D:\SKILL_AI\skills\..."` (single backslash trong JSON = escape)
3. **Agent đã restart chưa?**
4. **Check log của agent** — Claude Code: `claude mcp` để list, có chữ "✓" trước tên tool nghĩa là OK.

### `vbhc_load_org_config` báo `exists: false`

ORG dir chưa được setup. Xem lại [Bước 3 Scenario A](#scenario-a--cài-cho-cá-nhân--1-máy):

```bash
# Kiểm tra ORG dir hiện tại
echo %VBHC_ORG_DIR%   # Windows cmd
echo $env:VBHC_ORG_DIR  # PowerShell
echo $VBHC_ORG_DIR    # Mac/Linux

# Default nếu env không set
ls ~/.vbhc/org/       # phải có 3 file *.yaml
```

Nếu env var chưa truyền vào MCP process → check `env` field trong JSON config:
```json
"env": { "VBHC_ORG_DIR": "C:\\Users\\me\\.vbhc\\org" }
```

### HTTP server bind error `[Errno 10048] address already in use`

Port 8765 đã có process khác chiếm:
```bash
# Windows: tìm process
netstat -ano | findstr :8765
taskkill /F /PID <pid>

# Mac/Linux:
lsof -i :8765
kill -9 <pid>
```

Hoặc đổi port: `--port 8766`.

### File .docx output không có dấu gạch chân header

→ Đang dùng python-docx thủ công thay vì `vbhc_doc_builder`. Xem `scripts/vbhc_doc_builder.py` — phải import + dùng `add_header_section()`, đừng tự build table 2x2.

### Tracked changes không có tên thật

Server `vbhc` (python-docx) KHÔNG support tracked changes. Để có tracked changes (sửa file user đang mở):
- Cài thêm MCP `word-mcp-live` (Windows-only, COM-based)
- Dùng `mcp__word__word_live_*` tools cho live editing

### Client treo / không nhận response qua aaPanel proxy

99% là do `proxy_buffering` chưa tắt. nginx đang giữ response lại đợi đầy buffer trong khi MCP đang stream. Quay lại Bước 4B-5, đảm bảo block `location ^~ /mcp` có:
```nginx
proxy_buffering         off;
proxy_request_buffering off;
chunked_transfer_encoding on;
```

Test với curl `-N` (no buffering):
```bash
curl -N -u admin:pass -X POST https://mcp.hagiang.edu.vn/mcp \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}'
```
Nếu response stream về ngay → OK. Nếu treo → buffering chưa off.

### Let's Encrypt cấp cert lỗi "Failed to verify domain"

- DNS chưa lan: `dig +short mcp.hagiang.edu.vn` không ra IP server → đợi DNS, hoặc check Cloudflare đang proxy (đám mây cam) → tắt proxy tạm thời.
- Port 80 bị chặn: Let's Encrypt verify qua HTTP-01 challenge cần port 80 reachable. Check firewall:
  ```bash
  ufw status
  ufw allow 80/tcp
  ufw allow 443/tcp
  ```
- aaPanel có firewall riêng: vào **Security** trong aaPanel → mở port 80, 443.

### Bị 401 dù gõ đúng password

- Password file path sai trong `auth_basic_user_file` — `ls -la /www/server/nginx/conf/htpasswd-vbhc` xem file có không
- nginx user (`www`) không có quyền đọc file: `chmod 644 /www/server/nginx/conf/htpasswd-vbhc`
- Cache cũ trong nginx: `systemctl reload nginx`

### aaPanel Python Project: badge "Stopped" / "Failed"

Click **Log** xem error. Các nguyên nhân thường gặp:

- **`ModuleNotFoundError: No module named 'mcp'`** → Startup command đang gọi Python system thay vì venv. Sửa startup command thành full path: `/opt/vbhc/venv/bin/python /opt/vbhc/mcp/server.py --http ...`.
- **`Address already in use`** → systemd `vbhc-mcp.service` cũ đang chạy chiếm port 8765. Tắt: `systemctl disable --now vbhc-mcp && rm /etc/systemd/system/vbhc-mcp.service && systemctl daemon-reload`.
- **`No such file or directory: '...mcp/server.py'`** → Project path sai. Vào Edit project, sửa lại.
- **Plugin báo "Port already in use"** khi Add Project → đổi port khác (vd 8766) ở cả startup command + nginx reverse proxy target.

### aaPanel Python Project — sửa code rồi nhưng không apply

Plugin không tự reload code. Sau mỗi `git pull` hoặc sửa file:
1. Plugin → Project list → hàng `vbhc-mcp` → **Restart**
2. Hoặc terminal: `bt python` (hoặc xem `/etc/init.d/...` script plugin tạo)

Sửa YAML trong ORG dir cũng cần restart (vì server cache khi load).

### MCP server chết sau vài giờ

- Memory leak hiếm gặp; check `journalctl -u vbhc-mcp -n 100` xem có OOM/exception
- systemd đã có `Restart=on-failure` → tự khởi động lại khi crash
- Để chắc, thêm `Restart=always` thay `on-failure` trong service file

### File Word đang mở → không save được

Đóng file trong Word trước khi gen lại. Hoặc save sang tên `*_v2.docx`:
```python
output_path = "ket-qua_v2.docx" if Path("ket-qua.docx").exists() else "ket-qua.docx"
```

### Tiếng Việt bị `?` hoặc lỗi encoding trong stdout

Server đã có `sys.stdout = io.TextIOWrapper(..., encoding="utf-8")` ở đầu file. Nếu vẫn lỗi:
```bash
# Windows cmd
chcp 65001
set PYTHONIOENCODING=utf-8

# PowerShell
$env:PYTHONIOENCODING="utf-8"
[Console]::OutputEncoding=[Text.Encoding]::UTF8
```

---

## Cập nhật khi có version mới

```bash
cd D:\SKILL_AI\skills\soan-thao-vbhc
git pull

# Re-install nếu pyproject thay đổi
pip install -U mcp python-docx openpyxl pyyaml

# Restart agent (stdio sẽ tự pick up)
# HTTP server: restart manually
sudo systemctl restart vbhc-mcp        # Linux
nssm restart VBHC-MCP                  # Windows
```

**ORG dir KHÔNG bị overwrite khi update skill** — vì nằm ngoài skill folder. An toàn.

Nếu template `tri-thuc-template/` có file mới → bạn nên copy thủ công field mới vào ORG dir của mình. Diff giúp:

```bash
diff -u $VBHC_ORG_DIR/05-thong-tin-co-quan.yaml \
        D:/SKILL_AI/skills/soan-thao-vbhc/tri-thuc-template/05-thong-tin-co-quan.yaml
```

---

## Tài liệu liên quan

| File | Nội dung |
|---|---|
| `SKILL.md` | Workflow 6 pha + nguyên tắc soạn VB + anti-pattern |
| `SETUP-FOR-AGENTS.md` | Quick reference cấu hình từng agent (Cursor, Cline, Continue.dev...) |
| `tri-thuc-template/README.md` | Hướng dẫn sửa các file YAML trong ORG dir |
| `resources/workflow-7-buoc.md` | Chi tiết từng pha workflow |
| `resources/danh-muc-loai-vb.md` | Danh mục 27+ loại VBHC |

---

## Liên hệ / Hỗ trợ

Lỗi cài đặt: tạo issue trên repo, kèm output của:
```bash
python --version
pip show mcp python-docx openpyxl pyyaml
python "D:\...\mcp\server.py" 2>&1 | head -50   # log lỗi server
```
