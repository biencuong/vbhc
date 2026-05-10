# 🚀 Kế hoạch nâng cấp: 1 MCP Server — Nhiều máy con

## Kiến trúc mục tiêu

```
                        INTERNET
                           │
              ┌────────────┴────────────┐
              │     VPS Ubuntu + aaPanel│
              │                         │
              │  Nginx (HTTPS :443)     │
              │   ├─ SSL Let's Encrypt  │
              │   ├─ auth_basic         │
              │   └─ /mcp ──┐           │
              │             ▼           │
              │  FastMCP :8765          │
              │  streamable-http        │
              │  ┌─ Session A ──┐       │
              │  │  Máy A       │       │
              │  ├─ Session B ──┤       │
              │  │  Máy B       │       │
              │  └─ Session C ──┘       │
              └─────────────────────────┘
```

## Thông tin hiện tại

| Thông tin | Giá trị |
|---|---|
| **VPS** | Ubuntu + aaPanel |
| **MCP Server path** | `/home/mcp-soan-thao-vbhc/mcp/server.py` |
| **Python venv** | `/home/mcp-soan-thao-vbhc/venv` |
| **Service** | `vbhc-mcp` (systemd) |
| **Port** | `8765` |
| **Nginx config** | aaPanel quản lý |
| **auth file** | `/www/server/nginx/conf/htpasswd-vbhc` |
| **ORG dir** | `/root/.vbhc/org/` |

---

## 📋 Kế hoạch 6 bước

### Bước 0: Kiểm tra hiện trạng

SSH vào VPS với **root**, chạy:

```bash
# 1. MCP server có chạy không?
systemctl status vbhc-mcp

# 2. Version mcp package là bao nhiêu?
source /home/mcp-soan-thao-vbhc/venv/bin/activate
python -c "import mcp; print(f'mcp version: {mcp.__version__}')"

# 3. Port 8765 đang nghe?
ss -tlnp | grep 8765

# 4. Nginx config hiện tại?
cat /www/server/panel/vhost/nginx/*.conf | grep -A 30 "location.*mcp"
```

> ⏱ 2 phút — 🎯 Xác định chính xác version hiện tại

---

### Bước 1: Nâng cấp `mcp` package (QUAN TRỌNG)

**Lý do:** FastMCP version cũ (< 1.3.0) chỉ hỗ trợ 1 session. Phiên bản mới (>= 1.3.0) hỗ trợ multi-session.

```bash
# Kích hoạt venv
source /home/mcp-soan-thao-vbhc/venv/bin/activate

# Nâng cấp lên bản mới nhất
pip install --upgrade mcp

# Kiểm tra lại version
python -c "import mcp; print(f'mcp version: {mcp.__version__}')"
# Cần >= 1.3.0, lý tưởng >= 1.6.0

# Restart service
systemctl restart vbhc-mcp

# Kiểm tra log
sleep 2
journalctl -u vbhc-mcp -n 20 --no-pager
```

> ⏱ 3 phút — ⚠️ Rủi ro thấp

**Rollback nếu cần:**
```bash
source /home/mcp-soan-thao-vbhc/venv/bin/activate
pip install mcp==1.0.0   # hoặc version cũ
systemctl restart vbhc-mcp
```

---

### Bước 2: Test multi-session trên VPS

**Cách 1 — Dùng tmux (khuyên dùng):**
```bash
tmux new -s test-a
curl -N -u admin:PASS https://mcp.hagiang.edu.vn/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-A","version":"1"}}}'
```
➡️ `Ctrl+B, d` để detach

```bash
tmux new -s test-b
curl -N -u admin:PASS https://mcp.hagiang.edu.vn/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-B","version":"1"}}}'
```

**Cách 2 — Dùng terminal riêng:** Mở 2 terminal SSH riêng, chạy 2 lệnh curl cùng lúc.

> ✅ Cả 2 đều response → **thành công!**
> ❌ Session A mất khi B kết nối → xuống **Bước dự phòng**

---

### Bước 3: Tạo tài khoản riêng cho mỗi máy

```bash
# Thêm user cho từng máy
htpasswd /www/server/nginx/conf/htpasswd-vbhc mayA
# Nhập password

htpasswd /www/server/nginx/conf/htpasswd-vbhc mayB
# Nhập password

# Kiểm tra
cat /www/server/nginx/conf/htpasswd-vbhc
# mayA:$apr1$xxx...
# mayB:$apr1$yyy...
```

---

### Bước 4: Cấu hình từng máy client

**Máy A — `mcp.json`:**
```json
{
  "mcpServers": {
    "vbhc": {
      "url": "https://mayA:PASS_A@mcp.hagiang.edu.vn/mcp",
      "transport": "streamable-http"
    }
  }
}
```

**Máy B — `mcp.json`:**
```json
{
  "mcpServers": {
    "vbhc": {
      "url": "https://mayB:PASS_B@mcp.hagiang.edu.vn/mcp",
      "transport": "streamable-http"
    }
  }
}
```

---

### Bước 5: Kiểm tra end-to-end

1. Restart QwenPaw trên cả 2 máy
2. Trên máy A: gọi tool `vbhc_classify`
3. Trên máy B (cùng lúc): gọi tool `vbhc_classify`
4. Cả 2 đều trả về kết quả → **thành công!**

---

### Bước 6: Vận hành

```bash
# Xem log realtime
journalctl -u vbhc-mcp -n 50 -f

# Xem ai đang truy cập
tail -f /www/wwwlogs/mcp.hagiang.edu.vn.log

# Restart
systemctl restart vbhc-mcp

# Update code
cd /home/mcp-soan-thao-vbhc
git pull
systemctl restart vbhc-mcp

# Đổi password
htpasswd /www/server/nginx/conf/htpasswd-vbhc mayA
```

---

## 🚨 GIẢI PHÁP DỰ PHÒNG (nếu vẫn 1 session)

Nếu nâng cấp `mcp` vẫn không fix được, dùng **Multi-instance + Nginx upstream**:

### Bước A: Tạo nhiều instance service

```bash
for i in 8765 8766 8767; do
  cat > /etc/systemd/system/vbhc-mcp-${i}.service <<SERVICEEOF
[Unit]
Description=VBHC MCP Server - Instance ${i}
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/mcp-soan-thao-vbhc
Environment="VBHC_ORG_DIR=/root/.vbhc/org"
Environment="PYTHONIOENCODING=utf-8"
ExecStart=/home/mcp-soan-thao-vbhc/venv/bin/python \\
  /home/mcp-soan-thao-vbhc/mcp/server.py \\
  --http --host 127.0.0.1 --port ${i}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICEEOF

  systemctl enable --now vbhc-mcp-${i}
  echo "Started vbhc-mcp-${i} on port ${i}"
done
```

### Bước B: Sửa Nginx config

Trong aaPanel → Website → **Configuration file** → sửa block `#PROXY-START/`:

```nginx
#PROXY-START/
upstream mcp_backend {
    server 127.0.0.1:8765;
    server 127.0.0.1:8766;
    server 127.0.0.1:8767;
}

location ^~ /mcp
{
    auth_basic           "VBHC MCP";
    auth_basic_user_file /www/server/nginx/conf/htpasswd-vbhc;

    proxy_pass http://mcp_backend;
    proxy_http_version 1.1;
    proxy_set_header Host              127.0.0.1:8765;
    proxy_set_header X-Forwarded-Host  $host;
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
#PROXY-END/
```

Save → reload:

```bash
/etc/init.d/nginx reload
```

### Bước C: Dừng service cũ (nếu muốn)

```bash
systemctl disable --now vbhc-mcp   # tắt service đơn cũ
```

---

## 📊 So sánh giải pháp

| Tiêu chí | Nâng cấp `mcp` (Chính) | Multi-instance (Dự phòng) |
|---|---|---|
| **Độ khó** | ✅ Dễ (3 lệnh) | ⚠️ Trung bình |
| **Tài nguyên** | ✅ 1 process, ít RAM | ❌ N process, tốn RAM hơn |
| **Số client tối đa** | Phụ thuộc mcp version | N instance = N client |
| **Bảo trì** | ✅ Đơn giản | ⚠️ Phức tạp hơn |
| **Nên dùng** | **Thử trước** | **Chỉ dùng nếu cách 1 fail** |

---

## 📝 Lệnh thực thi nhanh (copy-paste vào SSH)

```bash
# === BẮT ĐẦU ===
echo "=== B0: Kiểm tra ==="
source /home/mcp-soan-thao-vbhc/venv/bin/activate
python -c "import mcp; print(f'Current: {mcp.__version__}')"

echo "=== B1: Nâng cấp ==="
pip install --upgrade mcp
python -c "import mcp; print(f'Upgraded: {mcp.__version__}')"

echo "=== B2: Restart ==="
systemctl restart vbhc-mcp
sleep 2
systemctl status vbhc-mcp

echo "=== B3: Log ==="
journalctl -u vbhc-mcp -n 30 --no-pager

echo "=== DONE — Test từ 2 máy client ==="
```

---

> **Tác giả:** Phân tích từ mã nguồn `soan-thao-vbhc` skill
> **Ngày:** 2026-05-11
