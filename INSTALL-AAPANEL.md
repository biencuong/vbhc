# Cài MCP `vbhc` trên VPS Ubuntu + aaPanel — A đến Z

Hướng dẫn cài và triển khai MCP `vbhc` trên 1 VPS Ubuntu đã có aaPanel, expose qua HTTPS với domain riêng + Basic Auth. Viết cho người mới — mỗi bước có lệnh copy-paste hoặc chỉ rõ click vào đâu trên UI aaPanel.

> **Đọc cùng:** [INSTALL.md](INSTALL.md) (tổng quát các kịch bản) — file này chỉ tập trung vào aaPanel.

## Mục lục

- [⚡ Cài nhanh 1 lệnh (KHUYẾN NGHỊ)](#-cài-nhanh-1-lệnh-khuyến-nghị)
- [0. Tổng quan kiến trúc](#0-tổng-quan-kiến-trúc)
- [1. Yêu cầu trước khi bắt đầu](#1-yêu-cầu-trước-khi-bắt-đầu)
- [2. Upload code lên VPS](#2-upload-code-lên-vps)
- [3. Cài Python deps (venv)](#3-cài-python-deps-venv)
- [4. Tạo ORG dir + sửa YAML cơ quan](#4-tạo-org-dir--sửa-yaml-cơ-quan)
- [5. Tạo MCP service (chạy persistent)](#5-tạo-mcp-service-chạy-persistent)
  - [5A. systemd (KHUYẾN NGHỊ)](#5a-systemd-khuyến-nghị)
  - [5B. aaPanel Python Project Manager (UI)](#5b-aapanel-python-project-manager-ui)
- [6. Trỏ DNS + tạo site trên aaPanel](#6-trỏ-dns--tạo-site-trên-aapanel)
- [7. Cài SSL Let's Encrypt](#7-cài-ssl-lets-encrypt)
- [8. Cấu hình Reverse Proxy (cốt lõi)](#8-cấu-hình-reverse-proxy-cốt-lõi)
- [9. Bật Basic Auth](#9-bật-basic-auth)
- [10. Verify end-to-end](#10-verify-end-to-end)
- [11. Cấu hình client (máy người dùng)](#11-cấu-hình-client-máy-người-dùng)
- [12. Vận hành sau cài đặt](#12-vận-hành-sau-cài-đặt)
- [13. Troubleshooting](#13-troubleshooting)

---

## ⚡ Cài nhanh 1 lệnh (KHUYẾN NGHỊ)

Phần Linux/MCP (Bước 1-5) đã được đóng gói thành script `deploy/install-server.sh`.
**SSH vào VPS với root, chạy 1 lệnh:**

```bash
cd /home && \
git clone https://github.com/biencuong/vbhc.git mcp-soan-thao-vbhc && \
cd mcp-soan-thao-vbhc && git checkout v0.9.0 && \
bash deploy/install-server.sh
```

Script tự làm:
1. `apt install python3-full python3-venv apache2-utils`
2. Tạo venv `/home/mcp-soan-thao-vbhc/venv`
3. `pip install mcp python-docx openpyxl pyyaml uvicorn`
4. Tạo ORG dir `/root/.vbhc/org/` + copy template YAML + **sinh 1 API key admin random** (chmod 600)
5. Ghi `/etc/systemd/system/vbhc-mcp.service` với env `VBHC_API_KEYS_FILE`
6. `systemctl daemon-reload + enable + start`
7. Test HTTP `127.0.0.1:8765/mcp` phải trả 401 (do API key middleware reject request không Bearer header)

Output cuối phải in **KEY ADMIN** — **LƯU LẠI NGAY** để cấp cho client. Sau đó tiếp tục từ
[Bước 4 sửa YAML cơ quan](#4-tạo-org-dir--sửa-yaml-cơ-quan) và [Bước 6 trỏ DNS + aaPanel](#6-trỏ-dns--tạo-site-trên-aapanel).

> **Update code lần sau (sau khi push thay đổi từ máy dev):**
> ```bash
> cd /home/mcp-soan-thao-vbhc && git pull && systemctl restart vbhc-mcp
> ```
> Hoặc nếu có thay đổi về deps/service:
> ```bash
> cd /home/mcp-soan-thao-vbhc && git pull && bash deploy/install-server.sh
> ```
> Script idempotent — chỉ làm phần thay đổi.

> **Custom path/port** (nếu không dùng mặc định):
> ```bash
> VBHC_ORG_DIR=/etc/vbhc-org VBHC_PORT=8800 bash deploy/install-server.sh
> ```

Phần dưới (Bước 1-5 chi tiết) là **manual fallback** nếu bạn muốn hiểu từng bước hoặc khi script báo lỗi.

---

## 0. Tổng quan kiến trúc

```
                        Internet
                           │
                           ▼
              https://mcp.hagiang.edu.vn
                           │
              ┌────────────┴────────────┐
              │  VPS Ubuntu + aaPanel   │
              │                         │
              │  nginx (port 443)       │
              │   ├─ SSL (Let's Encrypt) │
              │   └─ proxy_pass ──┐      │
              │                   ▼      │
              │   MCP server: 127.0.0.1:8765
              │   (systemd: vbhc-mcp.service)
              │   ★ API key middleware (Bearer)
              │                         │
              │   ORG dir: /root/.vbhc/org/
              │   ├─ YAML config cơ quan │
              │   └─ api-keys.yaml (chmod 600)
              └─────────────────────────┘
```

**Phân vai trò (v0.9.0+):**
- **MCP server**: nghe localhost port 8765 — không expose ra Internet trực tiếp.
  **Tự kiểm `Authorization: Bearer <key>`** qua Starlette middleware (file `mcp/auth.py`).
- **nginx (do aaPanel quản lý)**: terminate HTTPS + reverse proxy. **KHÔNG còn Basic Auth** —
  mỗi client cấp 1 API key riêng, server check.
- **aaPanel UI**: quản lý site, SSL, reverse proxy.

> **Migration từ phiên bản cũ Basic Auth**: xem [MIGRATION-v0.9.md](MIGRATION-v0.9.md).

---

## 1. Yêu cầu trước khi bắt đầu

| Yêu cầu | Cách kiểm tra |
|---|---|
| VPS Ubuntu 22.04 hoặc 24.04 | `lsb_release -a` |
| User root (hoặc sudo) | `whoami` ra `root` |
| aaPanel đã cài và đăng nhập được | URL kiểu `http://<ip>:8888/<entrance>` |
| Domain (vd `mcp.hagiang.edu.vn`) | Bạn có quyền sửa DNS |
| Port 80, 443 mở (Internet → server) | `ss -tlnp \| grep -E ':80\|:443'` thấy nginx |
| Python ≥ 3.10 | `python3 --version` |

> **Nếu chưa có aaPanel**, cài bằng:
> ```bash
> wget -O install.sh https://www.aapanel.com/script/install_7.0_en.sh
> bash install.sh aapanel
> ```
> Sau khi xong, ghi lại URL panel + tài khoản admin (script in ra cuối).

> **Nếu Cloudflare**: trong giai đoạn cấp SSL, **TẮT proxy (đám mây xám)** trên record DNS — bật lại sau khi xong nếu muốn.

---

## 2. Upload code lên VPS

Có 3 cách tùy bạn quen.

### 2.1. Git clone (nếu code trên Git)

```bash
cd /home
git clone <repo-url> mcp-soan-thao-vbhc
cd mcp-soan-thao-vbhc
ls    # phải thấy SKILL.md, mcp/, scripts/, tri-thuc-template/
```

### 2.2. SCP từ máy local

Trên máy Windows (PowerShell):
```powershell
scp -r "D:\SKILL_AI\skills\soan-thao-vbhc" root@<vps-ip>:/home/mcp-soan-thao-vbhc
```

### 2.3. aaPanel File Manager (UI)

aaPanel sidebar → **Files** → vào `/home/` → **Upload** → chọn file zip → upload xong, **Unzip**.

### Verify

```bash
cd /home/mcp-soan-thao-vbhc
ls -la
# Phải thấy: SKILL.md, README.md, INSTALL.md, mcp/, scripts/, tri-thuc-template/, ...
```

> Trong tài liệu này tôi mặc định path là `/home/mcp-soan-thao-vbhc`. Nếu bạn dùng path khác (vd `/www/wwwroot/vbhc`), thay tương ứng ở các bước sau.

---

## 3. Cài Python deps (venv)

Ubuntu 22.04+ chặn `pip install` vào system Python (PEP 668), phải dùng venv.

```bash
# Cài venv tools (chỉ cần 1 lần)
apt update
apt install -y python3-full python3-venv apache2-utils

# Tạo venv trong skill folder
cd /home/mcp-soan-thao-vbhc
python3 -m venv venv

# Cài deps vào venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install mcp python-docx openpyxl pyyaml

# Verify
./venv/bin/python -c "import mcp, docx, openpyxl, yaml; print('OK')"
# → in ra "OK"
```

Test thử server chạy được (foreground, Ctrl+C để thoát):
```bash
./venv/bin/python mcp/server.py --http --host 127.0.0.1 --port 8765
```

Phải thấy:
```
[vbhc] HTTP server: http://127.0.0.1:8765/mcp
[vbhc] SKILL_DIR = /home/mcp-soan-thao-vbhc
[vbhc] ORG_DIR   = /root/.vbhc/org
INFO:     Application startup complete.
```

**Ctrl+C** dừng. Bước sau sẽ chạy như service.

---

## 4. Tạo ORG dir + sửa YAML cơ quan

ORG dir chứa cấu hình chung cơ quan: tên, người ký, phòng, viết tắt, phân công nhiệm vụ.

```bash
# Tạo + copy template
mkdir -p /root/.vbhc/org
cp /home/mcp-soan-thao-vbhc/tri-thuc-template/*.yaml /root/.vbhc/org/

ls /root/.vbhc/org/
# 05-thong-tin-co-quan.yaml
# can-cu-phap-ly-mau.yaml
# phan-cong-nhiem-vu.yaml
```

**Sửa nội dung 3 file YAML này cho đúng cơ quan của bạn.** Có 2 cách:

### Cách 1 — qua aaPanel File Manager (dễ cho người mới)

aaPanel sidebar → **Files** → vào `/root/.vbhc/org/` → click vào file `.yaml` → **Edit**. Sửa xong, **Save**.

### Cách 2 — qua SSH

```bash
nano /root/.vbhc/org/05-thong-tin-co-quan.yaml
# Ctrl+O save, Ctrl+X thoát
```

**Cần sửa các field:**

| File | Field cần sửa |
|---|---|
| `05-thong-tin-co-quan.yaml` | `co_quan.ten_day_du`, `co_quan.co_quan_chu_quan`, `co_quan.dia_danh`, `nguoi_ky`, `phong_soan_thao` |
| `phan-cong-nhiem-vu.yaml` | `don_vi` — danh sách phòng/đơn vị + `chuc_nang` của từng phòng |
| `can-cu-phap-ly-mau.yaml` | (Tùy chọn) Thêm các Luật/NĐ/TT cơ quan thường viện dẫn |

> **Quan trọng**: tên cơ quan UPPERCASE đúng quy ước NĐ 30 (vd `"SỞ GIÁO DỤC VÀ ĐÀO TẠO"`). Người ký nhập đầy đủ họ tên có dấu (vd `"Nguyễn Văn A"`).

---

## 5. Tạo MCP service (chạy persistent)

Chọn **5A** (systemd) hoặc **5B** (aaPanel Python Project Manager). Cả 2 đều OK; 5A có CLI dễ debug, 5B có UI dễ thao tác.

### 5A. systemd (KHUYẾN NGHỊ)

> **Cách nhanh nhất**: dùng script ở [Cài nhanh 1 lệnh](#-cài-nhanh-1-lệnh-khuyến-nghị) đầu file. Phần dưới là cách thủ công nếu cần debug từng bước.

**Cách 1 — copy file template từ repo (an toàn, không lỗi indent):**

```bash
cp /home/mcp-soan-thao-vbhc/deploy/vbhc-mcp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vbhc-mcp
```

> File `deploy/vbhc-mcp.service` mặc định path `/home/mcp-soan-thao-vbhc`. Nếu code ở folder khác, chỉnh `WorkingDirectory` + `ExecStart` trong `/etc/systemd/system/vbhc-mcp.service` rồi `systemctl daemon-reload`.

**Cách 2 — heredoc (paste trong SSH, chú ý KHÔNG có space đầu dòng):**

```bash
cat > /etc/systemd/system/vbhc-mcp.service <<'EOF'
[Unit]
Description=VBHC MCP Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/mcp-soan-thao-vbhc
Environment="VBHC_ORG_DIR=/root/.vbhc/org"
Environment="PYTHONIOENCODING=utf-8"
ExecStart=/home/mcp-soan-thao-vbhc/venv/bin/python /home/mcp-soan-thao-vbhc/mcp/server.py --http --host 127.0.0.1 --port 8765
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now vbhc-mcp
```

> **Lỗi thường gặp khi paste heredoc:**
> - Dòng cuối `EOF` bị thụt space đầu → bash KHÔNG nhận là kết thúc, treo. Phải để `EOF` ở cột 0.
> - Dòng `ExecStart` bị wrap thành 2 dòng do terminal hẹp → systemd báo "Failed to parse". Phải để 1 dòng dài.
> - Nếu gặp 1 trong 2 lỗi trên → dùng Cách 1 (copy file) hoặc nano (xem [Bước 13 troubleshooting](#13-troubleshooting)).

Verify:
```bash
systemctl status vbhc-mcp
# Active: active (running) ← OK

curl -i http://127.0.0.1:8765/mcp
# HTTP/1.1 405 hoặc 406 hoặc body JSON-RPC ← OK

journalctl -u vbhc-mcp -n 20
# Phải thấy "Application startup complete"
```

### 5B. aaPanel Python Project Manager (UI)

> Plugin này không có CLI, chỉ thao tác qua UI. Nếu thích quản lý qua giao diện thì dùng cái này thay 5A.

**B5B-1. Cài plugin**

aaPanel sidebar → **App Store** → tab **Apps** → search **"Python Project Manager"** → **Install**.

Cài xong, sidebar có thêm **Python Project**.

**B5B-2. Verify Python version**

Python Project → tab **Python** / **Versions** → nếu chưa có Python ≥ 3.10, click **Install** → chọn 3.12.

> Plugin có thể tự tạo venv mới, NHƯNG bạn đã có venv ở `/home/mcp-soan-thao-vbhc/venv` → trong startup command sẽ trỏ vào venv này, không cần plugin tạo lại.

**B5B-3. Add Project**

Python Project → tab **Project** → **Add Project**:

| Field | Giá trị |
|---|---|
| Project name | `vbhc-mcp` |
| Project path | `/home/mcp-soan-thao-vbhc` |
| Python version | 3.12 (match với venv đã có) |
| Framework | **Other** / **Manual** / **None** ← KHÔNG chọn Flask/Django/FastAPI |
| Startup mode | **Manual** / **Custom command** |
| **Startup command** | `/home/mcp-soan-thao-vbhc/venv/bin/python /home/mcp-soan-thao-vbhc/mcp/server.py --http --host 127.0.0.1 --port 8765` |
| Port | `8765` |
| Map Domain | **Để trống** (sẽ setup riêng ở Bước 6-8) |
| External access | **OFF** |
| Auto restart | **ON** |
| Auto start on boot | **ON** |

**Environment Variables** (tab/section riêng trong form):

| Key | Value |
|---|---|
| `VBHC_ORG_DIR` | `/root/.vbhc/org` |
| `PYTHONIOENCODING` | `utf-8` |

Submit. Plugin tự start project.

**B5B-4. Verify**

Project list → hàng `vbhc-mcp` phải có badge **Running** (xanh).

Click **Log** xem output:
```
[vbhc] HTTP server: http://127.0.0.1:8765/mcp
[vbhc] SKILL_DIR = /home/mcp-soan-thao-vbhc
[vbhc] ORG_DIR   = /root/.vbhc/org
INFO:     Application startup complete.
```

Test:
```bash
curl -i http://127.0.0.1:8765/mcp
# HTTP 405/406 → OK
```

---

## 6. Trỏ DNS + tạo site trên aaPanel

### 6.1. Trỏ DNS

Vào trang quản trị DNS của domain (Cloudflare, Vinahost, Mắt Bão, GoDaddy...):

- Tạo **A record**:
  - Name/Host: `mcp` (chỉ phần trước domain chính, vd `mcp` cho `mcp.hagiang.edu.vn`)
  - Value/Points to: IP công khai của VPS (gõ trên VPS: `curl -4 ifconfig.me`)
  - TTL: 300 hoặc Auto
- Nếu Cloudflare: **TẮT proxy (đám mây xám)** giai đoạn cấp SSL

Đợi 1-3 phút, kiểm tra:
```bash
dig +short mcp.hagiang.edu.vn
# Phải trả về IP server. Trống → DNS chưa lan, đợi thêm.
```

### 6.2. Mở port 80, 443

aaPanel → **Security** (sidebar) → kiểm tra port 80, 443 đang **Allow**. Nếu chưa, thêm rule.

Hoặc qua terminal:
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw status
```

### 6.3. Tạo site

1. aaPanel sidebar → **Website** → nút **Add site** (góc phải trên)
2. Form **Add site**:
   - **Domain name**: `mcp.hagiang.edu.vn` (1 dòng, không thêm www)
   - **Note**: tùy chọn, vd `MCP soạn thảo VBHC`
   - **Root directory**: giữ mặc định (`/www/wwwroot/mcp.hagiang.edu.vn`) — sẽ không dùng để serve content nhưng aaPanel cần để cấp SSL
   - **FTP**: No
   - **Database**: No
   - **PHP version**: chọn **Pure Static** (no PHP)
   - **SSL**: bỏ qua, sẽ làm ở Bước 7
3. Click **Submit**

Verify:
```bash
curl -I http://mcp.hagiang.edu.vn
# HTTP/1.1 200, 403 hoặc 404 → site đã được tạo, nginx đang serve
```

---

## 7. Cài SSL Let's Encrypt

> aaPanel có ACME client riêng (KHÔNG dùng `certbot` system). Phải cấp SSL qua UI aaPanel để panel quản lý auto-renew.

1. aaPanel → **Website** → click vào hàng `mcp.hagiang.edu.vn` → popup **Settings** mở ra
2. Tab **SSL** ở thanh trái popup
3. Tab con **Let's Encrypt**
4. Tick checkbox `mcp.hagiang.edu.vn` (nếu có ô email, điền email admin của cơ quan để Let's Encrypt gửi cảnh báo hết hạn)
5. Click **Apply**
6. Đợi 30-60s. Khi thấy thông báo **Certificate has been issued**, scroll xuống cuối tab và bật toggle **Force HTTPS** (chuyển HTTP 301 → HTTPS)
7. Đóng popup

Verify:
```bash
curl -I https://mcp.hagiang.edu.vn
# HTTP/2 200, 403 hoặc 404 — KHÔNG có cert error → SSL OK

# HTTP phải redirect 301 sang HTTPS
curl -I http://mcp.hagiang.edu.vn
# HTTP/1.1 301 Moved Permanently
# Location: https://mcp.hagiang.edu.vn/
```

**Auto-renew:** aaPanel tự động renew SSL trước khi hết hạn (90 ngày) qua scheduler nội bộ. Không cần làm gì thêm.

### Nếu Apply lỗi

| Lỗi | Nguyên nhân | Fix |
|---|---|---|
| `Failed to verify domain` | DNS chưa lan, hoặc Cloudflare đang proxy | `dig +short` check; tắt proxy Cloudflare |
| `Connection refused on port 80` | Port 80 chưa mở | `ufw allow 80/tcp` |
| `Rate limit exceeded` | Đã thử > 5 lần/h | Đợi 1h |
| `Address already in use` | Port 80 bị process khác chiếm (vd Apache) | `ss -tlnp \| grep :80` xem ai chiếm |

---

## 8. Cấu hình Reverse Proxy (cốt lõi)

Đây là bước quan trọng nhất. aaPanel mặc định **không tương thích MCP streamable-http** — phải sửa nginx config thủ công.

### 8.1. Add reverse proxy qua UI

1. Website → click `mcp.hagiang.edu.vn` → popup Settings
2. Tab **Reverse proxy** ở thanh trái
3. Click **Add reverse proxy**
4. Form:
   - **Proxy name**: `mcp` (chỉ chữ thường)
   - **Target URL**: `http://127.0.0.1:8765`
   - **Sending domain**: giữ mặc định (`$host`)
   - **Content replacement / Cache**: tắt hết
5. Submit

### 8.2. Sửa nginx config (BẮT BUỘC)

aaPanel mặc định bật `proxy_buffering` + Host header sai → 2 vấn đề:
1. MCP streamable-http (SSE) sẽ chunk lỗi, client treo
2. FastMCP TrustedHostMiddleware reject với "Invalid Host header"

**Block aaPanel auto-tạo trông như sau** (đừng giữ nguyên):

```nginx
#PROXY-START/
location ^~ /
{
    proxy_pass http://127.0.0.1:8765;
    proxy_set_header Host $host;          ← gây "Invalid Host header"
    proxy_set_header X-Real-IP $remote_addr;
    ...
    # KHÔNG có proxy_buffering off → SSE treo
}
#PROXY-END/
```

1. Vẫn trong popup Settings của site, tab **Configuration file** (thanh trái popup)
2. Tìm block `#PROXY-START/ ... #PROXY-END/`
3. **Thay TOÀN BỘ block** (giữ 2 dòng marker `#PROXY-START/` và `#PROXY-END/` để aaPanel biết) bằng đoạn dưới:

```nginx
#PROXY-START/
location ^~ /mcp
{
    proxy_pass http://127.0.0.1:8765;
    proxy_http_version 1.1;
    # Host = backend address để qua TrustedHostMiddleware của FastMCP/Starlette
    # (nếu dùng $host = domain ngoài → server reject "Invalid Host header")
    proxy_set_header Host              127.0.0.1:8765;
    proxy_set_header X-Forwarded-Host  $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Connection        "";

    # BẮT BUỘC cho streamable-http (SSE)
    proxy_buffering         off;
    proxy_request_buffering off;
    proxy_cache             off;
    chunked_transfer_encoding on;

    # Timeout dài để giữ session lâu (24h)
    proxy_read_timeout 86400s;
    proxy_send_timeout 86400s;
}
#PROXY-END/
```

4. Click **Save**. aaPanel tự reload nginx. Nếu báo đỏ syntax → kiểm tra dấu `{`, `}`.

> ⚠ **CẢNH BÁO**: Sau khi sửa xong, **KHÔNG đụng vào tab "Reverse Proxy" trong UI nữa**. Nếu Edit/Save qua tab đó, aaPanel sẽ regen lại block giữa `#PROXY-START/` và `#PROXY-END/`, mất hết config tuỳ chỉnh. Mỗi lần cần sửa nginx, vào thẳng tab **Configuration file**.

> **Giải thích:** `proxy_buffering off` bắt nginx forward response chunk-by-chunk thay vì giữ cho đầy buffer. `chunked_transfer_encoding on` giữ chunked HTTP. `proxy_read_timeout 86400s` chống nginx ngắt session đang dài.

Test (chưa có auth, ai cũng vào được tạm thời):
```bash
curl -i https://mcp.hagiang.edu.vn/mcp
# HTTP/2 405 hoặc 406 — body có JSON-RPC error message
# → Reverse proxy OK
```

> **Nếu treo / không response**: chắc chắn `proxy_buffering off` đã được lưu. Mở lại Configuration file kiểm tra.

---

## 9. Cấp API key cho client

Domain công khai = ai cũng gọi được tools. **Phải có auth.** Từ v0.9.0 dùng API key
(Bearer token) thay Basic Auth — mỗi máy 1 key riêng, có thể revoke / IP whitelist /
rate limit độc lập.

> **KHÔNG cần** thêm `auth_basic` vào nginx config nữa — server tự kiểm.

### 9.1. Key admin đã có

Installer (Bước 5/Cài nhanh) đã sinh sẵn 1 key `admin`. File:

```bash
cat /root/.vbhc/org/api-keys.yaml
```

Phải thấy 1 entry với `id: admin`, `key: vbhc_<64hex>`. Nếu chưa lưu key, lấy lại từ file
này hoặc dùng `manage_keys.py rotate admin` (tạo key mới, vô hiệu key cũ).

### 9.2. Cấp key cho từng máy/người dùng

Dùng CLI `manage_keys.py`:

```bash
cd /home/mcp-soan-thao-vbhc

# Thêm key cơ bản
./venv/bin/python scripts/manage_keys.py add laptop-an --description "An laptop"

# Thêm key có IP whitelist + rate limit
./venv/bin/python scripts/manage_keys.py add may-vt \
    --description "Máy văn thư phòng VT" \
    --ips 192.168.1.50 \
    --rate-limit 60
```

Output sẽ in `vbhc_<64hex>` — **lưu lại để cấp cho người dùng tương ứng** (vẫn còn trong yaml,
nhưng tránh phải xem yaml mỗi lần).

Liệt kê tất cả keys (mask một phần):
```bash
./venv/bin/python scripts/manage_keys.py list
```

### 9.3. Apply: restart MCP service

Server cache config khi start. Sau khi sửa keys:
```bash
systemctl restart vbhc-mcp
journalctl -u vbhc-mcp -n 5
# Phải thấy: "API keys = .../api-keys.yaml (N key(s))"  với N = số key trong yaml
```

### 9.4. Quản lý keys hằng ngày

```bash
# Vô hiệu 1 key (vẫn giữ trong yaml)
./venv/bin/python scripts/manage_keys.py revoke laptop-an

# Đổi key mới (giữ id, sinh key random mới — key cũ KHÔNG còn tác dụng)
./venv/bin/python scripts/manage_keys.py rotate laptop-an

# Xoá hẳn khỏi yaml
./venv/bin/python scripts/manage_keys.py delete laptop-an
```

> Sau bất kỳ thao tác nào → `systemctl restart vbhc-mcp` để apply.

### 9.5. (Tuỳ chọn) IP whitelist cấp nginx

Nếu muốn thêm 1 lớp bảo vệ ở mức nginx (lọc trước khi vào server) — thêm vào đầu block
`location ^~ /mcp` trong **Configuration file**:

```nginx
    allow 123.45.67.89;        # IP cơ quan
    allow 98.76.54.32;         # IP nhà admin
    deny  all;
```

Phương án này áp dụng cho mọi client. Nếu muốn whitelist riêng từng key, dùng `--ips`
trong `manage_keys.py add` (Bước 9.2) — granular hơn.

---

## 10. Verify end-to-end

```bash
# Test 1: Không Authorization header → 401
curl -i https://mcp.hagiang.edu.vn/mcp
```
Phải thấy:
```
HTTP/2 401
www-authenticate: Bearer realm="vbhc"
{"error":"Missing 'Authorization: Bearer <key>' header"}
```

```bash
# Test 2: Sai key → 401
curl -i -H "Authorization: Bearer vbhc_wrong" https://mcp.hagiang.edu.vn/mcp
```
Phải thấy: `HTTP/2 401` + `{"error":"Invalid API key"}`.

```bash
# Test 3: Đúng key → 405/406 (server reach OK, method GET không hợp lệ cho MCP)
curl -i -H "Authorization: Bearer vbhc_<key-từ-bước-9>" https://mcp.hagiang.edu.vn/mcp
```
Phải thấy: `HTTP/2 405` (hoặc 406).

```bash
# Test 4: POST JSON-RPC initialize → server response
curl -N -X POST https://mcp.hagiang.edu.vn/mcp \
     -H "Authorization: Bearer vbhc_<key>" \
     -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}'
```
Phải thấy stream JSON về với info server, 11 tools list, ... → **Server hoàn toàn OK.**

4 test pass → có thể chuyển sang config client.

---

## 11. Cấu hình client (máy người dùng)

Trên máy mỗi user, trong agent (Claude Code, Cursor, Cline, Claude Desktop...):
**dùng `Authorization: Bearer <api-key>`**.

```json
{
  "mcpServers": {
    "vbhc": {
      "url": "https://mcp.hagiang.edu.vn/mcp",
      "headers": {
        "Authorization": "Bearer vbhc_<key-cấp-cho-máy-này>"
      }
    }
  }
}
```

> **Mỗi máy 1 key riêng**. Admin cấp key qua `manage_keys.py add <id>` (xem Bước 9).
> Nếu mất key, admin chạy `manage_keys.py rotate <id>` để tạo key mới.

### File config theo agent

| Agent | File |
|---|---|
| Claude Desktop (Win) | `%APPDATA%\Claude\claude_desktop_config.json` |
| Claude Desktop (Mac) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Claude Code | `claude mcp add vbhc -s user --transport http --url https://...` hoặc sửa `~/.claude.json` |
| Cursor | `~/.cursor/mcp.json` |
| Cline | UI Settings → MCP Servers → Add → headers `Authorization: Bearer ...` |

Restart agent. Test trong agent:
> "Liệt kê các tool MCP `vbhc_*` bạn có"

Phải thấy **11 tools**:

1. `vbhc_classify`
2. `vbhc_create_workfolder`
3. `vbhc_reorganize`
4. `vbhc_fill_template`
5. `vbhc_validate`
6. `vbhc_aggregate_survey`
7. `vbhc_regenerate_check`
8. `vbhc_load_org_config`
9. `vbhc_suggest_noi_nhan`
10. `vbhc_learn_template` ★ v0.9
11. `vbhc_update_template` ★ v0.9

→ **Cài thành công.**

---

## 12. Vận hành sau cài đặt

### 12.1. Update code

**Cách nhanh — code-only (không có thay đổi deps/service):**
```bash
cd /home/mcp-soan-thao-vbhc && git pull && systemctl restart vbhc-mcp
```

**Cách full — re-run script (an toàn cho mọi thay đổi):**
```bash
cd /home/mcp-soan-thao-vbhc && git pull && bash deploy/install-server.sh
```
Script idempotent — chỉ apply phần thay đổi (deps mới, service file đổi, ORG dir thiếu...).

**Cách thủ công:**
```bash
cd /home/mcp-soan-thao-vbhc
git pull
./venv/bin/pip install -U mcp python-docx openpyxl pyyaml
systemctl restart vbhc-mcp        # nếu dùng systemd (5A)
# Hoặc: aaPanel → Python Project → click Restart hàng vbhc-mcp (nếu dùng 5B)
```

### 12.2. Sửa YAML cơ quan

Sửa file trong `/root/.vbhc/org/` qua aaPanel File Manager hoặc nano. **PHẢI restart MCP service** sau khi sửa (server cache config khi load).

### 12.3. Quản lý API keys

```bash
cd /home/mcp-soan-thao-vbhc

# Thêm key mới
./venv/bin/python scripts/manage_keys.py add <id> --description "..." [--ips ip1,ip2] [--rate-limit N]

# Liệt kê
./venv/bin/python scripts/manage_keys.py list

# Vô hiệu (giữ trong yaml)
./venv/bin/python scripts/manage_keys.py revoke <id>

# Đổi key (giữ id, key mới — key cũ KHÔNG còn tác dụng sau restart service)
./venv/bin/python scripts/manage_keys.py rotate <id>

# Xoá hẳn
./venv/bin/python scripts/manage_keys.py delete <id>

# Sau bất kỳ thao tác nào → restart service
systemctl restart vbhc-mcp
```

File yaml: `/root/.vbhc/org/api-keys.yaml` (chmod 600). Backup file này khi đổi.

### 12.4. Backup quan trọng

| Cần backup | Tần suất |
|---|---|
| `/root/.vbhc/org/` (gồm `api-keys.yaml`) | Mỗi khi sửa keys hoặc YAML cơ quan |
| `/home/mcp-soan-thao-vbhc/` | Mỗi khi update code |
| `/www/server/panel/vhost/cert/mcp.hagiang.edu.vn/` | Tự động qua aaPanel |

Lệnh backup nhanh:
```bash
tar czf /root/vbhc-backup-$(date +%F).tar.gz \
    /root/.vbhc/org \
    /home/mcp-soan-thao-vbhc/scripts \
    /home/mcp-soan-thao-vbhc/resources
```

> **Lưu ý**: `api-keys.yaml` chứa plain key — file đã chmod 600 nhưng backup tar nên cũng phải lưu nơi chỉ admin truy cập được.

### 12.5. Renew SSL

aaPanel tự renew Let's Encrypt qua scheduler nội bộ — **không cần làm gì**.

Verify hạn cert hiện tại:
```bash
echo | openssl s_client -connect mcp.hagiang.edu.vn:443 2>/dev/null | openssl x509 -noout -dates
# notBefore=...
# notAfter=...
```

Nếu sắp hết hạn mà chưa renew → manual renew trong aaPanel: Website → site → SSL tab → **Renew**.

### 12.6. Xem log

```bash
# MCP server log
journalctl -u vbhc-mcp -n 100 -f          # systemd
# Hoặc: aaPanel → Python Project → Log

# nginx access log
tail -f /www/wwwlogs/mcp.hagiang.edu.vn.log

# nginx error log
tail -f /www/wwwlogs/mcp.hagiang.edu.vn.error.log
```

### 12.7. Restart full stack (sau reboot VPS)

VPS reboot → tất cả tự khởi động lại nhờ:
- `systemctl enable vbhc-mcp` đã set ở Bước 5A
- Plugin Python Project Manager bật **Auto start on boot**
- aaPanel + nginx tự start

Verify sau reboot:
```bash
systemctl is-active vbhc-mcp        # active
systemctl is-active nginx 2>/dev/null || /etc/init.d/nginx status   # running
```

---

## 13. Troubleshooting

### Client báo "MCP server vbhc connection failed"

Test theo thứ tự:

```bash
# 1. MCP server có chạy không?
systemctl status vbhc-mcp
# Hoặc xem Python Project list trong aaPanel

# 2. Server có nghe port 8765 không?
ss -tlnp | grep 8765
# Phải thấy: LISTEN 127.0.0.1:8765

# 3. Local request OK?
curl -i http://127.0.0.1:8765/mcp
# 405/406 → OK

# 4. Qua nginx OK (chưa auth)?
curl -i https://mcp.hagiang.edu.vn/mcp
# 401 (đúng — đang yêu cầu auth)

# 5. Qua nginx + auth OK?
curl -i -u admin:PASSWORD https://mcp.hagiang.edu.vn/mcp
# 405/406

# 6. Nếu bước 5 timeout → nginx có buffer lỗi
#    → quay lại Bước 8.2 verify proxy_buffering off
```

### Status code 401 dù gõ đúng API key

```bash
# 1. Key có trong YAML không?
./venv/bin/python scripts/manage_keys.py list --show-keys
# Cột "revoked" = "YES" → key bị vô hiệu

# 2. Server đã reload config sau khi thêm/sửa key chưa?
systemctl restart vbhc-mcp
journalctl -u vbhc-mcp -n 5 | grep "API keys"
# Phải thấy: "API keys = .../api-keys.yaml (N key(s))" với N đúng số key

# 3. Header trong client config có đúng format không?
# Phải là: Authorization: Bearer vbhc_<64hex> (có space giữa Bearer và key)
```

### Status code 403

Key có `allowed_ips` không match IP nguồn của client.
- Xem nginx access log: `tail -f /www/wwwlogs/mcp.hagiang.edu.vn.log` — cột $remote_addr là IP server thấy.
- Update yaml hoặc set `allowed_ips: []` để allow all.

### Status code 429 Too Many Requests

Key vượt rate limit. Tăng `rate_limit_per_minute` trong yaml hoặc rotate với rate cao hơn.

### Status code 502 Bad Gateway

MCP server crash hoặc dừng. Check:
```bash
systemctl status vbhc-mcp
journalctl -u vbhc-mcp -n 50
# Tìm "Error", "Traceback"
```

Nguyên nhân thường gặp:
- ORG dir thiếu file → `mkdir -p /root/.vbhc/org && cp /home/mcp-soan-thao-vbhc/tri-thuc-template/*.yaml /root/.vbhc/org/`
- YAML syntax sai → `python3 -c "import yaml; yaml.safe_load(open('/root/.vbhc/org/05-thong-tin-co-quan.yaml'))"`
- Port 8765 bị process khác chiếm → `ss -tlnp | grep 8765`

### Status code 504 Gateway Timeout

Request vào MCP nhưng MCP không response trong thời gian nginx chờ.

- Check Bước 8.2: `proxy_read_timeout 86400s` đã có?
- MCP server có treo? `journalctl -u vbhc-mcp -n 30 -f` → gọi tool xem có log gì
- Tăng tài nguyên VPS nếu RAM/CPU đầy

### nginx báo `nginx -t` syntax error sau khi save Configuration file

```bash
/www/server/nginx/sbin/nginx -t
# Phải in ra dòng nào lỗi (file + line number)
```

Mở file đó, xem dòng đó, kiểm tra:
- Dấu `{` `}` có match không
- Mỗi `;` cuối câu lệnh
- Tên directive đúng chính tả

Nếu rối → khôi phục từ backup config aaPanel tự tạo:
```bash
ls /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf*
# Có thể có file .bak
```

### Response body: `Invalid Host header`

Triệu chứng: `curl -i -u admin:pass https://mcp.hagiang.edu.vn/mcp` trả 400 + body `Invalid Host header` (không phải 405/406 mong đợi).

Nguyên nhân: FastMCP/Starlette có `TrustedHostMiddleware` mặc định chỉ accept Host header = `127.0.0.1` hoặc `localhost`. Khi nginx forward `Host: mcp.hagiang.edu.vn` (do `proxy_set_header Host $host;`) → middleware reject.

Fix: sửa block `location ^~ /mcp` trong nginx config — dòng `proxy_set_header Host`:

```nginx
# Đổi từ:
proxy_set_header Host              $host;

# Thành:
proxy_set_header Host              127.0.0.1:8765;
proxy_set_header X-Forwarded-Host  $host;
```

Save → reload nginx. Test lại curl phải ra 405/406.

### Heredoc paste fail — file service không tạo / `bash: warning: here-document delimited by end-of-file`

Triệu chứng: bạn paste block `cat > ... <<'EOF' ... EOF` vào terminal, nhưng terminal hiện prompt `>` chờ tiếp, hoặc Ctrl+C xong `cat /etc/systemd/system/vbhc-mcp.service` báo "No such file".

Nguyên nhân:
- Dòng `EOF` cuối bị thụt space đầu (`  EOF` thay vì `EOF`) → bash KHÔNG nhận là kết thúc → treo
- Dòng `ExecStart=...` bị wrap thành 2 dòng do terminal hẹp → systemd parse lỗi sau này

Fix — dùng cách an toàn nhất (copy file từ repo):
```bash
cp /home/mcp-soan-thao-vbhc/deploy/vbhc-mcp.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vbhc-mcp
```

Hoặc dùng `nano` (paste không lo wrap):
```bash
nano /etc/systemd/system/vbhc-mcp.service
# Paste content từ deploy/vbhc-mcp.service, Ctrl+O, Enter, Ctrl+X
systemctl daemon-reload
systemctl enable --now vbhc-mcp
```

### Plugin Python Project Manager: project Stopped sau khi Add

Click **Log** xem error:

| Error | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | Startup command đang gọi Python system thay vì venv. Sửa thành full path `/home/mcp-soan-thao-vbhc/venv/bin/python ...` |
| `Address already in use` | Port 8765 đã bị systemd `vbhc-mcp` chiếm. Tắt systemd hoặc chọn 1 trong 2: `systemctl disable --now vbhc-mcp` |
| `No such file or directory: '...mcp/server.py'` | Project path sai. Edit project, sửa lại |

### Cloudflare đang proxy → SSL apply fail

DNS record `mcp` đang ở chế độ "đám mây cam" (proxy on). Let's Encrypt HTTP-01 challenge sẽ fail vì Cloudflare chặn port 80 từ Let's Encrypt servers.

Fix:
1. Cloudflare DNS → click vào record `mcp` → đổi proxy thành "đám mây xám" (DNS only)
2. Đợi 1-2 phút
3. Quay lại aaPanel SSL → Apply lại

Sau khi cấp xong, có thể bật lại proxy Cloudflare nhưng phải chuyển SSL mode trong Cloudflare → **Full (strict)**.

### File Word output không có dấu gạch chân header

Code đang dùng python-docx thủ công thay vì `vbhc_doc_builder`. Xem `scripts/vbhc_doc_builder.py` — phải import + dùng `add_header_section()`, `add_so_vb_and_date_section()`, `add_signature_noi_nhan()`. KHÔNG tự build table 2x2 cho header.

### MCP service chết sau vài giờ

```bash
journalctl -u vbhc-mcp -n 100 | grep -i -E "error|killed|oom"
```

Thường gặp:
- OOM (out of memory) → upgrade RAM VPS hoặc giảm concurrent users
- Exception trong Python code → sửa bug, restart

systemd service đã có `Restart=always` nên tự khởi động lại — chỉ cần fix root cause.

---

## Phụ lục — Lệnh hữu ích

```bash
# === MCP service (systemd 5A) ===
systemctl status vbhc-mcp                    # trạng thái
systemctl restart vbhc-mcp                   # restart
journalctl -u vbhc-mcp -n 100 -f             # log realtime

# === MCP service (Plugin 5B) ===
# Quản lý qua aaPanel → Python Project

# === nginx (do aaPanel quản lý) ===
/www/server/nginx/sbin/nginx -t              # test config
/etc/init.d/nginx reload                     # reload
/etc/init.d/nginx status                     # trạng thái

# === SSL ===
echo | openssl s_client -connect mcp.hagiang.edu.vn:443 2>/dev/null | \
    openssl x509 -noout -dates               # xem hạn cert

# === Auth ===
htpasswd -c /www/server/nginx/conf/htpasswd-vbhc admin    # tạo mới (XÓA file cũ)
htpasswd /www/server/nginx/conf/htpasswd-vbhc user2       # thêm user (giữ user cũ)

# === Backup ===
tar czf /root/vbhc-$(date +%F).tar.gz /root/.vbhc/org \
    /www/server/nginx/conf/htpasswd-vbhc \
    /home/mcp-soan-thao-vbhc/scripts /home/mcp-soan-thao-vbhc/resources

# === Test toàn bộ ===
curl -i https://mcp.hagiang.edu.vn/mcp                          # 401
curl -i -u admin:PASS https://mcp.hagiang.edu.vn/mcp            # 405/406
```

---

## Kết

Sau khi xong tất cả các bước, bạn có:
- MCP `vbhc` chạy 24/7 trên VPS với auto-restart
- Domain HTTPS riêng + SSL tự renew
- Basic Auth bảo vệ
- File YAML cơ quan ở `/root/.vbhc/org/` để cập nhật khi có thay đổi nhân sự/phòng ban
- Mọi user trong cơ quan dùng cùng 1 server, share config chung

Khi cần hỗ trợ — gửi kèm output:
```bash
systemctl status vbhc-mcp
journalctl -u vbhc-mcp -n 50
tail -50 /www/wwwlogs/mcp.hagiang.edu.vn.error.log
curl -i https://mcp.hagiang.edu.vn/mcp
```
