# Cài đặt vbhc (local thin-MCP) — Cho cán bộ

Hướng dẫn cài đặt MCP `vbhc` chạy **local** trên máy Windows của cán bộ. File soạn thảo **không rời máy bạn**; cấu hình + mẫu (templates, thể thức ND30) tự đồng bộ từ máy chủ cơ quan.

## Trước khi cài

Cần có:

1. **Windows 10 trở lên**
2. **Python 3.10 trở lên** — kiểm tra bằng cách mở PowerShell và gõ:
   ```powershell
   python --version
   ```
   Nếu không có hoặc < 3.10:
   - Tải tại https://www.python.org/downloads/ (chọn **Add python.exe to PATH** khi cài)
   - Hoặc dùng: `winget install Python.Python.3.12`
3. **Kết nối Internet** (để tải code lần đầu + đồng bộ knowledge sau này)
4. **API key Bearer** do quản trị cơ quan cấp (định dạng `vbhc_xxxxxxxx...`, 64 ký tự sau prefix)
5. (Tùy chọn) **Git** — nếu có sẽ dùng `git clone`, không có sẽ tự tải zip

## Cài bằng 1 lệnh

Mở **PowerShell** (không cần quyền Admin) và dán:

```powershell
iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
```

Trình cài sẽ:

1. Kiểm tra Python (báo lỗi rõ ràng nếu thiếu)
2. Tạo thư mục cài tại `%LOCALAPPDATA%\vbhc\` (vd: `C:\Users\<tên>\AppData\Local\vbhc\`)
3. Tải code repo
4. Tạo môi trường Python riêng (venv) + cài dependencies
5. **Hỏi 3 thông tin:**
   - Cloud URL (mặc định `https://mcp.hagiang.edu.vn`, Enter để dùng)
   - **API key** (nhập key cơ quan cấp cho bạn)
   - Org ID (vd `so-gddt-tuyen-quang`, có thể bỏ trống)
6. Tải bộ knowledge (3 template + 3 rules + code) về cache local
7. Đăng ký MCP `vbhc` với Claude Code (nếu có)
8. In trạng thái cache để bạn xác nhận

Sau khi xong: **đóng + mở lại Claude Code** để Claude nhận MCP mới.

## Cài với tham số (cho admin / IT triển khai hàng loạt)

```powershell
& ([scriptblock]::Create((iwr https://mcp.hagiang.edu.vn/install.ps1).Content)) `
    -CloudUrl https://mcp.hagiang.edu.vn `
    -ApiKey vbhc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx `
    -OrgId so-gddt-tuyen-quang `
    -NonInteractive
```

Tham số khác:

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `-InstallDir` | `%LOCALAPPDATA%\vbhc` | Thư mục cài |
| `-RepoUrl` | `https://github.com/biencuong/vbhc.git` | Nguồn code |
| `-Branch` | `main` | Nhánh git |
| `-McpName` | `vbhc` | Tên MCP đăng ký với Claude Code |
| `-SkipMcpRegister` | (no) | Bỏ qua đăng ký Claude Code (cài thủ công) |
| `-NonInteractive` | (no) | Không prompt — yêu cầu -ApiKey |

## Xác nhận cài thành công

Bước smoke test cuối in JSON tổng kết. Nếu thấy:

```json
"configured": true,
"cached_assets": {
  "templates": ["bao-cao.docx", "cong-van.docx", ...],
  "rules": ["loai-vb.yaml", "the-thuc.yaml", "typo-fixes.yaml"]
},
"drift": { "templates": [], "rules": [], "code": null }
```

→ Cài OK. `drift` rỗng = cache khớp version cloud.

Trong Claude Code, sau khi restart, gõ thử:

```
phân loại văn bản: báo cáo tổng kết quý I/2026
```

Claude sẽ gọi tool `vbhc_classify` → trả về **Báo cáo** kèm slug.

## Cập nhật knowledge từ cloud

Sau khi cài, mỗi lần admin cơ quan cập nhật mẫu/quy tắc, bạn chạy trong chat:

```
gọi vbhc_sync_knowledge
```

(Hoặc: đóng/mở Claude Code, sync tự động khi tool đụng template stale.)

## Troubleshooting

### "Không tìm thấy Python >= 3.10"

→ Cài Python từ python.org, **nhớ tick "Add python.exe to PATH"**. Mở lại PowerShell, gõ `python --version` để xác nhận. Chạy lại installer.

### "git clone thất bại" / lỗi mạng

→ Kiểm tra:
- Có Internet không?
- Có chặn `github.com` qua firewall/proxy cơ quan không? Nếu có, liên hệ IT mở route hoặc dùng tham số `-RepoUrl` chỉ tới mirror nội bộ.
- Installer sẽ tự fallback sang tải zip nếu không có `git` — không cần lo nếu chỉ thiếu git.

### "Bootstrap thất bại" — Bearer token lỗi

Thường là:
- **401 Unauthorized**: API key sai hoặc đã bị revoke. Yêu cầu admin cấp key mới.
- **403 Forbidden**: IP máy không trong whitelist (nếu key có `allowed_ips`). Báo IP máy cho admin.
- **429 Too Many Requests**: vượt rate limit. Đợi 60s rồi thử lại.

### "claude mcp add báo lỗi"

→ Có thể bạn dùng Claude Desktop (không có `claude` CLI). Khi đó cần đăng ký thủ công: trình cài sẽ in đoạn JSON, copy vào `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vbhc": {
      "command": "C:\\Users\\<tên>\\AppData\\Local\\vbhc\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\<tên>\\AppData\\Local\\vbhc\\repo\\mcp\\server.py"]
    }
  }
}
```

Sau đó restart Claude Desktop.

### Cài lại từ đầu

Chạy 1-liner installer lần nữa — idempotent (sẽ update code + giữ config + cache).

## Gỡ cài đặt

```powershell
iwr https://mcp.hagiang.edu.vn/uninstall.ps1 | iex
```

Mặc định:
- Gỡ entry MCP `vbhc` khỏi Claude Code
- Xoá `%LOCALAPPDATA%\vbhc\` (code + venv)
- **Giữ** `~/.vbhc/` (config + cache) — để cài lại nhanh, không cần xin key lại

Để xoá luôn config + cache:

```powershell
& ([scriptblock]::Create((iwr https://mcp.hagiang.edu.vn/uninstall.ps1).Content)) -PurgeAll -NonInteractive
```

## Vị trí file sau khi cài

```
C:\Users\<tên>\
├── .vbhc\
│   ├── config.yaml             ← URL + API key + Org ID (chmod 600)
│   └── cache\
│       ├── manifest.json
│       ├── templates\<slug>.docx
│       ├── rules\<name>.yaml
│       └── code\
└── AppData\Local\vbhc\
    ├── repo\                   ← code (auto pull khi cài lại)
    └── venv\                   ← Python virtualenv
```

`~/.vbhc/` là **dữ liệu cá nhân của bạn** — đừng commit lên git hay chia sẻ.

## Liên hệ

- Repo: https://github.com/biencuong/vbhc
- Doc kỹ thuật chi tiết: `doc/HANDOFF-v1.0-WIP.md` trong repo
- Lỗi hoặc đề xuất: tạo issue tại GitHub
