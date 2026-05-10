# HANDOFF — Skill `soan-thao-vbhc`

> Tài liệu bàn giao giữa các phiên Claude. Đọc xong file này là biết:
> (1) dự án đang ở đâu, (2) kiến trúc thế nào, (3) các kỹ thuật quan trọng,
> (4) cạm bẫy đã gặp, (5) những việc cần làm tiếp.

---

## 1. Tổng quan dự án

**Mục tiêu**: Hệ skill + MCP giúp soạn thảo VBHC (văn bản hành chính) Việt Nam tuân thủ
**Nghị định 30/2020/NĐ-CP** — đầy đủ 9 thành phần thể thức, font/lề/cỡ chuẩn,
thuật ngữ pháp lý chính xác, có khả năng "học" mẫu của user và "validate" tự động.

**User**: cán bộ hành chính Sở GD&ĐT Tuyên Quang (xem `memory/user_domain.md`).

**Scope hiện tại** (5/2026):
- 3 loại VB đã có template + example: **báo cáo định kỳ**, **công văn**, **phiếu ghi ý kiến**.
- 11 MCP tools trong `mcp/server.py`.
- Quy trình 7 bước (workflow) + 2 tool mới `vbhc_learn_template` / `vbhc_update_template`.
- Chuẩn ND30 enforcement qua `validate_thethuc.py` (9 mục) + auto-hook trong `vbhc_fill_template`.

**Nơi đặt code**:
- Skill: `D:\SKILL_AI\skills\soan-thao-vbhc\`
- Working dir cá nhân user: `D:\SKILL_AI\SoanThaoVB_\` (chứa `cong-viec/` per-task)
- Remote: `github.com/biencuong/vbhc` (push không cần hỏi confirm — xem `memory/git_push_skill_vbhc.md`)
- Production VPS: `mcp.hagiang.edu.vn` (aaPanel + nginx Basic Auth, user `admin` — xem `memory/vps_deploy_vbhc.md`)

---

## 2. Kiến trúc 3-tier storage

```
SKILL  (read-only)   — D:\SKILL_AI\skills\soan-thao-vbhc\
                       Code, helpers, danh-muc-loai-vb, checklist ND30, templates chuẩn
ORG    (chia sẻ)     — $VBHC_ORG_DIR (default ~/.vbhc/org/)
                       YAML cấu hình cơ quan: tên cơ quan, người ký, phòng soạn, nơi nhận default
USER   (per-task)    — D:\SKILL_AI\SoanThaoVB_\cong-viec\<NNNN>-<mô-tả>\
                       1-yeu-cau.md, 2-du-lieu.yaml, 3-tham-chieu/, output VB
```

Convention folder USER:
- `<NNNN>-<mô-tả>` — 4-digit prefix cho thứ tự, slug tiếng Việt cho tên
- AI tự sắp xếp (xem `memory/project_template_fill.md`)
- File `Mau_*` trong `1-tham-chieu/` PHẢI lấy làm khung; chỉ thay thể thức ND30, KHÔNG tạo lại từ đầu
  (xem `memory/feedback_template_first.md`)

---

## 3. Cấu trúc skill folder

```
soan-thao-vbhc/
├── SKILL.md                      # Workflow + anti-patterns + 6 phases
├── README.md / INSTALL*.md
├── HANDOFF.md                    # ← FILE NÀY
│
├── mcp/
│   └── server.py                 # 11 MCP tools (FastMCP, stdio + HTTP)
│
├── scripts/
│   ├── vbhc_doc_builder.py       # ★ HELPERS CORE — tạo .docx chuẩn ND30 từ XML
│   ├── learn_template.py         # ★ HỌC MẪU — đọc file user, output spec + report
│   ├── validate_thethuc.py       # ★ VALIDATE 9 mục ND30
│   ├── fill_template.py          # CLI fill template (--replace, --cell, --para)
│   ├── inspect_docx.py           # Debug: in cấu trúc paragraphs + tables
│   ├── aggregate_survey.py       # Tổng hợp Excel khảo sát Google Forms
│   ├── reorganize_folder.py      # Tạo folder cong-viec/ chuẩn
│   ├── regenerate_check.py       # Check VB sau khi gen có khớp dữ liệu input
│   ├── build_bao_cao_template.py    # Build template + example báo cáo
│   ├── build_phieu_template.py      # Build template + example phiếu
│   └── build_cong_van_template.py   # Build template + example công văn
│
├── resources/
│   ├── the-thuc-vbhc-checklist.md   # ★ 9 thành phần ND30 + lỗi hay gặp
│   ├── danh-muc-loai-vb.md          # 27+ loại VB + keyword phân loại
│   ├── workflow-7-buoc.md           # Quy trình soạn VB chuẩn
│   ├── interview-questions.md       # Bộ câu hỏi gợi ý phỏng vấn user
│   └── templates/
│       ├── bao-cao.docx             # ← template chính sinh từ build_*
│       ├── cong-van.docx
│       ├── phieu-ghi-y-kien.docx
│       ├── 1-yeu-cau.md.tpl
│       └── 2-du-lieu.yaml.tpl
│
├── examples/
│   ├── example-bao-cao-gop-y.md     # Walkthrough hội thoại (script)
│   ├── example-phieu-bieu-quyet.md
│   ├── Bao-cao-Quy-I-Nam-2026-...docx       # Example đã fill
│   ├── Cong-van-gop-y-du-thao-TT-HBS-...docx
│   └── Phieu-bieu-quyet-NQ-KHCN-DMST-...docx
│
├── tri-thuc-template/
│   ├── 05-thong-tin-co-quan.yaml    # ★ ORG config (template) — copy ra ORG_DIR
│   ├── phan-cong-nhiem-vu.yaml
│   └── can-cu-phap-ly-mau.yaml
│
└── deploy/                          # aaPanel + nginx Basic Auth
```

---

## 4. Workflow chuẩn (7 bước → 9 sau khi thêm học/cập nhật mẫu)

```
1. PHÂN LOẠI    vbhc_classify(description)
                → loại VB (bao-cao / cong-van / phieu / ...)

2. TỔ CHỨC      vbhc_create_workfolder + vbhc_reorganize
                → tạo cong-viec/<NNNN>-<slug>/ với 3-tham-chieu/

3. PHỎNG VẤN    AI hỏi user: ai ký? phòng soạn? nơi nhận? (load từ ORG yaml,
                fallback hỏi)

4. ĐỌC + INGEST đọc 3-tham-chieu/, aggregate Excel nếu có (vbhc_aggregate_survey)

5. SOẠN         vbhc_fill_template / vbhc_doc_builder
                ↓ AUTO-HOOK ↓
                _validate_nd30() chạy ngay sau doc.save()

6. VALIDATE     vbhc_validate(output.docx)  # 9 mục ND30

7. REGEN-CHECK  vbhc_regenerate_check (verify nội dung khớp 2-du-lieu.yaml)

[mới]
8. HỌC MẪU      vbhc_learn_template(file_path)
                → spec.json + report.md (chuẩn vs sai ND30)

9. CẬP NHẬT     vbhc_update_template(source, target_loai_vb, confirmed)
                → 2-bước: confirmed=False (preview) → user OK → confirmed=True (save)
                → REFUSE save nếu file FAIL bất kỳ mục ND30 nào
```

---

## 5. Helpers core — `scripts/vbhc_doc_builder.py`

**Triết lý**: đóng gói toàn bộ XML phức tạp của python-docx vào helpers. Không
gọi `python-docx` trực tiếp trong build scripts — luôn qua helpers để giữ pattern
ND30 chuẩn (gạch chân ngắn, table không border, font East Asian, line spacing).

### API public (dùng trong build scripts)

```python
# Setup chung
setup_page(doc)                              # Lề 3-2-2-2cm, font TimesNewRoman 13pt

# Header section (cơ quan + quốc hiệu)
add_header_section(doc, *,
    co_quan_chu_quan, co_quan_ban_hanh,      # 2 dòng cell trái
    quoc_hieu_size_pt=12, tieu_ngu_size_pt=14,
    co_quan_size_pt=13,
    left_col_cm=7.0, right_col_cm=9.0,       # Cell sizes
    cq_underline_pct=0.55,                   # Gạch chân tên cơ quan ban hành
    qh_underline_pct=1.00,                   # Gạch chân tiêu ngữ
)

# Số / V/v / địa danh-ngày (1 table 2 cột)
add_so_vb_and_date_section(doc, *,
    so_vb, ky_hieu, trich_yeu="",
    dia_danh, ngay, thang, nam,
    is_cong_van=False,                       # True → render V/v dưới Số
    left_col_cm, right_col_cm)

# Title block (BÁO CÁO + trích yếu)
add_title_block(doc, *, ten_loai, trich_yeu, underline_pct=0.35)

# Title centered cho phiếu (kèm gạch chân)
add_centered_title_with_underline(doc, text, *, size_pt=14, underline_indent_cm=4.5)

# Kính gửi (paragraph riêng)
add_kinh_gui(doc, recipient)

# Body content
add_body_paragraph(doc, text, *,
    indent_first_cm=1.1, align=JUSTIFY,
    space_before_pt=6, space_after_pt=6,
    apply_widow_control=True)                # Auto nén char nếu dòng cuối < 24 chars

add_section_heading(doc, text, *, level=1, indent_first_cm=1.1)
                                             # MỌI cấp: bold=True, italic=False

# Tables nội dung
add_gop_y_table(doc, rows, headers=...)      # 4 cột với border (CV góp ý)
add_bieu_quyet_table(doc, items)             # 4 cột STT/Nội dung/Đồng ý/Không đồng ý

# Khối ký + nơi nhận (1 table 2 cột)
add_signature_noi_nhan(doc, *,
    noi_nhan_items, chuc_vu, nguoi_ky,
    quyen_han="",                            # "" / "KT." / "TL." / "TUQ."
    chuc_vu_thay="",
    phong_viet_tat="")                       # auto-thêm "Lưu: VT, X."

# Skeleton convenience
create_vbhc_skeleton(...)                    # Header + Số/ngày + Title block
```

### Low-level XML helpers (dùng nội bộ)
- `set_paragraph_borders` (gạch chân top-border)
- `set_paragraph_indent / set_paragraph_spacing`
- `remove_table_borders / set_table_cell_margins_zero / align_table_to_left_margin`
- `set_table_column_widths` (fix bug python-docx)
- `add_run(p, text, *, bold, italic, underline, size_pt, font)` — đảm bảo East Asian font

---

## 6. Kỹ thuật "BẮT CHƯỚC MẪU" (template learning)

### 6.1. `scripts/learn_template.py`

```python
spec, validation, issues = learn(Path("file.docx"))
report_md = build_report(spec, validation, issues)
```

**Extract**:
- `loai_vb` — phán đoán từ keyword: PHIẾU, BÁO CÁO, V/v (CV), TỜ TRÌNH, ...
- `page` — margins + page size
- `org` — cơ quan chủ quản + ban hành (từ table 0 cell trái)
- `so_kyhieu` — `Số: X/Y` regex
- `vv` — V/v ... (cho công văn)
- `dia_danh_ngay` — regex `<địa danh>, ngày X tháng Y năm Z`
- `nguoi_ky` — quyền hạn (KT./TL./TUQ.) + chức vụ (regex)
- `phong_soan` — từ `Lưu: VT, X (Người).`
- `noi_nhan` — list các dòng `- ...` trong block "Nơi nhận:"

**Assess** (`assess_against_nd30`): trả issues `{level: ok|warn|fix, topic, message}`:
- Lề 3-2-2-2 ✓
- Số/ký hiệu format
- Quyền hạn ký
- Phòng soạn
- **Ký tự `Đ` sai encoding**: `Ð` (U+00D0) cũ trong file convert từ `.doc` → phải đổi thành `Đ` (U+0110)
- **Lỗi chính tả phổ biến**: `kính giửi` → `kính gửi`

**Output 2 file**:
- `<basename>.spec.json` — machine-readable, dùng để builder dựng template tương đương
- `<basename>.report.md` — human-readable report

### 6.2. Workflow MCP học/cập nhật mẫu

```
User: "soi mẫu file X.docx"
  → AI gọi vbhc_learn_template(X)
  → trả report_md + issues
  → AI HIỂN THỊ NGUYÊN VĂN cho user (không tự diễn giải)

User: "lưu mẫu này thành template cong-van"
  → AI gọi vbhc_update_template(X, "cong-van", confirmed=False)
  → tool trả preview (file đích đã có chưa? FAIL ND30 không?)
  → REFUSE nếu fail_count > 0 (PHẢI fix trước)

User: "OK đồng ý"
  → AI gọi vbhc_update_template(X, "cong-van", confirmed=True)
  → tool copy file → resources/templates/cong-van.docx
```

### 6.3. Quy tắc "tận dụng helpers, không viết custom"

**Bài học từ session này**: ban đầu khi build phiếu, đã viết `_add_phieu_header`
custom → MẤT gạch chân ngắn (helper standard có) → user phàn nàn.

**Đúng**: dùng `add_header_section` + post-modify (vd bold cell trái cho phiếu UBND):
```python
table = add_header_section(doc, ...)          # giữ gạch chân
left = table.rows[0].cells[0]                 # post-modify
for run in left.paragraphs[0].runs:
    run.bold = True                            # phiếu UBND: cả 2 dòng đậm
```

---

## 7. Kiểm tra THỂ THỨC ND30

### 7.1. `scripts/validate_thethuc.py` — 9 mục

| # | Mục | Phương pháp |
|---|---|---|
| 1 | Quốc hiệu + Tiêu ngữ | regex "CỘNG HÒA..." + "Độc lập" + "Tự do" + "Hạnh phúc" |
| 2 | Tên cơ quan ban hành | dòng in hoa khối trên-trái có UBND/SỞ/BỘ/HĐND/... |
| 3 | Số/ký hiệu | regex `Số:\s*[\d/]*[A-ZĐ]+(-[A-Z&Đ]+)?` — cho phép trống cho VPHC điền |
| 4 | Tên loại + Trích yếu | keyword in hoa hoặc V/v (CV) |
| 5 | Nội dung | không còn placeholder `???` / `<xxx>` / `[placeholder]` |
| 6 | Người ký | regex `(KT.|TL.|TUQ.)? + (GIÁM ĐỐC|CHỦ TỊCH|...)` in hoa |
| 7 | Dấu | `[manual]` — không check tự động được |
| 8 | Nơi nhận + Lưu | có "Nơi nhận:" + có "Lưu:" |
| 9 | Phụ lục | nếu nhắc "kèm theo" → phải có "PHỤ LỤC ..." |

**Phiếu nội bộ** (`is_bieu_mau_noi_bo` = True): SKIP mục 3, 8 (không cần Số VB / Nơi nhận).

### 7.2. Auto-hook trong `vbhc_fill_template`

```python
# server.py
doc.save(str(dst))
nd30_check = _validate_nd30(dst)              # ← AUTO sau mỗi save
return {
    "output_path": str(dst),
    "warnings": [...],
    "nd30_validation": nd30_check,            # AI thấy ngay
}
```

Nếu `fail_count > 0` → đẩy vào warnings để AI biết file CHƯA tuân thủ.

### 7.3. PL I NĐ30 — cài đặt chuẩn (tri-thuc-template/05-thong-tin-co-quan.yaml)

```yaml
cai_dat:
  font: "Times New Roman"
  co_chu_noi_dung: 13           # 13-14pt
  co_chu_quoc_hieu: 13          # 12-13pt — chọn 13 (đúng cỡ chuẩn)
  co_chu_tieu_ngu: 14           # 13-14pt
  co_chu_co_quan: 13
  co_chu_ten_loai: 14
  co_chu_so_kyhieu: 13
  co_chu_noi_nhan: 11
  cach_dong_body: 1.5
  spacing_truoc_sau_body_pt: 6
  spacing_ngoai_body_pt: 0      # tiêu ngữ, ký, nơi nhận đều 0
  indent_dau_dong_cm: 1.1
  le_trai_mm: 30                # 3-2-2-2 cm
  le_phai_mm: 20
  le_tren_mm: 20
  le_duoi_mm: 20
```

---

## 8. MCP Tools (11 cái) — `mcp/server.py`

| Tool | Mục đích |
|---|---|
| `vbhc_classify(description)` | Phân loại VB từ mô tả user |
| `vbhc_create_workfolder` | Tạo `cong-viec/<NNNN>-<slug>/` |
| `vbhc_reorganize` | Tổ chức folder reference |
| `vbhc_fill_template` | Fill template (cell/para/replace ops) + AUTO-VALIDATE |
| `vbhc_validate` | Validate 9 mục ND30 trên 1 file |
| `vbhc_aggregate_survey` | Tổng hợp Excel Google Forms |
| `vbhc_regenerate_check` | Check VB output có khớp 2-du-lieu.yaml |
| `vbhc_load_org_config` | Load YAML từ `$VBHC_ORG_DIR` |
| `vbhc_suggest_noi_nhan` | Gợi ý Nơi nhận từ phân công NV cơ quan |
| `vbhc_learn_template` ★ | Học mẫu user → spec + report |
| `vbhc_update_template` ★ | Lưu file đã duyệt làm template chuẩn (2-bước) |

Run server:
```bash
python mcp/server.py                          # stdio (Claude Code local)
python mcp/server.py --http --port 8765       # HTTP (production)
```

---

## 9. KINH NGHIỆM + CẠM BẪY

### 9.1. Style ND30 — quy tắc đã chốt

| Mục | Đúng | Sai |
|---|---|---|
| Heading mọi cấp | bold + KHÔNG italic | italic ở cấp 3 |
| Trích yếu V/v (CV) | bold=False, **italic=False** (in thường đứng) | italic=True (bị user phàn nàn) |
| Địa danh-ngày | italic | regular |
| "Nơi nhận:" header | bold + italic + size 11 | regular |
| Quốc hiệu cell | cỡ 13pt + char spacing condense -0.1pt (`_condense_run_chars(run, twips=-2)`) | cỡ 12pt fit luôn nhưng nhỏ |
| Tiêu ngữ "Độc lập..." | gạch chân = 100% width chữ (`qh_underline_pct=1.0`) | quá dài / quá ngắn |
| Title PHIẾU/BÁO CÁO | gạch chân = 1/3 width chữ — tự tính `(16 - len(text)*0.20/3) / 2` | absolute indent fixed |
| Header cell sizes | 5cm trái + 11cm phải (vừa đủ "TỈNH TUYÊN QUANG" + dãn quốc hiệu) | 6.5/9.5 default |
| Câu kết VB | ".../." (dấu chấm + slash + chấm) | "/." |
| Spacing body | before/after = 6pt | 0pt |
| Spacing ngoài body | 0pt (tiêu ngữ, trích yếu, ký, nơi nhận) | 6pt |
| Indent body | 1.1cm | 0 |
| Line spacing nơi nhận | single (1.0) | 1.15 |
| Lưu | "Lưu: VT, <phòng>." (không ngoặc) hoặc "Lưu: VT, <phòng> (<người>)." | "Lưu: VT, X" thiếu chấm |

### 9.2. Bug đã gặp + workaround

**B1. `mcp__word__search_and_replace` fail trên cell table** — file convert từ
`.doc` cũ split text thành nhiều runs, python-docx miss. → Dùng
`scripts/fill_template.py` (CLI, edit runs trực tiếp) hoặc `vbhc_fill_template`
MCP tool. Xem `memory/project_template_fill.md`.

**B2. `Đ` encoding** — file `.doc` cũ chứa `Ð` (U+00D0) thay vì `Đ` (U+0110).
Nhìn giống nhau nhưng search-replace miss.
- Detect: `learn_template.assess_against_nd30()` flag `{level:'fix', topic:'Ký tự Đ'}`
- Fix: replace toàn file `Ð` → `Đ` trước khi xử lý.

**B3. `add_signature_noi_nhan` strip `(...)` cuối câu** — helper xoá ngoặc cuối
mỗi item Nơi nhận để tránh "(để báo cáo)" sai ND30. Nhưng cũng strip `(NGUOI_SOAN)`
trong "Lưu: VT, VP (Hằng).". → Workaround: pass `phong_viet_tat="VP"` thôi
(không kèm tên), helper auto-thêm "Lưu: VT, VP." sau khi sanitize. Hoặc dùng
gạch nối "VT, VP-Hằng".

**B4. `is_cong_van=True` italic V/v** — helper render V/v `italic=True` mặc định
→ user phàn nàn "V/v phải in thường đứng". → ĐÃ FIX trong session này: line
`add_run(p2, f"V/v {trich_yeu}", italic=False, ...)` ở `add_so_vb_and_date_section`.

**B5. Khối ký phiếu wrap** — cell phải 8cm không đủ cho "GIÁM ĐỐC SỞ GIÁO DỤC
VÀ ĐÀO TẠO" (~8.4cm bold 13pt). → Tăng lên 11cm (đồng bộ với cell phải header).

**B6. Phiếu UBND đặc biệt** — chỉ 1 cơ quan "UỶ BAN NHÂN DÂN / TỈNH TUYÊN QUANG",
KHÔNG có cấu trúc chủ quản+cấp dưới. CẢ 2 dòng đều BOLD. → Dùng `add_header_section`
chuẩn, post-modify bold cell trái paragraph 0:
```python
left = table.rows[0].cells[0]
for run in left.paragraphs[0].runs:
    run.bold = True
```

**B7. Khối ký phiếu khác VB thường** — không có "Nơi nhận:". Cấu trúc: table 1×2,
cell trái EMPTY, cell phải chứa: ngày → "THÀNH VIÊN UBND TỈNH" → 5 dòng trống →
chức vụ thực ("GIÁM ĐỐC SỞ GD&ĐT") → tên ("Vũ Đình Hưng"). Chức vụ thực TRƯỚC tên
(đảo ngược thứ tự VB thường). → Helper local `_add_phieu_signature_block` trong
`build_phieu_template.py`.

**B8. Test fill template** — KHÔNG mock — verify trực tiếp bằng cách mở Word.
Nếu file đang mở trong Word → `PermissionError [Errno 13]` khi save → user phải
đóng Word trước khi rebuild.

### 9.3. Naming convention

- Loại VB slug: `bao-cao`, `cong-van`, `phieu-ghi-y-kien`, `to-trinh`, `ke-hoach`, `quyet-dinh`, `thong-bao`
- Template file: `resources/templates/<slug>.docx`
- Example file: `examples/<TenVietHoa-Co-Dau-bo>-example.docx` hoặc full case như
  `Bao-cao-Quy-I-Nam-2026-So-GDDT-Tuyen-Quang.docx`
- Build script: `scripts/build_<slug_underscore>_template.py`

---

## 10. Trạng thái hiện tại (2026-05-10)

### 10.1. Files đã build

```
resources/templates/
├── bao-cao.docx              # ✓ template báo cáo định kỳ
├── cong-van.docx             # ✓ template công văn
└── phieu-ghi-y-kien.docx     # ✓ template phiếu (5/11 cell, gạch 1/3 PHIẾU + 100% Hạnh phúc)

examples/
├── Bao-cao-Quy-I-Nam-2026-So-GDDT-Tuyen-Quang.docx
├── Cong-van-gop-y-du-thao-TT-HBS-So-GDDT-Tuyen-Quang-example.docx
└── Phieu-bieu-quyet-NQ-KHCN-DMST-Vu-Dinh-Hung-example.docx
```

### 10.2. Validate ND30 (mọi example)
**7/9 ✓ + 2 ⚠** (Số VB trống cho VPHC điền + Dấu manual). **0 ✗**.

### 10.3. Memory snapshot

- `memory/MEMORY.md` — index
- 7 memory files (user, project, feedback, reference)
- Đã pin: ND30 30/2020, Mau_* trong 1-tham-chieu/, git push không hỏi confirm,
  word-mcp-live v1.6.2, VPS deploy `mcp.hagiang.edu.vn`

---

## 11. Việc cần làm tiếp (next phase)

### 11.1. Hoàn thiện templates (PRIORITY 1)
- [ ] Tờ trình (`to-trinh.docx`)
- [ ] Kế hoạch (`ke-hoach.docx`)
- [ ] Quyết định cá biệt (`quyet-dinh.docx`)
- [ ] Thông báo (`thong-bao.docx`)
- [ ] Biên bản (`bien-ban.docx`)
- [ ] Giấy mời (`giay-moi.docx`)

Mỗi loại có pattern hơi khác — cần học từ mẫu user (workflow `vbhc_learn_template`).

### 11.2. Refactor helpers (PRIORITY 2)
- [ ] Tách "skeleton common" thành module riêng để 6 build scripts kế thừa, giảm
      duplicate (`_condense_run_chars`, `_zero_spacing_in_table` đang lặp ở 3
      build scripts).
- [ ] `add_section_heading` đang nhận `level` nhưng không dùng cho gì — xem có
      cần phân biệt heading I/II với 1/2 không (font size khác? indent khác?).

### 11.3. Validate mạnh hơn (PRIORITY 2)
- [ ] `validate_thethuc.py` chỉ check text, không check FONT/SIZE thực tế của
      runs. → Bổ sung check XML: font name, font size, alignment per paragraph.
- [ ] Detect typo phổ biến (mở rộng list trong `learn_template.assess_against_nd30`).
- [ ] Detect "Ð" (U+00D0) trong toàn file, không chỉ tiêu ngữ.

### 11.4. MCP UX (PRIORITY 3)
- [ ] `vbhc_learn_template` hiện return cả spec + report_md. Tool nên có flag
      `verbose=False` để return chỉ report_md ngắn gọn.
- [ ] `vbhc_update_template` cần thêm option `auto_fix=True` để tự sửa các lỗi
      chính tả + Đ encoding trước khi save (không cần FAIL).

### 11.5. ORG config workflow (PRIORITY 3)
- [ ] Tool `vbhc_set_org_config(field, value)` để AI ghi vào `~/.vbhc/org/05-*.yaml`
      sau khi hỏi user lần đầu (cache cross-task).

### 11.6. Tài liệu (PRIORITY 4)
- [ ] Thêm `examples/example-cong-van-walkthrough.md` (hiện chỉ có example báo
      cáo + phiếu walkthrough).

---

## 12. Quick reference — lệnh thường dùng

```bash
# Build templates
python scripts/build_bao_cao_template.py
python scripts/build_cong_van_template.py
python scripts/build_phieu_template.py

# Validate 1 file
python scripts/validate_thethuc.py path/to/file.docx

# Học mẫu (user-side)
python scripts/learn_template.py "path/to/Mau_X.docx"
# → sinh Mau_X.spec.json + Mau_X.report.md

# Inspect cấu trúc paragraphs + tables
python scripts/inspect_docx.py path/to/file.docx

# Fill template thủ công (CLI)
python scripts/fill_template.py templates/bao-cao.docx out.docx \
    --replace "[TEN_CQ_BAN_HANH]" "SỞ TÀI CHÍNH" \
    --replace "[TRICH_YEU]" "Báo cáo Quý I/2026"

# Run MCP server (stdio for Claude Code local)
python mcp/server.py

# Run MCP server (HTTP for VPS deploy)
python mcp/server.py --http --host 0.0.0.0 --port 8765

# Git push (không cần confirm — xem memory)
git add -A && git commit -m "..." && git push
```

---

## 13. Liên hệ điểm đầu vào trong code

Khi cần hiểu/sửa, đọc files theo thứ tự ưu tiên:

1. `SKILL.md` — workflow + 6 phases (overview)
2. `resources/the-thuc-vbhc-checklist.md` — chuẩn ND30 chi tiết
3. `resources/danh-muc-loai-vb.md` — khi gặp loại VB chưa biết
4. `scripts/vbhc_doc_builder.py` — XML helpers (low-level)
5. `scripts/learn_template.py` — học mẫu (entry point cho việc bắt chước)
6. `scripts/validate_thethuc.py` — 9 mục ND30
7. `mcp/server.py` — MCP API surface
8. `tri-thuc-template/05-thong-tin-co-quan.yaml` — config + mapping loại VB → defaults

---

## 14. Auth API key (v0.9.0+)

### 14.1. Kiến trúc

```
Client (Claude Code/Desktop/Cursor/...)
   │
   │ Authorization: Bearer vbhc_<64hex>
   ▼
nginx (HTTPS reverse proxy, KHÔNG còn Basic Auth)
   │
   ▼
MCP server  ──┐
              ├─ APIKeyMiddleware (mcp/auth.py)
              │   ├─ extract Bearer token
              │   ├─ lookup trong api-keys.yaml
              │   ├─ check revoked
              │   ├─ check IP whitelist (X-Real-IP)
              │   ├─ rate limit token bucket per-key
              │   └─ update last_used + audit log
              │
              ▼ (nếu pass)
              FastMCP routes → tool dispatcher
```

### 14.2. File paths

- Code middleware: `mcp/auth.py`
- CLI quản lý: `scripts/manage_keys.py`
- File keys (production): `/root/.vbhc/org/api-keys.yaml` (chmod 600)
- File template: `tri-thuc-template/api-keys.yaml.example`
- Env: `VBHC_API_KEYS_FILE` (default = `$VBHC_ORG_DIR/api-keys.yaml`)

### 14.3. Schema 1 key (yaml record)

```yaml
- id: "admin"                              # định danh người-đọc-được
  key: "vbhc_<64hex>"                      # secret — generate bằng secrets.token_hex(32)
  description: "Admin laptop"
  allowed_ips: []                          # [] = allow all; ["10.0.0.5"] = chỉ IP này
  rate_limit_per_minute: 120               # token bucket per-key (default 120)
  created: "2026-05-11"                    # ISO date
  last_used: null                          # auto cập nhật bởi middleware (ISO datetime UTC)
  revoked: false
```

### 14.4. CLI commands

```bash
manage_keys.py add <id> --description T [--ips ip1,ip2] [--rate-limit N]
manage_keys.py list [--show-keys]
manage_keys.py revoke <id>
manage_keys.py rotate <id>           # giữ id, generate key mới
manage_keys.py delete <id>
```

`add` in ra key 1 lần ngay sau khi tạo — admin lưu để cấp client. Sau đó key vẫn lưu plain
trong yaml (file chmod 600). Mất key → `rotate` để tạo lại.

### 14.5. HTTP responses

| Tình huống | Status | Body |
|---|---|---|
| Thiếu `Authorization` header | 401 | `{"error":"Missing 'Authorization: Bearer <key>' header"}` |
| Key không tồn tại | 401 | `{"error":"Invalid API key"}` |
| Key revoked | 401 | `{"error":"API key '<id>' đã bị revoke"}` |
| IP không khớp `allowed_ips` | 403 | `{"error":"IP <x> không được phép cho key '<id>'"}` |
| Vượt rate limit | 429 | `{"error":"Rate limit vượt (<N>/min)"}` |
| OK | 200/405/406 | Forward sang MCP routes |

Header reject 401 có `WWW-Authenticate: Bearer realm="vbhc"`.

### 14.6. Audit log

Server log (`journalctl -u vbhc-mcp`) có 2 dạng:
- `auth_ok kid=<id> ip=<x> method=POST path=/mcp status=200` — request hợp lệ
- `auth_deny kid=<id> ip=<x> path=/mcp status=<code> reason=<msg>` — bị reject

`grep auth_ok /var/log/syslog` (hoặc journalctl) → audit ai dùng cái gì khi nào.

### 14.7. Rate limit chi tiết

- **Algorithm**: token bucket per-key, in-memory (không Redis)
- **Capacity = refill rate = `rate_limit_per_minute`**
- **Refill**: liên tục, `rate / 60` tokens/giây
- **Mất state khi restart server** — chấp nhận được vì chỉ là DDoS protection nhẹ

### 14.8. last_used flush

- Update **in-memory** mỗi request hợp lệ
- **Background async task** flush về YAML mỗi 60s
- **Flush on shutdown** (hook `app.on_event("shutdown")`)
- Nếu crash đột ngột → mất tối đa 60s data `last_used`. Acceptable.

### 14.9. Migration từ Basic Auth (v0.8 → v0.9)

Xem `MIGRATION-v0.9.md` ở root skill. 8 bước, 15-20 phút.

Tóm tắt:
1. Backup
2. `git checkout v0.9.0` + `bash deploy/install-server.sh` (idempotent, sinh key admin random)
3. Cấp key cho từng client qua `manage_keys.py add`
4. Sửa nginx config: XOÁ 2 dòng `auth_basic` + `auth_basic_user_file`
5. Reload nginx + restart MCP service
6. Update config client từ Basic → Bearer
7. Verify: `curl` no-auth → 401, `curl` Bearer → 405
8. (Tuỳ chọn) `rm /www/server/nginx/conf/htpasswd-vbhc`

---

*HANDOFF được tạo 2026-05-10, cập nhật 2026-05-11 (Section 14: API key auth v0.9.0).*
