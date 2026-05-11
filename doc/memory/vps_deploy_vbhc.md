---
name: VPS deploy VBHC MCP — production endpoint + API key auth (v0.9.0+)
description: VBHC MCP server production trên VPS aaPanel — auth API key Bearer per-client (v0.9.0+); chỗ tìm config + lệnh quản lý keys
type: project
originSessionId: 48676b67-ecfe-4106-963b-dd5080809ce6
---
## Endpoint production
- URL: `https://mcp.hagiang.edu.vn/mcp`
- Stack: aaPanel + nginx (reverse proxy + SSL only — KHÔNG còn Basic Auth từ v0.9.0) → FastMCP listen `127.0.0.1:8765`
- Service systemd: `vbhc-mcp.service` (workdir `/home/mcp-soan-thao-vbhc/`)
- Env: `VBHC_ORG_DIR=/root/.vbhc/org`, `VBHC_API_KEYS_FILE=/root/.vbhc/org/api-keys.yaml`

## Auth — API key Bearer (v0.9.0+)
- File keys: `/root/.vbhc/org/api-keys.yaml` (chmod 600 — chỉ root đọc)
- Format key: `vbhc_<32-byte-hex>` (64 chars sau prefix)
- Server kiểm qua `mcp/auth.py` (Starlette middleware) — KHÔNG còn nginx auth_basic
- Per-key features: `allowed_ips` (whitelist) + `rate_limit_per_minute` (token bucket) + `revoked` flag + `last_used` (audit)

**Trước v0.9.0** dùng nginx Basic Auth (htpasswd, user `admin`) — đã chuyển. Nếu VPS chưa migrate, xem `MIGRATION-v0.9.md` trong skill repo.

## Lệnh quản lý nhanh (chạy trên VPS, root)
```bash
cd /home/mcp-soan-thao-vbhc

# Cấp key cho 1 máy
./venv/bin/python scripts/manage_keys.py add laptop-an --description "An laptop" [--ips 10.0.0.5] [--rate-limit 60]

# Liệt kê
./venv/bin/python scripts/manage_keys.py list [--show-keys]

# Vô hiệu key (giữ trong yaml)
./venv/bin/python scripts/manage_keys.py revoke laptop-an

# Đổi key (giữ id, sinh key mới — key cũ KHÔNG còn tác dụng)
./venv/bin/python scripts/manage_keys.py rotate laptop-an

# Xoá hẳn
./venv/bin/python scripts/manage_keys.py delete laptop-an

# Apply: restart service (server cache config khi start)
systemctl restart vbhc-mcp
journalctl -u vbhc-mcp -n 5    # phải thấy "API keys = ... (N key(s))"

# Verify
curl -i https://mcp.hagiang.edu.vn/mcp                                  # 401 (do server)
curl -i -H "Authorization: Bearer vbhc_xxx" https://mcp.hagiang.edu.vn/mcp  # 405 OK
```

## Critical nginx config gotcha (đã fix, đừng đụng)
- `proxy_set_header Host 127.0.0.1:8765` — BẮT BUỘC để qua TrustedHostMiddleware của FastMCP/Starlette. Nếu để mặc định `$host` (domain ngoài) → FastMCP reject "Invalid Host header".
- aaPanel auto-sinh block `#PROXY-START/...#PROXY-END/` — sửa TRỰC TIẾP trong file config (giữ marker), KHÔNG sửa qua UI Reverse Proxy (sẽ bị regen mất).
- v0.9.0 đã XOÁ 2 dòng `auth_basic` trong nginx config. Không thêm lại.

## Client config
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

## Why
Trước v0.9.0 dùng 1 password Basic Auth chia sẻ → không revoke từng client, không audit, không rate limit per-client. v0.9.0 chuyển sang API key per-client với metadata phong phú.

## How to apply
- User nói "cấp key cho máy mới" → `manage_keys.py add <id>` + cấp key Bearer cho client
- User báo lỗi 401 → check key có revoked không, server đã restart sau khi sửa yaml chưa, header có đúng `Bearer vbhc_xxx` không
- User báo 403 → IP whitelist mismatch — xem nginx access log lấy IP thật
- User báo 429 → vượt rate limit per-key — tăng `rate_limit_per_minute` trong yaml
- Tài liệu chi tiết: `D:\SKILL_AI\skills\soan-thao-vbhc\INSTALL-AAPANEL.md` mục 9 + `MIGRATION-v0.9.md` + `HANDOFF.md` Section 14
