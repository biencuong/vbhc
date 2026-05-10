# MCP Server `vbhc`

MCP server cho skill `soan-thao-vbhc`. Cung cấp 5 tools deterministic cho workflow soạn VBHC.

## Cài đặt

### 1. Cài Python deps

```bash
pip install mcp python-docx
```

Hoặc dùng uv:

```bash
uv pip install mcp python-docx
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

### 4. Restart client

Sau khi cấu hình, restart Claude Code / qwenpaw để load MCP server.

Tools sẽ xuất hiện dưới prefix:
- `mcp__vbhc__vbhc_classify`
- `mcp__vbhc__vbhc_create_workfolder`
- `mcp__vbhc__vbhc_reorganize`
- `mcp__vbhc__vbhc_fill_template`
- `mcp__vbhc__vbhc_validate`

## Tools

### `vbhc_classify(description)`
Phân loại VB từ mô tả tự nhiên của user.
- Input: `description: str`
- Output: `{matches, suggestion, need_clarification}`

### `vbhc_create_workfolder(description, parent_dir, custom_slug?)`
Tạo folder công việc chuẩn `<NNNN>-<slug>/` với 1-yeu-cau.md + 2-du-lieu.yaml + 3-tham-chieu/.

### `vbhc_reorganize(source_folder, custom_slug?, parent_dir?)`
Sắp xếp folder bừa thành chuẩn.

### `vbhc_fill_template(template_path, output_path, cell_ops?, paragraph_ops?, replace_ops?)`
Fill .docx template. Hỗ trợ cả 3 chiến lược:
- `cell_ops`: edit ô cụ thể trong table
- `paragraph_ops`: edit paragraph theo index
- `replace_ops`: tìm-thay text (works trên cả paragraph và cell)

### `vbhc_validate(docx_path)`
Chạy checklist 9 thành phần thể thức. Tự nhận diện biểu mẫu nội bộ (phiếu biểu quyết) để skip check Số VB / Nơi nhận.

## Troubleshooting

### "ImportError: No module named 'mcp'"
→ Chạy `pip install mcp`. Đảm bảo Python ≥ 3.10.

### "ImportError: No module named 'docx'"
→ `pip install python-docx` (KHÔNG phải `pip install docx`).

### Tools không xuất hiện sau khi cấu hình
→ Restart client. Kiểm tra log của client có lỗi spawn server không.

### Tracked changes không ghi tên thật
→ Server này dùng python-docx (không tracked changes). Nếu cần tracked changes, dùng song song MCP `word-mcp-live` qua tool `mcp__word__word_live_*`.
