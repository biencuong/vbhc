# VBHC Knowledge Hub (cloud/)

Thay vai trò của MCP HTTP cũ (`mcp/server.py --http`) — chỉ phục vụ **assets** (templates, rules, code bundle) cho local thin-MCP trên máy user.

**Triết lý:** cloud chỉ giữ "nguồn chân lý" cho các thứ chia sẻ trong tổ chức. File công việc của user **không bao giờ rời máy local**.

---

## Routes

| Method | Path | Auth | Mô tả |
|---|---|---|---|
| GET | `/healthz` | public | Health check |
| GET | `/install.ps1` | public | PowerShell installer (1-liner) |
| GET | `/kb/manifest.json` | Bearer | Version + URL của mọi asset |
| GET | `/kb/templates/<slug>.docx` | Bearer | Binary template (bao-cao, cong-van, ...) |
| GET | `/kb/rules/<name>.yaml` | Bearer | YAML rule (the-thuc, loai-vb, typo-fixes) |
| GET | `/kb/code/scripts.tar.gz` | Bearer | Bundle thư mục `scripts/` (cập nhật code helper) |
| GET | `/kb/code/version.txt` | Bearer | Code-runtime version string |
| GET | `/kb/org/<org_id>/<filename>` | Bearer | Cấu hình per-org |
| POST | `/kb/templates/<slug>.docx` | Bearer + admin | (Phase 4) admin upload template mới |

Auth = Bearer API key (reuse `mcp/auth.py` + `api-keys.yaml` hiện có).

---

## Layout `KB_DIR` (mặc định `/var/lib/vbhc-kb/`)

```
/var/lib/vbhc-kb/
├── manifest.json              # sinh bởi build_manifest.py
├── install.ps1                # PowerShell installer (copy từ cloud/install.ps1)
├── templates/
│   ├── bao-cao.docx
│   ├── cong-van.docx
│   └── phieu-ghi-y-kien.docx
├── rules/                     # (Phase 1.5)
│   ├── the-thuc.yaml
│   ├── loai-vb.yaml
│   └── typo-fixes.yaml
├── code/
│   ├── scripts.tar.gz         # bundle scripts/
│   └── version.txt            # "v1.0.0+abc1234"
└── org/                       # (Phase 4) per-org config
    └── so-gddt-tuyen-quang/
        ├── 05-thong-tin-co-quan.yaml
        ├── phan-cong-nhiem-vu.yaml
        └── can-cu-phap-ly-mau.yaml
```

---

## Deploy trên VPS

```bash
# 1. Sync code mới nhất từ git
cd /home/mcp-soan-thao-vbhc
git pull

# 2. Tạo KB_DIR và import assets từ repo
sudo mkdir -p /var/lib/vbhc-kb
sudo /home/mcp-soan-thao-vbhc/venv/bin/python \
    /home/mcp-soan-thao-vbhc/cloud/build_manifest.py \
    --kb-dir /var/lib/vbhc-kb \
    --import-from-repo /home/mcp-soan-thao-vbhc

# 3. Copy installer
sudo cp /home/mcp-soan-thao-vbhc/cloud/install.ps1 /var/lib/vbhc-kb/install.ps1

# 4. Cài systemd service
sudo cp /home/mcp-soan-thao-vbhc/cloud/vbhc-kb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vbhc-kb

# 5. Verify
sudo systemctl status vbhc-kb
curl http://127.0.0.1:8766/healthz
curl -H "Authorization: Bearer $KEY" http://127.0.0.1:8766/kb/manifest.json
```

---

## Nginx reverse proxy (aaPanel)

Thêm vào nginx config (`#PROXY-START/...#PROXY-END/`):

```nginx
location /kb {
    proxy_pass http://127.0.0.1:8766;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location = /install.ps1 {
    proxy_pass http://127.0.0.1:8766/install.ps1;
    proxy_set_header Host $host;
}

location = /healthz {
    proxy_pass http://127.0.0.1:8766/healthz;
}
```

Reload:
```bash
nginx -t && /etc/init.d/nginx reload
```

---

## Cập nhật assets sau khi push code mới

```bash
cd /home/mcp-soan-thao-vbhc && git pull
sudo /home/mcp-soan-thao-vbhc/venv/bin/python \
    /home/mcp-soan-thao-vbhc/cloud/build_manifest.py \
    --import-from-repo /home/mcp-soan-thao-vbhc
# Service không cần restart — đọc trực tiếp filesystem
```

---

## Test local (dev)

```powershell
# Trên Windows dev machine
$env:VBHC_KB_DIR = "$env:TEMP\vbhc-kb-test"
$env:VBHC_API_KEYS_FILE = "$env:TEMP\test-api-keys.yaml"

# Tạo api-keys file tạm
@"
keys:
  - id: "dev"
    key: "vbhc_devkey0000000000000000000000000000000000000000000000000000000"
    description: "Dev test"
    allowed_ips: []
    rate_limit_per_minute: 1000
    revoked: false
"@ | Set-Content $env:VBHC_API_KEYS_FILE

# Import assets từ repo
python cloud\build_manifest.py --import-from-repo .

# Run server
python cloud\kb_server.py --host 127.0.0.1 --port 8766
```

```bash
# Test trong terminal khác
curl http://127.0.0.1:8766/healthz
curl http://127.0.0.1:8766/kb/manifest.json    # → 401 (chưa auth)
curl -H "Authorization: Bearer vbhc_devkey0000000000000000000000000000000000000000000000000000000" \
    http://127.0.0.1:8766/kb/manifest.json     # → JSON
```
