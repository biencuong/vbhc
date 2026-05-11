---
name: Skill soan-thao-vbhc + MCP vbhc
description: Skill + MCP server đã build tại D:\SKILL_AI\skills\soan-thao-vbhc\ — workflow 6 pha soạn VBHC end-to-end cho qwenpaw / Claude Code
type: project
originSessionId: d2678777-08f3-4e95-9a55-7c3501505901
---
## Vị trí
`D:\SKILL_AI\skills\soan-thao-vbhc\`

## Architecture (v4 — 2026-05-10): 3-tier storage + HTTP transport

### 3-tier storage
- **SKILL** = `D:\SKILL_AI\skills\soan-thao-vbhc\` (code + danh mục VB chuẩn, read-only)
- **ORG**   = `$VBHC_ORG_DIR` (default `~/.vbhc/org/`) — config chung cơ quan, gồm:
  - `05-thong-tin-co-quan.yaml` (cơ quan, người ký, phòng, viết tắt GDĐT)
  - `phan-cong-nhiem-vu.yaml` (mới) — danh sách đơn vị + chức năng → AI gợi ý nơi nhận
  - `can-cu-phap-ly-mau.yaml` (mới) — VB pháp lý mẫu + hiệu lực
- **USER**  = `cong-viec/<NNNN>-...` (per-call args) hoặc `$VBHC_USER_DIR`

Hiện tại Sở GDĐT Tuyên Quang ORG = `D:\SKILL_AI\SoanThaoVB_\tri-thuc\`. Templates ở `D:\SKILL_AI\skills\soan-thao-vbhc\tri-thuc-template\` để clone cho cơ quan khác.

### Transport modes
- **stdio** (default): `python server.py` — local mỗi máy
- **HTTP**: `python server.py --http --host 0.0.0.0 --port 8765` — cho team share
  - Client config: `{"mcpServers": {"vbhc": {"url": "http://host:8765/mcp"}}}`
  - **Test verified**: server start OK với streamable-http

### Tools mới (lên 9 total)
- `vbhc_load_org_config(filename)` — đọc YAML từ ORG dir, auto-parse, có hint khi thiếu file
- `vbhc_suggest_noi_nhan(vb_purpose, vb_type, user_provided?)` — gợi ý nơi nhận từ phân công NV; sanitize bỏ "(...)"; đề nghị user cung cấp file phân công NV nếu chưa có
- `vbhc_classify` được nâng cấp với `ambiguous_forms`: khi mô tả chứa "góp ý"/"phản hồi"/"phúc đáp"/"đề xuất" → trả về options dạng VB (Báo cáo / Công văn / Tờ trình) để AI hỏi user

### Rules format mới (2026-05-10)
- **Ngày VB**: `ngày     tháng MM năm YYYY` — bỏ trống ngày, điền tháng/năm hiện tại
- **Nơi nhận**: KHÔNG ngoặc đơn `(để báo cáo)`, `(để phối hợp)` — NĐ 30 không quy định
- **Bảng**: full content width 16cm sát lề trái-phải qua `align_table_to_left_margin()`
- **Viết tắt**: "Giáo dục và Đào tạo" = "GDĐT" (không "GD&ĐT")
- **VB phản hồi/góp ý**: AI PHẢI hỏi user dạng (Báo cáo/Công văn) dựa trên yêu cầu VB nguồn

## Cấu trúc (153KB, 17 file)
- `SKILL.md` — entry, workflow 6 pha, anti-pattern
- `README.md` — cài đặt + ví dụ
- `resources/` — workflow-7-buoc.md, interview-questions.md, danh-muc-loai-vb.md (27+ loại), the-thuc-vbhc-checklist.md, templates/
- `scripts/` — 4 CLI Python: reorganize_folder, fill_template, inspect_docx, validate_thethuc + `_common.py`
- `mcp/` — FastMCP server với 5 tools: classify, create_workfolder, reorganize, fill_template, validate
- `examples/` — example-phieu-bieu-quyet.md (hội thoại mẫu end-to-end)

## 6 MCP tools đã expose
- `mcp__vbhc__vbhc_classify(description)` — phân loại VB từ text
- `mcp__vbhc__vbhc_create_workfolder(description, parent_dir, custom_slug?)`
- `mcp__vbhc__vbhc_reorganize(source_folder, custom_slug?, parent_dir?)`
- `mcp__vbhc__vbhc_fill_template(template, output, cell_ops?, paragraph_ops?, replace_ops?)`
- `mcp__vbhc__vbhc_validate(docx_path)` — checklist 9 thành phần, tự nhận biểu mẫu nội bộ
- `mcp__vbhc__vbhc_aggregate_survey(xlsx_path)` — tổng hợp Excel Google Forms (stats + comments)

## Cài MCP cho client
```bash
# Claude Code:
claude mcp add vbhc -s user -- python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"

# qwenpaw / generic JSON config:
{
  "mcpServers": {
    "vbhc": {
      "command": "python",
      "args": ["D:\\SKILL_AI\\skills\\soan-thao-vbhc\\mcp\\server.py"]
    }
  }
}
```

## Test status (đã verify session 09/5/2026)
- `vbhc_classify` × 4 case (phiếu, công văn, tờ trình, không rõ) — đúng
- `vbhc_validate` trên `Phieu-bieu-quyet-NQ-KHCN-DMST-Vu-Dinh-Hung.docx` → 8 ok / 1 warn / 0 fail
- `vbhc_validate` trên `Bao-cao-gop-y-du-thao-TT-HBS-...docx` → 7 ok / 2 warn / 0 fail
- `vbhc_aggregate_survey` trên Excel 235 phản hồi học bạ số → đúng (3 demographics, 13 stats, 3 comments cols với 120/104/95 non-trivial)
- `fill_template.py` test cell + paragraph ops — đúng
- `reorganize_folder.py` chạy thật trên 2 folder (XinYKenTVUBNDT, Gop y du thao TT HBS) — đúng

## Loại VB skill đã cover (ngoài 27+ loại standard)
- Phiếu biểu quyết / Phiếu ghi ý kiến (biểu mẫu nội bộ, không số VB)
- Báo cáo góp ý dự thảo theo đề cương cứng + tổng hợp khảo sát Excel

## Doc-builder: chuẩn ND 30 đầy đủ (v3 — verified)
Module `scripts/vbhc_doc_builder.py` đã cập nhật lên v3 với 11 cải tiến:

**Chuẩn header (final tuning 2026-05-10):**
- Cell trái 7cm + cell phải 9cm (tổng 16cm = vùng nội dung A4 NĐ 30)
- Cell padding = 0 (set qua `tblCellMar`)
- **Gạch chân tên cơ quan = 55% width tên đơn vị** (`cq_underline_pct=0.55`) — tính theo TEXT WIDTH (`len * 0.27cm`)
- **Gạch chân tiêu ngữ = 100% width tiêu ngữ** (`qh_underline_pct=1.00`) — tính theo TEXT WIDTH (`len * 0.20cm`)
- **Stroke 0.5pt** (sz=4 tức 4/8 pt) — mảnh, đẹp
- **Gap text → gạch chân = 1.2pt** (`space_before_pt=1.2`) — sát text
- Quốc hiệu **12pt** (NĐ 30: 12-13pt)
- Tiêu ngữ **14pt** (NĐ 30: 13-14pt)
- Tên CQ **13pt** (regular cho chủ quản, bold cho ban hành)
- **Line spacing tên CQ + Quốc hiệu = single (1.0)** + before/after = 0pt

**Chuẩn body:**
- Justify (căn 2 đầu)
- Indent đầu dòng **1.1cm** chỉ cho body
- Spacing **before=after=6pt** chỉ cho body, các phần khác (header, title, sig, table) = 0
- Line spacing 1.5
- Auto compress char spacing -0.1pt khi có nguy cơ widow (1-2 từ mồ côi cuối khổ)

**Đề mục flush left** (KHÔNG indent), spacing 0 — different from body.

**Trích yếu:** spacing 0 + gạch chân ngắn dưới = 30-40% (`underline_pct=0.35`)

**Khối ký:**
- KT.GĐ/PGĐ: line spacing single, before/after = 0 (tight)
- Tham số `phong_viet_tat="GDPT"` → tự thêm `- Lưu: VT, GDPT.` cuối Nơi nhận

**Bảng auto-resize cột:**
- Iterative algorithm: clamp violators, redistribute
- min_width = 2.8cm, max = 6cm
- Header weight = chars × 1.8 (header không wrap)
- Total guaranteed = 16cm

**Column widths sticky** qua `set_table_column_widths` (set tblGrid + từng cell, không chỉ columns[i])
**Table no border** qua `remove_table_borders` (tblBorders all 'nil')

**Why:** python-docx default tạo header bị vỡ bố cục (Quốc hiệu wrap, không có gạch chân, column widths không sticky). User chỉ ra 2 file đã tạo bị vỡ visual dù text đúng.

**How to apply:**
- KHI tạo VB mới từ đầu: LUÔN import vbhc_doc_builder, dùng `add_header_section()`, `add_so_vb_and_date_section()`, `add_title_block()`, `add_signature_noi_nhan()`. KHÔNG tự build table 2x2 cho header bằng python-docx thủ công.
- LUÔN render PDF (`mcp__word__convert_to_pdf`) để verify layout sau khi gen — Word UI render khác PDF render.

## Files regenerated 2026-05-09 → updated 2026-05-10 với format v3
- `0002-phieu-bieu-quyet-nq-khcn-dmst/Phieu-bieu-quyet-NQ-KHCN-DMST-Vu-Dinh-Hung.docx` — Vũ Đình Hưng (GĐ Sở GD&ĐT)
- `0003-gop-y-du-thao-tt-hoc-ba-so/Bao-cao-gop-y-du-thao-TT-HBS-So-GDDT-Tuyen-Quang.docx` — Đinh Thế Hiệp (PGĐ, KT.GĐ)

## Folder convention (updated 2026-05-10)
```
cong-viec/<NNNN>-<mô-tả>/
├── 0-ky-thuat/        ← scripts, 1-yeu-cau.md, 2-du-lieu.yaml, file-manifest.yaml
├── 1-tham-chieu/      ← file nguồn user đưa vào (PDF, docx, xlsx)
└── <san-pham>.docx    ← file kết quả ở root
```

## Regenerate-check tool
`scripts/regenerate_check.py` + MCP `vbhc_regenerate_check`:
- Track files trong `1-tham-chieu/` qua `0-ky-thuat/file-manifest.yaml` (size + mtime)
- Khi user nói "soạn lại VB", AI gọi tool → biết có file mới hoặc file cũ thay đổi
- Đã verify: detect được file `2026.05.07_soGD_x_Gop y Du thao thong tu Hoc ba so_1.docx` mới user thêm vào folder 0003

## Config chung
File `tri-thuc/05-thong-tin-co-quan.yaml` giờ chứa:
- `co_quan` (chủ quản, ban hành, địa danh)
- `nguoi_ky` (list lãnh đạo + ký_dạng + chuc_vu_thay)
- `phong_soan_thao` (list phòng + viet_tat — cho dòng "Lưu: VT, X")
- `cai_dat` (font, size, line spacing, lề chuẩn ND 30)

AI HỎI user khi soạn VB (chọn ai ký + phòng nào soạn) — KHÔNG tự đoán.

## Why: 
Đóng gói lại workflow vừa làm (sắp xếp folder XinYKenTVUBNDT → 0002-... + fill phiếu biểu quyết) để qwenpaw tự chạy mỗi khi user yêu cầu soạn VB qua chat. End-to-end: phân loại → sắp xếp → phỏng vấn → soạn → validate.

## How to apply:
- Khi user kích hoạt qua qwenpaw / Claude Code → AI đọc SKILL.md + làm theo workflow 6 pha.
- Mỗi pha có quy tắc dừng-hỏi rõ ràng. Đặc biệt **không tự đặt quan điểm "Đồng ý"** trên phiếu biểu quyết.
- Khi cần update template VB mặc định → bổ sung file vào `resources/templates/`.
- Khi cần thêm loại VB → cập nhật `resources/danh-muc-loai-vb.md` + thêm rule trong `mcp/server.py::CLASSIFY_RULES`.
