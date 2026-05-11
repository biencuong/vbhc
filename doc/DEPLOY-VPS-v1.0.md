# Deploy v1.0.0 lên VPS production

> **Mục tiêu**: Chuyển `mcp.hagiang.edu.vn` từ v0.9 (HTTP MCP) sang v1.0 (Knowledge Hub). Sau deploy: endpoint cũ `/mcp` không còn — user buộc migrate sang local thin-MCP.

## Tóm tắt thay đổi trên VPS

| Hạng mục | v0.9 (đang chạy) | v1.0 (sau deploy) |
|---|---|---|
| Service systemd | `vbhc-mcp.service` (port 8765, HTTP MCP) | `vbhc-kb.service` (port 8766, Knowledge Hub) |
| KB_DIR | (không có) | `/var/lib/vbhc-kb/` (manifest, templates, rules, code, install.ps1) |
| Nginx routes | `location /mcp` → 8765 | `location /kb`, `/install.ps1`, `/uninstall.ps1`, `/healthz` → 8766 |
| API key scope | (chỉ read) | Thêm `admin` cho key admin để publish |
| Endpoint `/mcp` | ✓ hoạt động | ✗ trả 404 (user phải migrate) |

## Trước khi bắt đầu — chuẩn bị (5 phút)

### Backup trên VPS

SSH vào VPS rồi:

```bash
# 1. Backup nginx config hiện tại
sudo cp -a /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf \
           /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf.bak-pre-v1.0

# 2. Backup api-keys.yaml
sudo cp -a /root/.vbhc/org/api-keys.yaml \
           /root/.vbhc/org/api-keys.yaml.bak-pre-v1.0

# 3. Ghi lại version hiện tại
cd /home/mcp-soan-thao-vbhc
git log --oneline -1 > /tmp/vbhc-pre-v1.0-commit.txt
cat /tmp/vbhc-pre-v1.0-commit.txt
# Lưu sha này — dùng cho rollback
```

### Thông báo user trước (tùy chọn nhưng nên có)

Nếu có nhiều cán bộ đang dùng v0.9, gửi tin trước 24h:

> "Hệ MCP `vbhc` sẽ update lên v1.0 lúc <giờ>. File user sẽ chạy local trên máy bạn (không upload server nữa). Sau deploy bạn cần chạy lại 1-lệnh PowerShell — chi tiết trong tin nhắn sau."

---

## Bước 1 — Pull code v1.0.0

```bash
cd /home/mcp-soan-thao-vbhc
git fetch --tags
git checkout v1.0.0
git log --oneline -1   # phải thấy commit 02111fe hoặc 8389df3
```

Verify file mới có mặt:

```bash
ls cloud/install.ps1 cloud/uninstall.ps1 cloud/kb_server.py cloud/build_manifest.py
ls mcp/bootstrap.py mcp/knowledge_client.py
ls tri-thuc-template/rules/the-thuc.yaml
```

Tất cả phải tồn tại.

---

## Bước 2 — Cài deps mới

```bash
cd /home/mcp-soan-thao-vbhc
./venv/bin/pip install --upgrade pyyaml uvicorn starlette
./venv/bin/python -c "import yaml, uvicorn, starlette; print('OK')"
```

Nếu lỗi externally-managed-environment, dùng `--break-system-packages` hoặc tạo venv mới — venv đã có sẵn nên không nên gặp.

---

## Bước 3 — Build KB_DIR

```bash
sudo mkdir -p /var/lib/vbhc-kb
sudo chown -R $(whoami):$(whoami) /var/lib/vbhc-kb

./venv/bin/python cloud/build_manifest.py \
    --kb-dir /var/lib/vbhc-kb \
    --import-from-repo /home/mcp-soan-thao-vbhc
```

Output mong đợi:
```
[ok] imported assets from /home/mcp-soan-thao-vbhc → /var/lib/vbhc-kb
[ok] manifest written: /var/lib/vbhc-kb/manifest.json
     templates=3 rules=3 orgs=0 code=v1.0.0+<sha>
```

Verify:

```bash
ls /var/lib/vbhc-kb/
# Phải thấy: code/ install.ps1 manifest.json rules/ templates/ uninstall.ps1

cat /var/lib/vbhc-kb/manifest.json | head -20
ls /var/lib/vbhc-kb/templates/   # 3 file .docx
ls /var/lib/vbhc-kb/rules/       # 3 file .yaml
```

---

## Bước 4 — Cài systemd `vbhc-kb.service`

```bash
sudo cp cloud/vbhc-kb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vbhc-kb
sudo systemctl start vbhc-kb

# Verify
sudo systemctl status vbhc-kb
sudo journalctl -u vbhc-kb -n 20
```

Phải thấy log `[vbhc-kb] HTTP server: http://127.0.0.1:8766` + `API keys = ... (N key(s))`.

Test local (chưa qua nginx):

```bash
curl -i http://127.0.0.1:8766/healthz
# → 200, JSON

# Get một key có sẵn để test (nếu key cũ chưa scope admin, sẽ làm ở Bước 6)
KEY=$(sudo cat /root/.vbhc/org/api-keys.yaml | grep -m1 "key:" | awk '{print $2}')
curl -i -H "Authorization: Bearer $KEY" http://127.0.0.1:8766/kb/manifest.json
# → 200, manifest JSON
```

---

## Bước 5 — Sửa nginx aaPanel

> **Quan trọng**: aaPanel auto-sinh block `#PROXY-START/...#PROXY-END/`. Sửa **trực tiếp file**, KHÔNG qua UI Reverse Proxy (UI sẽ regen mất config tay).

File: `/www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf`

### 5.1. Mở file để sửa

```bash
sudo nano /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf
# hoặc: vim, code-server, v.v.
```

### 5.2. Xác định block hiện tại

Tìm 2 block:

1. `#PROXY-START/...` ... `#PROXY-END/` — aaPanel auto-block (có thể có `location /mcp { proxy_pass http://127.0.0.1:8765; ... }`)
2. Custom block `location /mcp` (nếu bạn đã sửa tay từ v0.9)

### 5.3. Thay block reverse proxy

**Xoá hết** các `location /mcp { ... }` cũ. **Thêm vào** trong block `server { ... }` (cùng cấp với các location khác, BÊN NGOÀI `#PROXY-START/.../#PROXY-END/`):

```nginx
# === vbhc Knowledge Hub v1.0 (port 8766) ===
# Public: installer + uninstaller + healthz (KHÔNG cần auth)
location = /install.ps1 {
    proxy_pass http://127.0.0.1:8766/install.ps1;
    proxy_http_version 1.1;
    proxy_set_header Host 127.0.0.1:8766;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    add_header Cache-Control "no-cache" always;
}

location = /uninstall.ps1 {
    proxy_pass http://127.0.0.1:8766/uninstall.ps1;
    proxy_http_version 1.1;
    proxy_set_header Host 127.0.0.1:8766;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    add_header Cache-Control "no-cache" always;
}

location = /healthz {
    proxy_pass http://127.0.0.1:8766/healthz;
    proxy_http_version 1.1;
    proxy_set_header Host 127.0.0.1:8766;
}

# Auth-protected: knowledge + admin publish
location /kb {
    proxy_pass http://127.0.0.1:8766;
    proxy_http_version 1.1;
    proxy_set_header Host 127.0.0.1:8766;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # Cho phép body lớn cho POST template (max 10MB ở server-side)
    client_max_body_size 12m;
    proxy_request_buffering off;
}

# v0.9 endpoint /mcp đã bị gỡ ở v1.0 — trả 410 Gone với hint migrate
location = /mcp {
    return 410 "v0.9 /mcp endpoint đã bị gỡ ở v1.0. Migrate: https://github.com/biencuong/vbhc/blob/main/MIGRATION-v1.0.md";
    add_header Content-Type "text/plain; charset=utf-8";
}
```

> **Tại sao** `proxy_set_header Host 127.0.0.1:8766`: FastMCP/Starlette dùng TrustedHostMiddleware reject nếu Host header là domain ngoài. Mặc định `$host` sẽ là `mcp.hagiang.edu.vn` → reject.

### 5.4. Test cấu hình + reload

```bash
sudo nginx -t
# → "syntax is ok" + "test is successful"

# Nếu OK, reload:
sudo nginx -s reload
# hoặc qua aaPanel: System → Service → Reload nginx
```

Nếu có lỗi syntax: rollback bằng `sudo cp /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf.bak-pre-v1.0 /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf`.

### 5.5. Smoke test qua nginx (từ máy local)

```bash
# Từ máy bạn, hoặc trên VPS (curl localhost với Host header):
curl -i https://mcp.hagiang.edu.vn/healthz
# → 200 OK, JSON {"status":"ok","kb_dir":"/var/lib/vbhc-kb"}

curl -sI https://mcp.hagiang.edu.vn/install.ps1
# → 200 OK, Content-Type: text/plain; charset=utf-8

curl -i https://mcp.hagiang.edu.vn/kb/manifest.json
# → 401 Unauthorized (chưa Bearer) — đúng

curl -sI -H "Authorization: Bearer <KEY>" https://mcp.hagiang.edu.vn/kb/manifest.json
# → 200 OK

curl -i https://mcp.hagiang.edu.vn/mcp
# → 410 Gone với hint migrate
```

---

## Bước 6 — Dừng service cũ + cấp scope admin

### 6.1. Dừng + disable `vbhc-mcp.service`

```bash
sudo systemctl stop vbhc-mcp
sudo systemctl disable vbhc-mcp

# Verify
sudo systemctl status vbhc-mcp
# → inactive (dead), disabled
```

Không xoá file unit — giữ phòng rollback. Có thể đổi tên cho rõ:

```bash
sudo mv /etc/systemd/system/vbhc-mcp.service /etc/systemd/system/vbhc-mcp.service.deprecated
sudo systemctl daemon-reload
```

### 6.2. Cấp scope `admin` cho ít nhất 1 key

Liệt kê keys hiện có:

```bash
cd /home/mcp-soan-thao-vbhc
./venv/bin/python scripts/manage_keys.py list
```

Chọn 1 key sẽ làm admin (vd id `biencuong-laptop`):

```bash
./venv/bin/python scripts/manage_keys.py grant biencuong-laptop admin
sudo systemctl restart vbhc-kb

# Verify
sudo journalctl -u vbhc-kb -n 5
# → "Loaded N API keys"

./venv/bin/python scripts/manage_keys.py list
# → cột scope của biencuong-laptop = "admin,read"
```

---

## Bước 7 — Test 1-liner installer trên máy mới

> **Quan trọng**: Test trên máy **KHÁC** với máy admin (vd: máy đồng nghiệp, hoặc Windows VM). Nếu test trên máy admin sẽ overwrite MCP entry của bạn.

Trên máy test:

```powershell
iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
```

Khi prompt nhập:
- Cloud URL: Enter (default `https://mcp.hagiang.edu.vn`)
- API key: key có scope `read` (KHÔNG dùng key admin nếu không cần publish)
- Org ID: `so-gddt-tuyen-quang`

Mong đợi: 8 steps PASS, smoke test JSON in ra với `configured: true`, `drift: {templates: [], rules: [], code: null}`.

Trong Claude Code (sau restart):

```
phân loại văn bản: báo cáo quý I/2026
```

→ Tool `vbhc_classify` chạy local, trả về **Báo cáo**.

```
gọi vbhc_knowledge_status
```

→ JSON status với `cloud_url: https://mcp.hagiang.edu.vn`, `cached_assets` ≥ 3 templates + 3 rules.

---

## Bước 8 — Test admin publish (tùy chọn nhưng nên)

Trên máy admin (đã grant scope admin):

1. Cài v1.0 (chạy lại installer hoặc đã có sẵn)
2. Trong Claude Code:

```
học mẫu D:\SoanThaoVB_\some-template.docx
```

→ AI gọi `vbhc_learn_template` → in report ND30.

```
lưu file vừa học thành template "test-deploy" (confirmed=true)
```

→ AI gọi `vbhc_update_template` → ghi `~/.vbhc/cache/templates/test-deploy.docx`.

```
publish template "test-deploy" lên cloud (confirmed=true)
```

→ AI gọi `vbhc_publish_template` → POST lên cloud → server archive (nếu có cũ) + rebuild manifest.

Verify trên VPS:

```bash
ls /var/lib/vbhc-kb/templates/test-deploy.docx   # mới
tail -3 /var/lib/vbhc-kb/audit.log               # publish_ok với kid=biencuong-laptop
```

---

## Rollback (nếu cần)

Trường hợp gặp lỗi nặng (không sửa được trong vài phút), rollback về v0.9:

### Rollback nginx

```bash
sudo cp /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf.bak-pre-v1.0 \
        /www/server/panel/vhost/nginx/mcp.hagiang.edu.vn.conf
sudo nginx -t && sudo nginx -s reload
```

### Rollback service

```bash
sudo systemctl stop vbhc-kb
sudo systemctl disable vbhc-kb
sudo mv /etc/systemd/system/vbhc-mcp.service.deprecated /etc/systemd/system/vbhc-mcp.service
sudo systemctl daemon-reload
sudo systemctl enable vbhc-mcp
sudo systemctl start vbhc-mcp
```

### Rollback code

```bash
cd /home/mcp-soan-thao-vbhc
git checkout v0.9.1   # hoặc commit SHA đã lưu ở Bước 0
```

### Rollback api-keys

```bash
sudo cp /root/.vbhc/org/api-keys.yaml.bak-pre-v1.0 /root/.vbhc/org/api-keys.yaml
sudo systemctl restart vbhc-mcp
```

Sau rollback, endpoint `/mcp` v0.9 hoạt động lại — user chưa migrate vẫn dùng được.

---

## Kiểm tra cuối — checklist

- [ ] `systemctl status vbhc-kb` → active (running)
- [ ] `systemctl status vbhc-mcp` → inactive
- [ ] `curl https://mcp.hagiang.edu.vn/healthz` → 200
- [ ] `curl -H "Bearer ..." https://mcp.hagiang.edu.vn/kb/manifest.json` → 200 + JSON
- [ ] `curl https://mcp.hagiang.edu.vn/install.ps1` → 200 + PowerShell content
- [ ] `curl https://mcp.hagiang.edu.vn/mcp` → 410 Gone (hoặc 404)
- [ ] 1-liner installer trên máy mới chạy 8/8 steps OK
- [ ] `vbhc_knowledge_status` trong Claude Code trả JSON đầy đủ
- [ ] (Admin) `vbhc_publish_template` POST OK + audit.log có entry

## Sau deploy — bước cuối

Gửi tin thông báo cho cán bộ:

> "MCP `vbhc` đã update lên v1.0. Endpoint cũ `mcp.hagiang.edu.vn/mcp` không còn hoạt động. Để dùng tiếp:
>
> 1. Mở PowerShell
> 2. Chạy: `claude mcp remove vbhc -s user`
> 3. Chạy: `iwr https://mcp.hagiang.edu.vn/install.ps1 | iex`
> 4. Nhập API key bạn đang có (cùng key cũ)
> 5. Đóng + mở lại Claude Code
>
> Hướng dẫn đầy đủ: https://github.com/biencuong/vbhc/blob/main/MIGRATION-v1.0.md"
