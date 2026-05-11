# MCP Server `vbhc`

MCP server cho skill `soan-thao-vbhc`. Cung cấp **13 tools** deterministic cho workflow soạn VBHC theo Nghị định 30/2020/NĐ-CP.

## Cài đặt

### 1. Cài Python deps

```bash
pip install mcp python-docx pyyaml openpyxl
```

Hoặc dùng uv:

```bash
uv pip install mcp python-docx pyyaml openpyxl
```

### 2. Kiểm tra server chạy được

```bash
python D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py
```

Server sẽ block chờ stdin (đó là behavior đúng của MCP server). `Ctrl+C` để dừng.

### 3. Đăng ký với client

#### Với Claude Code

```bash
claude mcp add vbhc -s user -- python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"
```

#### Với qwenpaw (hoặc client tương tự dùng cấu hình JSON)

Thêm vào file config (vd: `~/.qwenpaw/config.json` hoặc `~/.qwenpaw.json`):

```json
{
  "mcpServers": {
    "vbhc": {
      "command": "python",
      "args": ["D:\\SKILL_AI\\skills\\soan-thao-vbhc\\mcp\\server.py"]
    }
  }
}
```

### 4. (Tùy chọn) Bootstrap cloud Knowledge Hub (v1.0+)

Nếu cơ quan có cloud KB Hub (vd `https://mcp.hagiang.edu.vn`), chạy 1 lần để tải templates + rules về local cache:

```bash
python -m mcp.bootstrap --url https://mcp.hagiang.edu.vn --key vbhc_<your-key> --org so-gddt-tuyen-quang
```

Bootstrap ghi `~/.vbhc/config.yaml` + sync mọi asset về `~/.vbhc/cache/`. Sau đó server tự dùng cache (offline OK, auto-refresh khi stale).

### 5. Restart client

Sau khi cấu hình, restart Claude Code / qwenpaw để load MCP server.

Tools sẽ xuất hiện dưới prefix `mcp__vbhc__<tool_name>`.

## Tools (13)

### Phân loại & sắp xếp

#### `vbhc_classify(description)`
Phân loại VB từ mô tả tự nhiên của user. Trả về matches + ambiguous_forms khi mô tả chứa "góp ý" / "phúc đáp" (Báo cáo vs Công văn).

#### `vbhc_create_workfolder(description, parent_dir, custom_slug?)`
Tạo folder công việc chuẩn `<NNNN>-<slug>/` với `0-ky-thuat/`, `1-tham-chieu/`, `1-yeu-cau.md`, `2-du-lieu.yaml`.

#### `vbhc_reorganize(source_folder, custom_slug?, parent_dir?)`
Sắp xếp folder bừa thành chuẩn `<NNNN>-<mô-tả>/`.

#### `vbhc_regenerate_check(work_folder, update?)`
Detect file mới/thay đổi trong `1-tham-chieu/` qua `0-ky-thuat/file-manifest.yaml`. Dùng khi user nói "soạn lại VB".

### Fill & validate

#### `vbhc_fill_template(template_path, output_path, cell_ops?, paragraph_ops?, replace_ops?)`
Fill .docx template. Hỗ trợ cả 3 chiến lược: cell_ops (table), paragraph_ops (theo index), replace_ops (tìm-thay). `template_path` chấp nhận cả slug (vd `"bao-cao"`) — tự resolve qua cache → bundled → cloud-pull.

#### `vbhc_validate(docx_path)`
Chạy checklist 9 thành phần thể thức ND30. Tự nhận biểu mẫu nội bộ (phiếu biểu quyết) để skip check Số VB / Nơi nhận.

#### `vbhc_aggregate_survey(xlsx_path)`
Tổng hợp Excel Google Forms (stats + comments) để soạn báo cáo khảo sát.

### Cấu hình cơ quan

#### `vbhc_load_org_config(filename?)`
Đọc YAML từ ORG dir (`$VBHC_ORG_DIR` hoặc `~/.vbhc/org/`). Default file: `05-thong-tin-co-quan.yaml`.

#### `vbhc_suggest_noi_nhan(vb_purpose, vb_type, user_provided?)`
Gợi ý "Nơi nhận" từ phân công nhiệm vụ cơ quan. Sanitize bỏ "(...)" — ND30 không quy định ngoặc đơn.

### Học & cập nhật template (admin/per-user)

#### `vbhc_learn_template(file_path)`
Phân tích thể thức 1 file mẫu user đưa vào, so với ND30, trả về spec + report_md (human-readable).

#### `vbhc_update_template(source_file, target_loai_vb, confirmed?)`
Lưu 1 file đã duyệt làm template chuẩn vào **local cache** (`~/.vbhc/cache/templates/<slug>.docx`). Workflow 2 bước (confirmed=False preview → confirmed=True ghi). REFUSE nếu source FAIL bất kỳ check ND30.

Sau khi ghi cache, `vbhc_fill_template` dùng được ngay. Để chia sẻ cho máy khác: dùng `vbhc_publish_template` (Phase 4 — chưa release).

### Cloud sync (v1.0+)

#### `vbhc_sync_knowledge(force?, only?)`
Pull templates + rules + code bundle từ cloud KB Hub về `~/.vbhc/cache/`.

- `force=True`: pull cả khi cache còn fresh
- `only="manifest"|"templates"|"rules"|"code"`: chỉ pull 1 kind (default: tất cả)

Sau sync, các tool khác (vbhc_classify, vbhc_validate, ...) dùng version mới ở lần gọi tiếp theo (rules YAML cache được clear tự động).

Trả về `{ok, synced_at, results, errors, counts}`.

#### `vbhc_knowledge_status()`
Trả tóm tắt cache:
- `configured` — đã bootstrap chưa
- `cached_assets` — templates / rules có trong cache
- `local_manifest` — versions local
- `cloud_manifest` — versions cloud (nếu kết nối được)
- `drift` — assets cần sync (sha256 lệch)
- `last_sync` — summary lần sync trước

Dùng khi user hỏi "cache có gì", "có version mới không", hoặc debug khi tool không thấy template/rule.

## Cache layout (v1.0+)

```
~/.vbhc/
├── config.yaml                 ← cloud_url + api_key + org_id
└── cache/
    ├── manifest.json           ← bản sao manifest cloud
    ├── etag.json               ← ETag conditional GET
    ├── last_sync.json          ← summary lần sync gần nhất
    ├── templates/<slug>.docx
    ├── rules/<name>.yaml       ← the-thuc, typo-fixes, loai-vb
    └── code/scripts.tar.gz + version.txt
```

Override `VBHC_HOME` env var để dùng folder khác (test isolated).

## Troubleshooting

### "ImportError: No module named 'mcp'"
→ Chạy `pip install mcp`. Đảm bảo Python ≥ 3.10.

### "ImportError: No module named 'docx'"
→ `pip install python-docx` (KHÔNG phải `pip install docx`).

### "ImportError: No module named 'yaml'"
→ `pip install pyyaml`.

### Tools không xuất hiện sau khi cấu hình
→ Restart client. Kiểm tra log của client có lỗi spawn server không.

### `vbhc_sync_knowledge` báo "Chưa bootstrap"
→ Chạy `python -m mcp.bootstrap` (interactive) hoặc với `--url --key --org`.

### `vbhc_fill_template` với slug báo "file not found"
→ Slug chưa có trong cache. Chạy `vbhc_sync_knowledge` trước. Hoặc dùng full path `.docx` thay slug.

### Tracked changes không ghi tên thật
→ Server này dùng python-docx (không tracked changes). Nếu cần, dùng song song MCP `word-mcp-live` qua tool `mcp__word__word_live_*`.
