# Migrate từ v0.9 cloud MCP → v1.0 local thin-MCP

> **Bắt buộc**: Sau khi VPS deploy v1.0, endpoint cũ `https://mcp.hagiang.edu.vn/mcp` **sẽ không còn**. Mọi client v0.9 phải chuyển sang kiến trúc mới.

## Vì sao đổi?

v0.9 (cloud MCP HTTP) có hai vấn đề:

1. **Server không truy cập được file `D:\...` của user** — workaround dùng UNC path không thực tế cho cán bộ hành chính.
2. **File user bị upload lên server** — risk privacy + băng thông.

v1.0 (local thin-MCP + cloud Knowledge Hub):

- **File user ở local** (không upload server)
- **Templates + thể thức ND30 + rules + code** đồng bộ từ cloud về `~/.vbhc/cache/`
- Cán bộ onboard bằng **1 lệnh PowerShell**
- Tự liền sẹo (auto-pull asset thiếu)

## Tóm tắt thay đổi

| Khía cạnh | v0.9 (cũ) | v1.0 (mới) |
|---|---|---|
| Endpoint | `https://mcp.hagiang.edu.vn/mcp` | `python <local>\mcp\server.py` (stdio) |
| Transport | HTTP streamable | stdio (mỗi máy 1 process) |
| Auth | Bearer header trong client config | API key chỉ dùng để pull knowledge (cloud KB Hub) |
| File user | Server đụng file qua share | Local — server không thấy |
| Cloud serve | Tất cả tools | Chỉ templates + rules + code (read), publish template (admin) |
| Cài đặt | `claude mcp add vbhc -s user -- url + Bearer` | `iwr .../install.ps1 \| iex` |

## Migrate (3 bước, ~5 phút)

### Bước 1 — Backup (an toàn)

Folder công việc của bạn (nếu có) thường ở `D:\SoanThaoVB_\cong-viec\` hoặc tương tự. **Không bị ảnh hưởng** bởi migration — v1.0 không đụng tới. Nhưng nên backup phòng tai nạn:

```powershell
# Tùy chọn — copy folder work sang chỗ an toàn
Copy-Item -Recurse "D:\SoanThaoVB_\cong-viec" "D:\SoanThaoVB_\cong-viec-backup-v0.9"
```

### Bước 2 — Gỡ MCP `vbhc` cũ (HTTP)

```powershell
claude mcp remove vbhc -s user
```

Verify đã gỡ:

```powershell
claude mcp list
# Không còn dòng "vbhc: https://mcp.hagiang.edu.vn/mcp"
```

### Bước 3 — Cài v1.0 bằng 1 lệnh

```powershell
iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
```

Khi prompt:
- **Cloud URL**: Enter (mặc định `https://mcp.hagiang.edu.vn`)
- **API key**: API key cơ quan cấp (cùng key bạn dùng cho v0.9 — hoặc xin admin cấp mới nếu hết hạn)
- **Org ID**: `so-gddt-tuyen-quang` (hoặc bỏ trống nếu cá nhân)

Sau khi xong:
1. **Đóng + mở lại Claude Code**
2. Verify trong chat: gõ "phân loại văn bản: báo cáo quý I" → Claude gọi `vbhc_classify` → trả về **Báo cáo**

Chi tiết installer xem `INSTALL-LOCAL.md`.

## Kiểm tra sau migrate

| Check | Cách verify |
|---|---|
| MCP `vbhc` đăng ký local | `claude mcp list` → thấy `vbhc: ...\venv\Scripts\python.exe ...` |
| Cache đồng bộ | Trong chat: "gọi vbhc_knowledge_status" → JSON có `configured: true`, `cached_assets.templates` ≥ 3, `drift` rỗng |
| Tool fill chạy local | Soạn 1 VB mới → file output ghi trên máy bạn, không phải qua server |
| Cập nhật knowledge | "gọi vbhc_sync_knowledge" → pull manifest + assets từ cloud về cache |

## API key — vẫn dùng?

**Có**, nhưng vai trò đổi:

- **v0.9**: Bearer key dùng để **MCP HTTP transport** (server xác thực client)
- **v1.0**: Bearer key dùng để **pull knowledge từ cloud KB Hub** (port 8766) — tải templates + rules + code về cache local

Cùng `api-keys.yaml`, **cùng key có thể tái sử dụng**. Nếu thiếu, liên hệ admin cơ quan.

## Quản trị cơ quan (admin)

Nếu bạn là admin (quản lý keys + push template):

### Thêm scope `admin` cho 1 key

Trên VPS (SSH):

```bash
cd /home/mcp-soan-thao-vbhc
./venv/bin/python scripts/manage_keys.py grant <admin-id> admin
systemctl restart vbhc-kb
```

### Publish template từ máy admin

Sau khi đã `vbhc_update_template("ten-loai-vb", confirmed=True)` (ghi vào cache local):

```
trong chat: gọi vbhc_publish_template với slug "ten-loai-vb" và confirmed=true
```

Tool sẽ POST file lên `https://mcp.hagiang.edu.vn/kb/templates/<slug>.docx`. Server archive version cũ, rebuild manifest. Máy user khác chạy `vbhc_sync_knowledge` sẽ thấy version mới.

## Troubleshooting

### "Connection refused" sau khi đã cài v1.0

→ Claude Code chưa restart. Đóng + mở lại Claude Code.

### `vbhc_sync_knowledge` báo 401

→ API key sai hoặc đã bị revoke. Verify `~/.vbhc/config.yaml` có đúng key, hoặc xin admin cấp lại.

### Vẫn thấy entry `vbhc` cũ HTTP

→ `claude mcp remove vbhc -s user` rồi cài lại bằng `iwr .../install.ps1 | iex`. Installer sẽ overwrite.

### Folder `cong-viec/` không còn truy cập được qua MCP

→ Đúng — v1.0 chạy local trên máy bạn, không qua server nữa. Trực tiếp dùng tool MCP từ Claude Code là OK.

## Rollback (nếu cần)

Nếu v1.0 không hoạt động và cần tạm thời quay lại v0.9 (sẽ bị disabled khi VPS deploy xong):

```powershell
# Gỡ v1.0
iwr https://mcp.hagiang.edu.vn/uninstall.ps1 | iex

# Cài lại entry v0.9 HTTP (manual)
claude mcp add vbhc -s user -t http --header "Authorization: Bearer vbhc_<key>" -- https://mcp.hagiang.edu.vn/mcp
```

**Lưu ý**: Sau khi VPS deploy v1.0, endpoint `/mcp` không còn — rollback chỉ có ý nghĩa **trước khi** VPS chuyển. Khuyến nghị: migrate ngay khi nhận được thông báo.

## Liên hệ hỗ trợ

- Repo: https://github.com/biencuong/vbhc
- Doc kỹ thuật: `doc/HANDOFF-v1.0-WIP.md` trong repo
- Issue / yêu cầu: tạo issue tại GitHub
