# soan-thao-vbhc — Skill + MCP soạn VBHC theo NĐ 30/2020

Skill tự động hóa việc soạn văn bản hành chính Việt Nam: phân loại loại VB, tổ chức hồ sơ, phỏng vấn lấy quan điểm/dữ liệu, fill template `.docx`, validate thể thức, gợi ý nơi nhận theo phân công nhiệm vụ.

## Tài liệu

| File | Mục đích |
|---|---|
| **[INSTALL.md](INSTALL.md)** | Hướng dẫn cài đặt tổng quát, 3 scenarios (cá nhân / phòng-Sở / dev) |
| **[INSTALL-AAPANEL.md](INSTALL-AAPANEL.md)** | **★ Hướng dẫn A→Z cho VPS Ubuntu + aaPanel** (cụ thể, verbose, cho người mới) |
| [SKILL.md](SKILL.md) | Workflow 6 pha, nguyên tắc, anti-pattern (AI đọc khi soạn) |
| [SETUP-FOR-AGENTS.md](SETUP-FOR-AGENTS.md) | Quick reference cấu hình từng agent (Cursor, Cline, Continue...) |
| [tri-thuc-template/README.md](tri-thuc-template/README.md) | Cách sửa YAML trong ORG dir cho cơ quan của bạn |

## Tính năng chính

| Pha | Hành vi |
|---|---|
| 1. Phân loại | 27+ loại VBHC chuẩn NĐ 30 + biểu mẫu nội bộ + ambiguous-form (báo cáo vs công văn cho VB phản hồi/góp ý) |
| 2. Tổ chức hồ sơ | Folder `<NNNN>-<slug>/` với cấu trúc `0-ky-thuat/` + `1-tham-chieu/` + sản phẩm root |
| 3. Phỏng vấn | 4 nhóm bắt buộc: Mục đích · Người ký · Nơi gửi · Quan điểm |
| 4. Yêu cầu nguồn | Trigger "theo NĐ X" → đòi file gốc; verify hiệu lực; tổng hợp Excel khảo sát |
| 5. Fill / Generate | python-docx + `vbhc_doc_builder` (header chuẩn ND 30: gạch chân, font, spacing) |
| 6. Validate | Checklist 9 thành phần thể thức; auto-detect biểu mẫu nội bộ |

## Kiến trúc 3 tier

```
SKILL (code, read-only)  ──►  ORG (config cơ quan)  ──►  USER (file công việc)
D:\SKILL_AI\skills\...        ~/.vbhc/org/               cong-viec/<NNNN>-...
```

Chi tiết trong [INSTALL.md](INSTALL.md).

## 9 MCP tools

```
vbhc_classify(description)              Phân loại VB + detect dạng mơ hồ
vbhc_create_workfolder(...)             Tạo folder chuẩn 0-ky-thuat/1-tham-chieu/
vbhc_reorganize(source_folder)          Sắp xếp folder bừa
vbhc_fill_template(template, ops...)    Fill .docx (cell/paragraph/replace)
vbhc_validate(docx_path)                Checklist 9 thành phần thể thức
vbhc_aggregate_survey(xlsx_path)        Tổng hợp Excel Google Forms
vbhc_regenerate_check(work_folder)      Detect file mới trong 1-tham-chieu/
vbhc_load_org_config(filename)          Đọc YAML từ ORG tier
vbhc_suggest_noi_nhan(purpose, ...)     Gợi ý nơi nhận theo phân công NV
```

## Cấu trúc thư mục

```
soan-thao-vbhc/
├── INSTALL.md                  # ★ Hướng dẫn cài đặt + triển khai
├── SKILL.md                    # Entry workflow + anti-pattern
├── README.md                   # File này
├── SETUP-FOR-AGENTS.md         # Quick reference per-agent
├── resources/
│   ├── workflow-7-buoc.md
│   ├── interview-questions.md
│   ├── danh-muc-loai-vb.md     # 27+ loại VBHC
│   ├── the-thuc-vbhc-checklist.md
│   └── templates/              # 1-yeu-cau.md.tpl, 2-du-lieu.yaml.tpl
├── tri-thuc-template/          # ★ Template ORG dir cho cơ quan mới
│   ├── README.md
│   ├── 05-thong-tin-co-quan.yaml
│   ├── phan-cong-nhiem-vu.yaml
│   └── can-cu-phap-ly-mau.yaml
├── scripts/
│   ├── vbhc_doc_builder.py     # Module chính tạo .docx chuẩn NĐ 30
│   ├── reorganize_folder.py
│   ├── fill_template.py
│   ├── inspect_docx.py
│   ├── validate_thethuc.py
│   ├── aggregate_survey.py
│   ├── regenerate_check.py
│   └── _common.py
└── mcp/
    └── server.py               # FastMCP server (stdio + HTTP transport)
```

## Cài nhanh

### VPS Ubuntu + aaPanel (1 lệnh)

```bash
cd /home && \
git clone https://github.com/biencuong/vbhc.git mcp-soan-thao-vbhc && \
bash mcp-soan-thao-vbhc/deploy/install-server.sh
```

Script tự cài deps, tạo venv, ORG dir, systemd service, start + verify. Sau đó setup site + SSL + reverse proxy + auth trên aaPanel — xem **[INSTALL-AAPANEL.md](INSTALL-AAPANEL.md)**.

### Cá nhân, 1 máy, Claude Code (Windows)

```bash
# 1. Clone + deps
git clone https://github.com/biencuong/vbhc.git D:\SKILL_AI\skills\soan-thao-vbhc
pip install mcp python-docx openpyxl pyyaml

# 2. ORG dir + template
mkdir %USERPROFILE%\.vbhc\org
copy "D:\SKILL_AI\skills\soan-thao-vbhc\tri-thuc-template\*.yaml" "%USERPROFILE%\.vbhc\org\"
# → sửa các file YAML trong %USERPROFILE%\.vbhc\org\ cho cơ quan của bạn

# 3. Đăng ký MCP
claude mcp add vbhc -s user -- python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"

# 4. Restart Claude Code → test
```

Đầy đủ chi tiết: xem **[INSTALL.md](INSTALL.md)**.

## Nguyên tắc kỹ thuật quan trọng

### Tại sao có cả Skill VÀ MCP?

- **Skill** = hướng dẫn AI cách hành xử qua hội thoại (workflow, câu hỏi, anti-pattern). AI đọc + tự thực thi.
- **MCP tools** = các thao tác deterministic, không phụ thuộc khả năng LLM. Đặc biệt cho:
  - `vbhc_fill_template` — không thể tin AI fill .docx đúng cell mỗi lần
  - `vbhc_validate` — checklist khách quan, không bias
  - `vbhc_doc_builder` — generate header chuẩn NĐ 30 với XML chính xác (gạch chân, padding, line spacing)

### Workaround đặc thù

`mcp__word__search_and_replace` thường **fail** trên text trong **cell của table** sau khi file convert từ `.doc` → text bị split runs. Tool `vbhc_fill_template` xử lý bằng cách edit runs trực tiếp.

### Tracked changes

Server `vbhc` dùng python-docx → KHÔNG support tracked changes. Cần tracked changes (sửa file user đang mở) → dùng kèm `word-mcp-live` (Windows-only, COM-based).

## License

MIT
