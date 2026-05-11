# soan-thao-vbhc — Skill + MCP soạn VBHC theo NĐ 30/2020

Skill tự động hóa việc soạn văn bản hành chính Việt Nam: phân loại loại VB, tổ chức hồ sơ, phỏng vấn lấy quan điểm/dữ liệu, fill template `.docx`, validate thể thức, gợi ý nơi nhận theo phân công nhiệm vụ.

## Kiến trúc v1.0

```
+-------------------+        Bearer key          +--------------------+
| Local thin-MCP    | <------- pull ------------ | Cloud KB Hub       |
| (stdio, mỗi máy)  |  templates+rules+code      | mcp.hagiang.edu.vn |
|                   |                             | /kb/* (port 8766)  |
| 14 tools          | -------- publish --------> |                    |
| ~/.vbhc/cache/    |  (admin only)              | /var/lib/vbhc-kb/  |
+-------------------+                             +--------------------+
        |
        v
   File user ở LOCAL (D:\..., không upload server)
```

- **File user ở local** — server không thấy
- **Knowledge** (templates ND30, rules, code) đồng bộ từ cloud về `~/.vbhc/cache/`
- **Cán bộ onboard bằng 1 lệnh PowerShell** (xem [INSTALL-LOCAL.md](INSTALL-LOCAL.md))
- **Admin publish** template mới qua `vbhc_publish_template` → mọi máy khác sync nhận

## Tài liệu

| File | Mục đích |
|---|---|
| **[INSTALL-LOCAL.md](INSTALL-LOCAL.md)** | **★ Hướng dẫn cài cho cán bộ Windows** (1-liner PowerShell) |
| **[MIGRATION-v1.0.md](MIGRATION-v1.0.md)** | Đang dùng v0.9 cloud HTTP? Chuyển sang v1.0 |
| [INSTALL-AAPANEL.md](INSTALL-AAPANEL.md) | Triển khai cloud KB Hub trên VPS Ubuntu + aaPanel (admin) |
| [SKILL.md](SKILL.md) | Workflow + nguyên tắc + anti-pattern (AI đọc khi soạn) |
| [mcp/README.md](mcp/README.md) | Tham chiếu 14 MCP tools |
| [doc/HANDOFF-v1.0-WIP.md](doc/HANDOFF-v1.0-WIP.md) | State refactor v1.0 (5 phase, deliverables, quirks) |
| [cloud/README.md](cloud/README.md) | Cloud KB Hub deploy + admin |
| [tri-thuc-template/README.md](tri-thuc-template/README.md) | Cách sửa YAML ORG dir cho cơ quan |

## Tính năng chính

| Pha | Hành vi |
|---|---|
| 1. Phân loại | 27+ loại VBHC chuẩn NĐ 30 + biểu mẫu nội bộ + ambiguous-form (báo cáo vs công văn cho VB phản hồi/góp ý) |
| 2. Tổ chức hồ sơ | Folder `<NNNN>-<slug>/` với cấu trúc `0-ky-thuat/` + `1-tham-chieu/` + sản phẩm root |
| 3. Phỏng vấn | 4 nhóm bắt buộc: Mục đích · Người ký · Nơi gửi · Quan điểm |
| 4. Yêu cầu nguồn | Trigger "theo NĐ X" → đòi file gốc; verify hiệu lực; tổng hợp Excel khảo sát |
| 5. Fill / Generate | python-docx + `vbhc_doc_builder` (header chuẩn ND 30: gạch chân, font, spacing) |
| 6. Validate | Checklist 9 thành phần thể thức; auto-detect biểu mẫu nội bộ |
| 7. Học + cập nhật | `vbhc_learn_template` + `vbhc_update_template` ghi cache local; admin publish lên cloud |

## 14 MCP tools

```
# Phân loại + sắp xếp
vbhc_classify(description)              Phân loại VB + detect dạng mơ hồ
vbhc_create_workfolder(...)             Tạo folder chuẩn 0-ky-thuat/1-tham-chieu/
vbhc_reorganize(source_folder)          Sắp xếp folder bừa
vbhc_regenerate_check(work_folder)      Detect file mới trong 1-tham-chieu/

# Fill + validate
vbhc_fill_template(template, ops...)    Fill .docx (cell/paragraph/replace); template = slug or path
vbhc_validate(docx_path)                Checklist 9 thành phần thể thức
vbhc_aggregate_survey(xlsx_path)        Tổng hợp Excel Google Forms

# Cấu hình cơ quan
vbhc_load_org_config(filename)          Đọc YAML từ ORG tier
vbhc_suggest_noi_nhan(purpose, ...)     Gợi ý nơi nhận theo phân công NV

# Học + cập nhật template
vbhc_learn_template(file_path)          Phân tích thể thức 1 file mẫu user
vbhc_update_template(source, slug)      Ghi template vào ~/.vbhc/cache/

# Cloud sync (v1.0+)
vbhc_sync_knowledge(force, only)        Pull templates+rules+code từ cloud KB Hub
vbhc_knowledge_status()                 Tóm tắt cache + drift vs cloud
vbhc_publish_template(slug, confirmed)  Admin push template lên cloud (cần scope admin)
```

## Cấu trúc thư mục

```
soan-thao-vbhc/
├── INSTALL-LOCAL.md            # ★ Cài cho cán bộ (PowerShell 1-liner)
├── MIGRATION-v1.0.md           # ★ Chuyển từ v0.9 sang v1.0
├── INSTALL-AAPANEL.md          # Deploy cloud KB Hub trên VPS
├── SKILL.md                    # Entry workflow + anti-pattern
├── README.md                   # File này
├── resources/                  # workflow + checklist + danh mục 27+ loại VB
├── tri-thuc-template/          # ORG dir template cho cơ quan
│   ├── 05-thong-tin-co-quan.yaml
│   ├── phan-cong-nhiem-vu.yaml
│   ├── can-cu-phap-ly-mau.yaml
│   └── rules/                  # Phase 1.5 — data-driven rules
│       ├── the-thuc.yaml
│       ├── typo-fixes.yaml
│       └── loai-vb.yaml
├── scripts/                    # CLI Python — fill, validate, classify, etc.
│   ├── rules_loader.py         # YAML loader cache→bundled
│   └── manage_keys.py          # CLI quản lý API keys (scope read/admin)
├── mcp/                        # Local thin-MCP server
│   ├── server.py               # stdio, 14 tools
│   ├── auth.py                 # APIKeyMiddleware (dùng cho cloud KB Hub)
│   ├── bootstrap.py            # First-run wizard ghi ~/.vbhc/config.yaml
│   └── knowledge_client.py     # HTTP client pull/publish KB
├── cloud/                      # Knowledge Hub HTTP server (VPS)
│   ├── kb_server.py            # Starlette serve /kb/* + /install.ps1
│   ├── build_manifest.py       # Sinh manifest.json (sha256 + version)
│   ├── install.ps1             # Installer 1-liner (UTF-8 BOM)
│   └── uninstall.ps1           # Gỡ
└── doc/
    ├── HANDOFF-v1.0-WIP.md     # State refactor v1.0
    └── PLAN-v1.0.md            # Plan đã duyệt
```

## Cài nhanh

### Cá nhân, Claude Code, Windows (1 lệnh)

```powershell
iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
```

Chi tiết: [INSTALL-LOCAL.md](INSTALL-LOCAL.md).

### Đang dùng v0.9 (HTTP MCP)?

Chuyển sang v1.0: [MIGRATION-v1.0.md](MIGRATION-v1.0.md). Quan trọng — endpoint `mcp.hagiang.edu.vn/mcp` (v0.9) **đã bị gỡ** khi VPS update v1.0.

### Triển khai cloud KB Hub (admin)

VPS Ubuntu + aaPanel:

```bash
cd /home && git clone https://github.com/biencuong/vbhc.git mcp-soan-thao-vbhc
bash mcp-soan-thao-vbhc/deploy/install-server.sh
# Sau đó: build_manifest --import-from-repo, install vbhc-kb.service, nginx /kb + /install.ps1
```

Chi tiết: [INSTALL-AAPANEL.md](INSTALL-AAPANEL.md) + [cloud/README.md](cloud/README.md).

## Nguyên tắc kỹ thuật quan trọng

### Tại sao có cả Skill VÀ MCP?

- **Skill** = hướng dẫn AI cách hành xử qua hội thoại (workflow, câu hỏi, anti-pattern). AI đọc + tự thực thi.
- **MCP tools** = các thao tác deterministic, không phụ thuộc khả năng LLM. Đặc biệt cho:
  - `vbhc_fill_template` — không thể tin AI fill .docx đúng cell mỗi lần
  - `vbhc_validate` — checklist khách quan, không bias
  - `vbhc_doc_builder` — generate header chuẩn NĐ 30 với XML chính xác

### Data-driven rules (v1.0+)

Rules ND30 + classifier + typo fixes ở `tri-thuc-template/rules/*.yaml` — sửa YAML không cần đổi code. Loader: `scripts/rules_loader.py` (cache → bundled fallback).

### Workaround đặc thù

`mcp__word__search_and_replace` thường fail trên text trong cell sau khi convert `.doc` → split runs. Tool `vbhc_fill_template` xử lý bằng edit runs trực tiếp.

### Tracked changes

Server `vbhc` dùng python-docx → KHÔNG support tracked changes. Cần tracked changes (sửa file user đang mở) → dùng kèm `word-mcp-live` (Windows-only, COM-based).

## License

MIT
