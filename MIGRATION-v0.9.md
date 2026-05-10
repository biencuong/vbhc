# Migration v0.9.0 — chuyển từ Basic Auth sang API key

> **Đối tượng**: VPS đang chạy phiên bản trước v0.9.0 với nginx Basic Auth (htpasswd, user `admin`).
> **Sau migration**: nginx chỉ làm SSL + reverse proxy, **MCP server** tự kiểm `Authorization: Bearer <key>`.

---

## Vì sao đổi?

| Basic Auth (cũ) | API key (v0.9.0) |
|---|---|
| 1 password chia sẻ | Mỗi máy 1 key riêng |
| Không revoke từng client | Revoke 1 key, các key khác vẫn dùng được |
| Không biết ai gọi gì | `last_used` + audit log per-key |
| Không hạn IP per-client | `allowed_ips` per-key |
| Không rate limit per-client | `rate_limit_per_minute` per-key |

---

## Quy trình 8 bước (15-20 phút)

### Bước 1 — Backup

```bash
# Bao gồm: config nginx Basic Auth, ORG dir hiện tại
tar czf /root/vbhc-pre-v0.9-$(date +%F).tar.gz \
    /root/.vbhc \
    /www/server/nginx/conf/htpasswd-vbhc \
    /home/mcp-soan-thao-vbhc/scripts \
    /home/mcp-soan-thao-vbhc/resources \
    2>/dev/null

ls -la /root/vbhc-pre-v0.9-*.tar.gz
```

### Bước 2 — Pull code v0.9.0

```bash
cd /home/mcp-soan-thao-vbhc
git fetch --tags
git checkout v0.9.0
```

### Bước 3 — Chạy installer (idempotent)

```bash
bash deploy/install-server.sh
```

Installer làm:
- `pip install` thêm `uvicorn` (deps mới)
- Tạo `/root/.vbhc/org/api-keys.yaml` với **1 key admin random** + `chmod 600`
- Cập nhật service file thêm env `VBHC_API_KEYS_FILE`
- Restart service

**Phải xuất hiện ở output:**
```
[WARN] ===================================================================
[WARN]   KEY ADMIN: vbhc_xxxxxxxxxxxxxxxxxxxxxxxx...
[WARN]   → LƯU LẠI NGAY — đặt vào config client (Authorization: Bearer ...)
[WARN] ===================================================================
```

**LƯU LẠI KEY NÀY** — sẽ dùng ở Bước 7 cho client config. Nếu lỡ mất, xem lại trong file:
```bash
cat /root/.vbhc/org/api-keys.yaml
```

### Bước 4 — Cấp key cho từng client (nếu nhiều máy)

Mỗi máy người dùng 1 key riêng:

```bash
cd /home/mcp-soan-thao-vbhc
./venv/bin/python scripts/manage_keys.py add laptop-an --description "An laptop"
./venv/bin/python scripts/manage_keys.py add may-vt   --description "Máy văn thư"
```

Mỗi lệnh in ra `vbhc_xxx` — ghi lại để cấp cho người dùng tương ứng.

Tuỳ chọn nâng cao:
```bash
# Giới hạn IP + rate limit cho 1 key
./venv/bin/python scripts/manage_keys.py add may-vt \
    --description "Máy văn thư" \
    --ips 192.168.1.50 \
    --rate-limit 60
```

Restart service để load keys mới:
```bash
systemctl restart vbhc-mcp
journalctl -u vbhc-mcp -n 10
# Phải thấy: "API keys = .../api-keys.yaml (N key(s))"
```

Liệt kê tất cả keys (để kiểm tra):
```bash
./venv/bin/python scripts/manage_keys.py list
```

### Bước 5 — Sửa nginx config: XÓA 2 dòng Basic Auth

Vào aaPanel → **Website** → click site `mcp.hagiang.edu.vn` → **Configuration file**.

Tìm 2 dòng trong block `location ^~ /mcp`:
```nginx
auth_basic           "VBHC MCP";
auth_basic_user_file /www/server/nginx/conf/htpasswd-vbhc;
```

**Xóa hoặc comment cả 2 dòng**:
```nginx
# auth_basic           "VBHC MCP";
# auth_basic_user_file /www/server/nginx/conf/htpasswd-vbhc;
```

Save (aaPanel auto-reload nginx). Nếu không auto:
```bash
/www/server/nginx/sbin/nginx -t && /etc/init.d/nginx reload
```

### Bước 6 — Verify server-side check thay nginx

```bash
# Không Authorization header → 401 (do MCP server, KHÔNG phải nginx)
curl -i https://mcp.hagiang.edu.vn/mcp
# HTTP/2 401
# www-authenticate: Bearer realm="vbhc"
# {"error":"Missing 'Authorization: Bearer <key>' header"}

# Sai key → 401
curl -i -H "Authorization: Bearer vbhc_wrong" https://mcp.hagiang.edu.vn/mcp
# 401, body {"error":"Invalid API key"}

# Đúng key → 405 (server reach OK, GET không hợp lệ cho MCP)
curl -i -H "Authorization: Bearer vbhc_<key-thật-từ-bước-3>" https://mcp.hagiang.edu.vn/mcp
# HTTP/2 405 hoặc 406

# Basic Auth cũ KHÔNG còn tác dụng
curl -i -u admin:OLDPASS https://mcp.hagiang.edu.vn/mcp
# 401 (vì server check Bearer, không phải Basic)
```

### Bước 7 — Cập nhật config client

Trên mỗi máy người dùng — sửa file config Claude Code/Cursor/Cline...

**Trước (Basic Auth)**:
```json
{
  "mcpServers": {
    "vbhc": {
      "url": "https://admin:OLDPASS@mcp.hagiang.edu.vn/mcp"
    }
  }
}
```

**Sau (Bearer)**:
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

File config theo agent (xem [INSTALL-AAPANEL.md](INSTALL-AAPANEL.md) Bước 11):
- Claude Code: `~/.claude.json` hoặc `claude mcp add` CLI
- Cursor: `~/.cursor/mcp.json`
- Claude Desktop: `%APPDATA%\Claude\claude_desktop_config.json` (Win) / `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)
- Cline: UI Settings → MCP Servers → Add → header `Authorization: Bearer ...`

Restart agent. Test trong agent:
> "Liệt kê các tool MCP `vbhc_*` bạn có"

→ Phải thấy đủ 11 tools (9 cũ + 2 mới: `vbhc_learn_template`, `vbhc_update_template`).

### Bước 8 — (Tuỳ chọn) Xoá htpasswd cũ

Sau khi mọi client đã chuyển sang Bearer:

```bash
rm /www/server/nginx/conf/htpasswd-vbhc
```

---

## Troubleshooting

### Client báo 401 dù gõ đúng key

```bash
# 1. Key có trong YAML không?
./venv/bin/python scripts/manage_keys.py list --show-keys

# 2. Key có bị revoked không?
# (cột "revoked" trong list trên = "YES" → vô hiệu)

# 3. Server đã reload config chưa?
systemctl restart vbhc-mcp
journalctl -u vbhc-mcp -n 5
# Tìm dòng "API keys = ... (N key(s))" — N phải đúng số key

# 4. IP có whitelist không?
# Nếu key có allowed_ips != [], request phải đến từ IP đó.
# Check IP nguồn nginx forward:
tail -20 /www/wwwlogs/mcp.hagiang.edu.vn.log
```

### Status 429 Too Many Requests

Key vượt rate limit. Tăng:
```bash
# Dùng manage_keys.py để rotate với rate cao hơn (chưa expose trực tiếp).
# Workaround: edit yaml trực tiếp:
nano /root/.vbhc/org/api-keys.yaml
# Sửa rate_limit_per_minute lên cao hơn
systemctl restart vbhc-mcp
```

### Status 403

Key có `allowed_ips` không match IP nguồn.
- Check IP thật của client: client có thể đi qua NAT/CDN — nginx thấy IP khác client.
- Xem `X-Real-IP` trong nginx log: `tail -f /www/wwwlogs/mcp.hagiang.edu.vn.log`
- Sửa `allowed_ips` trong yaml hoặc set `[]` (allow all).

### Server không start, log "API keys file not found"

```bash
# File phải tồn tại + user vbhc-mcp service đọc được
ls -la /root/.vbhc/org/api-keys.yaml
# -rw------- 1 root root ... → quyền 600 cho root

# Service chạy với user nào? (mặc định root)
systemctl cat vbhc-mcp | grep User
```

Nếu service chạy với user khác root → đổi quyền hoặc dùng group.

### Rollback (nếu có vấn đề)

```bash
# 1. Restore Basic Auth file
tar xzf /root/vbhc-pre-v0.9-*.tar.gz -C /
# (sẽ restore /www/server/nginx/conf/htpasswd-vbhc + /root/.vbhc/...)

# 2. Sửa lại nginx config: thêm 2 dòng auth_basic
# (qua aaPanel Configuration file)

# 3. Checkout commit cũ
cd /home/mcp-soan-thao-vbhc
git checkout d67fd3e            # hoặc tag/commit cũ trước v0.9.0
systemctl restart vbhc-mcp
```

---

## Sau migration

- Memory: trong skill nội bộ, đã cập nhật `vps_deploy_vbhc.md` để phản ánh API key
- Backup yaml định kỳ: `/root/.vbhc/org/api-keys.yaml` (file quan trọng — mất key admin = restore từ backup hoặc rotate)
- Audit: log hệ thống MCP server có dòng `auth_ok kid=<id> ip=<x> ...` cho mọi request hợp lệ — `journalctl -u vbhc-mcp | grep auth_ok` để track
