# HANDOFF — Skill `soan-thao-vbhc` (pre-v1.0)

> **Lưu ý**: File này là handoff **pre-v1.0** (đầu 2026-05). Kiến trúc đã đổi
> ở v1.0 — đọc HANDOFF mới trước:
>
> **→ [doc/HANDOFF-v1.0-WIP.md](doc/HANDOFF-v1.0-WIP.md)** — bàn giao v1.0 (5 phase + deliverables + quirks + tasks tiếp)
>
> **→ [doc/PLAN-v1.0.md](doc/PLAN-v1.0.md)** — plan đầy đủ duyệt
>
> File này giữ làm tham chiếu cho phần kỹ thuật vẫn còn dùng (vbhc_doc_builder
> XML helpers, kỹ thuật học mẫu, workaround search_and_replace) — các thứ đó
> không đổi ở v1.0.

## Tổng quan v1.0 (state hiện tại)

**Mục tiêu**: Hệ skill + MCP soạn VBHC tuân thủ Nghị định 30/2020/NĐ-CP — 9 thành phần thể thức, font/lề/cỡ chuẩn, học mẫu, validate tự động.

**Architecture v1.0** (đã release):

```
LOCAL Thin-MCP (mỗi máy user)          CLOUD KB Hub (mcp.hagiang.edu.vn:8766)
- stdio transport                      - FastAPI/Starlette
- 14 tools                             - GET /kb/* (read, Bearer)
- ~/.vbhc/cache/ (templates+rules)  ←  - POST /kb/templates/* (admin scope)
- File user ở local                    - templates/rules/code/install.ps1
```

**Scope v1.0** (5/2026):
- 3 loại VB có template + example: báo cáo, công văn, phiếu ghi ý kiến
- 14 MCP tools (xem `mcp/README.md`)
- Rules ND30 data-driven (`tri-thuc-template/rules/*.yaml`)
- 1-liner PowerShell installer (`cloud/install.ps1`)
- Admin publish workflow (scope `admin` trong `api-keys.yaml`)

**Nơi đặt code**:
- Skill: `D:\SKILL_AI\skills\soan-thao-vbhc\`
- Working dir user: `D:\SoanThaoVB_\cong-viec\` (per-task)
- Remote: `github.com/biencuong/vbhc` (push auto — xem `doc/memory/git_push_skill_vbhc.md`)
- Production VPS: `mcp.hagiang.edu.vn` (aaPanel — xem `doc/memory/vps_deploy_vbhc.md`)

## Kiến trúc storage (v1.0)

```
SKILL  (read-only)   — D:\SKILL_AI\skills\soan-thao-vbhc\
                       Code, helpers, danh-muc-loai-vb, checklist ND30, templates bundled
CACHE  (per-user)    — ~/.vbhc/cache/   (sync từ cloud KB Hub)
                       manifest.json, templates/<slug>.docx, rules/*.yaml, code/scripts.tar.gz
ORG    (chia sẻ)     — $VBHC_ORG_DIR (default ~/.vbhc/org/)
                       YAML cấu hình cơ quan: cơ quan, người ký, phòng soạn, nơi nhận default
USER   (per-task)    — D:\SoanThaoVB_\cong-viec\<NNNN>-<mô-tả>\
                       1-yeu-cau.md, 2-du-lieu.yaml, 1-tham-chieu/, output VB
```

## Kỹ thuật quan trọng (v1.0 vẫn dùng — KHÔNG đổi)

### Header chuẩn NĐ 30 — `scripts/vbhc_doc_builder.py`

Cell trái 7cm + cell phải 9cm = 16cm, padding 0, gạch chân 55% (tên CQ) / 100% (tiêu ngữ), stroke 0.5pt, line spacing single + before/after 0pt. **LUÔN import helpers, đừng tự build header bằng python-docx thủ công** — sẽ vỡ visual layout.

### Workaround `search_and_replace` trên table cell

`mcp__word__search_and_replace` fail trên text trong cell của file convert từ `.doc` → text split runs. Dùng python-docx trực tiếp: `paragraph.runs[0].text = new`, clear `runs[1:]`.

### Unicode print Windows

`cp1252` không encode được tiếng Việt → crash. Đầu mọi script:
```python
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```

Hoặc set env `PYTHONIOENCODING=utf-8` khi chạy.

### Kỹ thuật học mẫu (`vbhc_learn_template`)

`scripts/learn_template.py`: đọc file `.docx` → phân tích từng vùng (header, quốc hiệu, số/ký hiệu, ngày, người ký, nơi nhận) → so với 9 mục thể thức ND30 → trả `spec` (chi tiết) + `validation` (✓/⚠/✗) + `issues` (cần sửa). User review report_md → chốt → `vbhc_update_template` ghi vào `~/.vbhc/cache/templates/<slug>.docx`.

## v1.0 specific — đọc doc/HANDOFF-v1.0-WIP.md

Chi tiết về:
- Phase 1: Cloud Knowledge Hub HTTP (`cloud/kb_server.py`)
- Phase 1.5: Data-driven rules YAML (`tri-thuc-template/rules/`)
- Phase 2: Local sync + auto-bootstrap (`mcp/knowledge_client.py` + `bootstrap.py`)
- Phase 3: PowerShell installer (`cloud/install.ps1` + `uninstall.ps1`)
- Phase 4: Admin publish (scope, POST handler, `vbhc_publish_template`)
- Phase 5: Migration + release v1.0

Test commands, env vars, known quirks (UTF-8 BOM cho `.ps1`, KHÔNG dùng `-m mcp.bootstrap` do site-packages conflict, etc.) — tất cả ở `doc/HANDOFF-v1.0-WIP.md` section tương ứng.
