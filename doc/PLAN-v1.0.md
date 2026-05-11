# Plan — Nâng cấp VBHC: Local Thin-MCP + Cloud Knowledge Hub (Auto-Bootstrap)

## Context

**Vấn đề:** MCP server hiện đang deploy 2 cách:
- **Local stdio:** chạy trên máy user → file I/O OK, nhưng admin không thể đẩy update template/rule cho cả đội (mỗi máy 1 bản code).
- **Cloud HTTP (`mcp.hagiang.edu.vn`):** chạy trên VPS → admin update template/rule 1 chỗ là cả đội nhận, NHƯNG server cloud không truy cập được file trên máy user (`D:\SoanThaoVB_\...`). Workaround duy nhất hiện nay là UNC path — không thực tế cho cán bộ hành chính.

**Hệ quả:** Phải chọn 1 trong 2 trade-off:
- File-local nhưng update-thủ-công (git pull trên từng máy)
- Update-cloud nhưng phải share file qua network drive

**Mục tiêu:** Có cả 2 — file ở local, knowledge update từ cloud. Cụ thể những thứ cần update từ cloud:
- **Mẫu** (`resources/templates/*.docx`) — template chuẩn ND30
- **Thể thức** (`scripts/validate_thethuc.py`, `resources/the-thuc-vbhc-checklist.md`) — quy tắc 9 mục ND30
- **Cách kiểm tra** — logic validate, regex patterns, typo lists
- **Cách tạo file chuẩn** — helpers `vbhc_doc_builder.py` (XML patterns)

**Quyết định đã chốt với user:**
1. **Cloud chuyển hoàn toàn sang Knowledge Hub** — gỡ tools file-I/O ở cloud, cloud chỉ phục vụ assets.
2. **Local thin-MCP có auto-bootstrap** — máy nào thiếu file/component sẽ tự pull từ VPS khi cần (không cần user can thiệp).
3. **Installer dùng PowerShell `.ps1`** — hosted trên VPS, cài 1 lệnh.
4. **Rules YAML làm sớm (Phase 1.5)** — để rule có thể update từ cloud ngay cùng templates.

---

## Kiến trúc đề xuất: **Hybrid Local Runtime + Cloud Knowledge Hub**

```
┌────────────────────────────────────────────────────────────┐
│  CLOUD (mcp.hagiang.edu.vn)                                │
│  Knowledge Hub — HTTP API (FastAPI)                        │
│                                                            │
│  GET  /install.ps1                ← bootstrap installer    │
│  GET  /kb/manifest.json           ← version mọi asset      │
│  GET  /kb/templates/<slug>.docx   ← binary template        │
│  GET  /kb/rules/the-thuc.yaml     ← rule ND30 (YAML)       │
│  GET  /kb/rules/loai-vb.yaml      ← danh mục VB            │
│  GET  /kb/rules/typo-fixes.yaml   ← lỗi chính tả           │
│  GET  /kb/code/scripts.tar.gz     ← bundle scripts/        │
│  GET  /kb/code/version.txt        ← code-runtime version   │
│  GET  /kb/org/<org_id>/*.yaml     ← cấu hình per-org       │
│  POST /kb/templates/<slug>.docx   ← admin upload           │
│                                                            │
│  Auth: Bearer API key (giữ hệ thống v0.9 + manage_keys.py) │
│  /install.ps1 PUBLIC (không cần key) — bootstrap free      │
└──────────────────────┬─────────────────────────────────────┘
                       │ HTTPS pull (TTL + ETag + auto-bootstrap)
                       ▼
┌────────────────────────────────────────────────────────────┐
│  LOCAL (máy mỗi user — Windows/Mac)                        │
│  Thin MCP server — stdio (Claude Code)                     │
│                                                            │
│  Tools file-I/O (giữ nguyên signature, làm việc trên path  │
│  local — tự auto-pull asset nếu cache thiếu):              │
│   ├─ vbhc_classify                                         │
│   ├─ vbhc_create_workfolder                                │
│   ├─ vbhc_fill_template                                    │
│   ├─ vbhc_validate                                         │
│   ├─ vbhc_learn_template                                   │
│   ├─ vbhc_update_template       (lưu local)                │
│   └─ ... (11 tool hiện có)                                 │
│                                                            │
│  Tools MỚI:                                                │
│   ├─ vbhc_sync_knowledge        ← thủ công sync            │
│   ├─ vbhc_publish_template      ← push template lên cloud  │
│   └─ vbhc_knowledge_status      ← version + last sync      │
│                                                            │
│  Cache: ~/.vbhc/cache/                                     │
│   ├─ manifest.json     templates/  rules/  code/           │
│   └─ last_sync.json    (timestamp + ETag per asset)        │
│                                                            │
│  Config: ~/.vbhc/config.yaml                               │
│   ├─ cloud_url    api_key    org_id    auto_sync_hours: 24 │
│                                                            │
│  AUTO-BOOTSTRAP behavior (ở mỗi tool call):                │
│   1. Tool cần template X → check cache → thiếu? → pull    │
│   2. Cache > TTL (24h)? → background pull manifest         │
│   3. Code version mismatch? → log + cảnh báo user sync     │
│   4. Lỗi network? → fallback bundled defaults (resources/) │
└────────────────────────────────────────────────────────────┘
```

**Triết lý chia tầng:**

| Layer | Vị trí | Nội dung | Update channel |
|---|---|---|---|
| **Code runtime** (logic) | Local | `mcp/server.py`, helpers | `vbhc_sync_knowledge` (kéo `scripts.tar.gz`) |
| **Knowledge** (data + rules) | Cloud → cache | Templates, ND30 YAML rules, typo, ORG config | Auto-pull on demand + scheduled |
| **User files** | Local | `D:\SoanThaoVB_\cong-viec\<NNNN>-...\` | User edit |

**Điểm mạnh:**
- File user **không bao giờ rời máy** → bảo mật + đúng cách hành chính làm việc
- Admin update template/rule 1 lần → mọi user nhận khi sync tiếp theo (hoặc lần gọi tool tiếp theo nhờ auto-bootstrap)
- Hoạt động offline nếu cache còn
- Cán bộ mới: 1 lệnh `iwr https://mcp.hagiang.edu.vn/install.ps1 | iex` → xong
- Reuse 90% code hiện tại — tool signatures giữ nguyên, chỉ thay nguồn lookup (`SKILL_DIR/resources/` → `~/.vbhc/cache/` với fallback)

---

## Critical files to modify

| File | Thay đổi |
|---|---|
| `mcp/server.py` | (1) Thêm 3 tool mới (`vbhc_sync_knowledge`, `vbhc_publish_template`, `vbhc_knowledge_status`). (2) Refactor `_template_path(slug)`, `_rules_path(name)`: ưu tiên `~/.vbhc/cache/`, fallback `SKILL_DIR/resources/`. (3) Mỗi tool file-I/O thêm hook `_ensure_asset(name)` chạy auto-pull nếu thiếu. (4) Gỡ args HTTP mode (`--http`) ở local-only build, hoặc giữ cho dev. |
| `mcp/knowledge_client.py` *(mới)* | HTTP client: `sync_manifest()`, `pull_asset(uri)`, `pull_if_missing(name)`, ETag cache, retry với backoff, fallback offline. ~200 LOC. |
| `mcp/bootstrap.py` *(mới)* | First-run wizard: hỏi `cloud_url` + `api_key` → ghi `~/.vbhc/config.yaml` → gọi `sync_manifest()` lần đầu. Gọi từ `server.py` khi config rỗng. ~80 LOC. |
| `scripts/validate_thethuc.py` | Refactor: load rules từ `~/.vbhc/cache/rules/the-thuc.yaml` (fallback hardcode). 9 mục check thành data-driven (regex + keyword list trong YAML). |
| `scripts/learn_template.py` | Tương tự — typo list + assess rules từ `~/.vbhc/cache/rules/typo-fixes.yaml`. |
| `cloud/kb_server.py` *(mới)* | FastAPI app: route `/kb/*` (auth Bearer) + `/install.ps1` (public). ~250 LOC. Reuse `mcp/auth.py` middleware. Có thể chạy chung process với MCP cũ (transition) hoặc thay thế hoàn toàn. |
| `cloud/build_manifest.py` *(mới)* | Script chạy trên VPS: scan thư mục assets → sinh `manifest.json` với version (hash) + size + mtime. Chạy mỗi lần admin publish. |
| `cloud/install.ps1` *(mới)* | PowerShell installer. Logic: tải Python embeddable nếu thiếu → venv → `pip install` deps → clone repo (git hoặc tải zip từ VPS) → tạo `~/.vbhc/config.yaml` → register MCP trong Claude Code config. ~150 dòng. Hosted tại `https://mcp.hagiang.edu.vn/install.ps1`. |
| `cloud/uninstall.ps1` *(mới)* | Gỡ cài đặt sạch sẽ. |
| `tri-thuc-template/rules/the-thuc.yaml` *(mới)* | Data-driven ND30 rules (9 mục: regex, keyword list, exclusion rules). |
| `tri-thuc-template/rules/typo-fixes.yaml` *(mới)* | Typo list + Đ encoding fix + chính tả phổ biến. |
| `tri-thuc-template/rules/loai-vb.yaml` *(mới)* | 27+ loại VB + keyword classifier (extract từ `CLASSIFY_RULES` trong server.py). |
| `deploy/install-server.sh` | Thêm bước copy `cloud/kb_server.py` + tạo systemd service riêng cho KB (hoặc thêm route vào service hiện tại). |
| `INSTALL-LOCAL.md` *(mới)* | Hướng dẫn cán bộ: 1 lệnh PowerShell + nhập API key → xong. |
| `MIGRATION-v1.0.md` *(mới)* | Migration guide từ v0.9 (cloud MCP) → v1.0 (Local thin + Cloud KB). |

**Reuse — không viết lại:**
- Toàn bộ `vbhc_doc_builder.py` (helpers XML, ~600 LOC)
- Logic 11 tool hiện có — chỉ thay path lookup
- Auth middleware `mcp/auth.py` — dùng lại cho `/kb/*` routes
- `manage_keys.py` CLI (admin tool key)
- Toàn bộ `tri-thuc-template/*.yaml` hiện có (chỉ thêm folder `rules/`)

---

## Auto-Bootstrap Design (điểm mới quan trọng)

Mỗi máy local phải "tự liền sẹo" khi thiếu component. Cơ chế:

### 1. Bootstrap lần đầu (chạy installer)
```
install.ps1 → tạo ~/.vbhc/ → hỏi cloud_url + api_key
            → pull manifest.json + tất cả assets (templates, rules, code)
            → register MCP trong %APPDATA%\Claude\claude_desktop_config.json
            → smoke test: gọi vbhc_knowledge_status
```

### 2. Self-healing (mỗi tool call)
```python
def _ensure_asset(name: str):
    """Idempotent: tải nếu cache thiếu/stale. Background nếu stale, blocking nếu missing."""
    cache_path = CACHE_DIR / name
    if not cache_path.exists():
        knowledge_client.pull_blocking(name)   # phải có để chạy tool
    elif _is_stale(cache_path, ttl_hours=24):
        knowledge_client.pull_background(name) # không block, lần sau có bản mới
```

### 3. Code update (scripts/ hoặc helpers)
```
vbhc_knowledge_status → so version code local (~/.vbhc/cache/code/version.txt)
                       với cloud → nếu khác:
                       - WARN user "Có bản update code, chạy vbhc_sync_knowledge --code"
                       - Không tự reload code đang chạy (rủi ro)
                       - vbhc_sync_knowledge --code → tải scripts.tar.gz, extract, restart MCP
```

### 4. Fallback offline
```
Không kết nối được cloud → dùng cache hiện có
Cache trống + offline → dùng bundled defaults trong SKILL_DIR/resources/
                       (kèm khi cài, dù outdated)
                       Log WARNING "Đang dùng template offline, sync khi có mạng"
```

### 5. Config drift
```
Mỗi tool call: nếu ~/.vbhc/config.yaml thiếu cloud_url/api_key
              → in lỗi rõ ràng + gợi ý chạy `bootstrap` lại
```

---

## Migration path (5 phase, mỗi phase ship được)

### Phase 1 — Cloud Knowledge Hub (1.5 ngày)
- `cloud/kb_server.py` FastAPI serve `/kb/*` + `/install.ps1`
- `cloud/build_manifest.py` sinh manifest từ assets
- Deploy lên VPS, song song với MCP HTTP cũ (port riêng hoặc route riêng)
- Test: `curl /kb/manifest.json` + `curl /kb/templates/bao-cao.docx`
- **Ship được:** Admin có endpoint pull templates

### Phase 1.5 — Data-driven rules (1 ngày)
- Extract validate rules + typo list + classifier → 3 YAML trong `tri-thuc-template/rules/`
- Refactor `validate_thethuc.py`, `learn_template.py`, classifier để load YAML
- Test: thay 1 regex trong YAML → behavior thay đổi không cần đổi code
- Build manifest cập nhật rules → cloud serve
- **Ship được:** Rules có thể update từ cloud cùng templates

### Phase 2 — Local sync + auto-bootstrap (2 ngày)
- `mcp/knowledge_client.py` (HTTP + ETag + cache + offline fallback)
- `mcp/bootstrap.py` (first-run wizard)
- Thêm `vbhc_sync_knowledge`, `vbhc_knowledge_status` tools
- Refactor 11 tool hiện có: `_ensure_asset()` hook trước mỗi lần đọc template/rule
- Test: xóa cache → gọi `vbhc_fill_template` → tự pull asset → chạy thành công
- Test offline: ngắt mạng → vẫn chạy với cache cũ
- **Ship được:** Local MCP tự liền sẹo từ cloud

### Phase 3 — PowerShell installer (1 ngày)
- `cloud/install.ps1` — 1-liner cho cán bộ Windows
- Bao gồm: Python embeddable tải nếu thiếu, venv, pip install, git clone (hoặc tải zip), tạo config, register Claude Code MCP
- `cloud/uninstall.ps1` để gỡ sạch
- Tài liệu `INSTALL-LOCAL.md` cho non-tech user
- Test: máy Windows sạch → `iwr https://mcp.hagiang.edu.vn/install.ps1 | iex` → Claude Code có tools
- **Ship được:** Cán bộ mới onboard trong 5 phút

### Phase 4 — Admin publish workflow (0.5 ngày)
- `vbhc_publish_template` tool (chỉ key có scope `admin`)
- Flow: admin local `vbhc_update_template` (lưu cache local) → `vbhc_publish_template` (POST lên cloud + bump manifest)
- Cloud cập nhật manifest version → user khác lần sync tiếp theo nhận
- **Ship được:** Vòng đời template đầy đủ end-to-end

### Phase 5 — Migration v0.9 → v1.0 + dọn dẹp (1 ngày)
- `MIGRATION-v1.0.md` cho cán bộ hiện đang dùng cloud MCP v0.9
- Tắt MCP HTTP cũ (`--http` mode trong server.py) — chỉ giữ KB Hub
- Hoặc: giữ MCP HTTP read-only cho transition (gỡ tool file-I/O, chỉ giữ classify/validate)
- Cập nhật README, SKILL.md, HANDOFF.md
- **Ship được:** v1.0 stable, doc đầy đủ

**Tổng:** ~6–7 ngày dev. Mỗi phase backward-compatible.

---

## Verification

**Phase 1 — Cloud KB:**
```bash
curl -H "Authorization: Bearer $KEY" https://mcp.hagiang.edu.vn/kb/manifest.json
# → JSON với templates + rules + versions
curl -o /tmp/t.docx https://mcp.hagiang.edu.vn/kb/templates/bao-cao.docx
curl https://mcp.hagiang.edu.vn/install.ps1   # public, không cần auth
```

**Phase 1.5 — Rules YAML:**
```bash
# Trên VPS: edit tri-thuc-template/rules/typo-fixes.yaml (thêm "giửi: gửi")
python scripts/learn_template.py path/to/file.docx  # phát hiện typo mới
```

**Phase 2 — Auto-bootstrap:**
```powershell
# Windows local
Remove-Item -Recurse ~/.vbhc/cache  # xóa cache
# Trong Claude Code: gọi vbhc_fill_template với slug "bao-cao"
# → log: "[auto-bootstrap] pulling templates/bao-cao.docx..."
# → file output sinh thành công
```

```powershell
# Offline test
# Disable WiFi → gọi vbhc_validate → vẫn chạy với cache đã có
```

**Phase 3 — Cán bộ mới:**
```powershell
# Trên máy Windows sạch:
iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
# → prompt nhập api_key
# → cài Python + clone + config + register
# → Claude Code restart → thấy 11+3 tools
# → gọi vbhc_classify "báo cáo quý" → trả "Báo cáo"
```

**Phase 4 — Admin publish:**
```
Máy admin:
  "Học file Mau_Cong_van_moi.docx → ND30 OK → publish thành cong-van v2"
  → vbhc_learn_template → vbhc_update_template → vbhc_publish_template
  → manifest cloud: cong-van version bump

Máy cán bộ khác:
  vbhc_knowledge_status → thấy "cong-van: local=v1, cloud=v2"
  vbhc_sync_knowledge → pull → cache có v2
  vbhc_fill_template("cong-van", ...) → dùng v2 mới
```

**End-to-end smoke:**
1. Admin push template mới từ máy A
2. Cán bộ B (chưa từng dùng) cài bằng `install.ps1`
3. Cán bộ B soạn 1 công văn → file nằm trên ổ D: máy B, dùng template mới nhất
4. Ngắt mạng → cán bộ B vẫn validate được 1 file đã có (cache offline OK)
