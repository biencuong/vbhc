# HANDOFF v1.0 — Local Thin-MCP + Cloud Knowledge Hub (đang dở Phase 2)

> **Tài liệu bàn giao cho phiên tiếp theo (Codex hoặc agent khác).** Đọc xong file này là biết:
> (1) đang giải bài toán gì, (2) plan tổng thể, (3) đã làm xong những gì + bằng chứng test, (4) đang dở chỗ nào, (5) việc gì cần tiếp.
>
> Tài liệu liên quan trong cùng folder `doc/`:
> - `PLAN-v1.0.md` — plan đầy đủ đã được user duyệt (5 phase)
> - `memory/` — bộ nhớ persistent của Claude (user profile, project state, feedback, references)
>
> Tài liệu nền (đặt ở root skill):
> - `HANDOFF.md` — bàn giao tổng quan kiến trúc skill (pre-v1.0)
> - `SKILL.md` — workflow 7 bước + anti-patterns
> - `UPGRADE-MULTI-CLIENT.md` — bối cảnh đa client (v0.9)

---

## 1. Bài toán + Mục tiêu

**Vấn đề gốc:** Cloud MCP server (`mcp.hagiang.edu.vn`) không truy cập được file trên máy user (`D:\SoanThaoVB_\...`). Workaround cũ phải UNC path — không thực tế cho cán bộ hành chính.

**Mục tiêu v1.0:**
- File user **ở local** (không upload server)
- Knowledge (templates, thể thức ND30, validation rules, code helper) **update từ cloud**
- Cán bộ mới onboard bằng **1 lệnh PowerShell**
- Local MCP **tự liền sẹo** (auto-bootstrap pull asset thiếu)

**Kiến trúc đề xuất (đã duyệt):**

```
CLOUD: Knowledge Hub HTTP (FastAPI)
  GET /healthz, /install.ps1, /kb/manifest.json,
      /kb/templates/<slug>.docx, /kb/rules/<name>.yaml,
      /kb/code/scripts.tar.gz, /kb/code/version.txt,
      /kb/org/<org_id>/<filename>
  Auth: Bearer API key (reuse mcp/auth.py)

LOCAL: Thin MCP server (stdio cho Claude Code)
  - 11 tool cũ (giữ signature, đổi nguồn lookup template)
  - 2 tool mới: vbhc_sync_knowledge, vbhc_knowledge_status
  - Cache: ~/.vbhc/cache/ (manifest + templates + rules + code)
  - Config: ~/.vbhc/config.yaml (cloud_url + api_key + org_id)
  - Auto-bootstrap: tool call thiếu asset → tự pull blocking
  - Offline fallback: cache hết hạn nhưng có → dùng cache cũ
```

Xem `PLAN-v1.0.md` (cùng folder) để biết chi tiết.

---

## 2. Trạng thái 5 phase

| # | Phase | Trạng thái | Ước lượng |
|---|---|---|---|
| 1 | Cloud Knowledge Hub (FastAPI serve assets) | ✅ **DONE** | 1.5 ngày |
| 1.5 | Extract rules → YAML (data-driven) | ✅ **DONE** | 1 ngày |
| 2 | Local sync + auto-bootstrap | ✅ **DONE** (commit 2f8b56a, 2026-05-11) | — |
| 3 | PowerShell installer (.ps1) | ✅ **DONE** (2026-05-11) | — |
| 4 | Admin publish workflow | ⏳ pending | 0.5 ngày |
| 5 | Migration v0.9 → v1.0 + cleanup | ⏳ pending | 1 ngày |

---

## 3. Phase 1 — Cloud Knowledge Hub ✅

### Files đã thêm

| File | Vai trò |
|---|---|
| `cloud/kb_server.py` | Starlette HTTP server, port 8766, reuse `mcp/auth.py` Bearer middleware. Mount `/kb/*` sub-app có auth, `/healthz` + `/install.ps1` public. |
| `cloud/build_manifest.py` | Script scan assets → sinh `manifest.json` (sha256 + size + mtime + version git). Có `--import-from-repo` để copy assets từ repo sang KB_DIR. |
| `cloud/vbhc-kb.service` | Systemd unit cho VPS. Port 8766, `VBHC_KB_DIR=/var/lib/vbhc-kb`. |
| `cloud/README.md` | Hướng dẫn deploy trên VPS + nginx config + test local. |

### Routes

```
GET  /healthz                        (public)  - health check
GET  /install.ps1                    (public)  - PowerShell installer (Phase 3)
GET  /kb/manifest.json               (auth)    - version mọi asset
GET  /kb/templates/<slug>.docx       (auth)    - binary template
GET  /kb/rules/<name>.yaml           (auth)    - YAML rule
GET  /kb/code/scripts.tar.gz         (auth)    - bundle scripts/
GET  /kb/code/version.txt            (auth)    - code-runtime version
GET  /kb/org/<org_id>/<filename>     (auth)    - cấu hình per-org
POST /kb/templates/<slug>.docx       (auth)    - placeholder 501 (Phase 4)
```

### Test (đã pass)

```bash
# Setup local
python cloud/build_manifest.py --kb-dir "<temp>" --import-from-repo .
python cloud/kb_server.py --host 127.0.0.1 --port 8766 \
    --kb-dir "<temp>" --api-keys-file "<test-keys.yaml>"

# Verify
GET /healthz                              → 200
GET /kb/manifest.json (no auth)           → 401 + WWW-Authenticate
GET /kb/manifest.json (Bearer hợp lệ)     → 200, JSON
GET /kb/templates/bao-cao.docx            → 200, 38059 bytes
GET /kb/templates/BAO-CAO.docx            → 400 (slug regex chặn uppercase)
GET /kb/templates/../etc/passwd.docx      → 404 (URL normalize)
POST /kb/templates/x.docx                 → 501 (placeholder Phase 4)
Bearer key sai                            → 401
```

### Deploy lên VPS (chưa làm)

```bash
# Trên VPS:
cd /home/mcp-soan-thao-vbhc && git pull
sudo mkdir -p /var/lib/vbhc-kb
sudo venv/bin/python cloud/build_manifest.py \
    --kb-dir /var/lib/vbhc-kb --import-from-repo .
sudo cp cloud/vbhc-kb.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now vbhc-kb

# Nginx (aaPanel):
# location /kb { proxy_pass http://127.0.0.1:8766; ... }
# location = /install.ps1 { proxy_pass http://127.0.0.1:8766/install.ps1; }
# location = /healthz     { proxy_pass http://127.0.0.1:8766/healthz; }
```

---

## 4. Phase 1.5 — Rules YAML ✅

### Triết lý

Tách **data** (regex, keywords, msgs, typo) ra YAML, giữ **logic** trong Python. Function structure không đổi — chỉ thay nguồn đọc constants.

### Files đã thêm/sửa

| File | Vai trò |
|---|---|
| `tri-thuc-template/rules/the-thuc.yaml` *(mới)* | 9 mục ND30: regex placeholder, 4 keyword quốc hiệu, regex chức vụ ký, lề 3-2-2-2, list từ khóa loại VB, ... |
| `tri-thuc-template/rules/typo-fixes.yaml` *(mới)* | Encoding fixes (`Ð U+00D0` → `Đ U+0110`) + typo (`kính giửi` → `kính gửi`). |
| `tri-thuc-template/rules/loai-vb.yaml` *(mới)* | 13 classify rules + 3 ambiguous form patterns (góp ý / phúc đáp / đề xuất). |
| `scripts/rules_loader.py` *(mới)* | Helper load YAML: cache (`~/.vbhc/cache/rules/`) → bundled (`tri-thuc-template/rules/`) → None. In-memory cache, `clear_cache()`. |
| `scripts/validate_thethuc.py` *(sửa)* | 9 check function đọc data từ `load_rules("the-thuc")`. Giữ `_FALLBACK` dict đầy đủ để backward compat khi YAML thiếu. |
| `scripts/learn_template.py` *(sửa, dòng 199-205 cũ)* | `assess_against_nd30` loop qua `typo_fixes` + `encoding_fixes` từ YAML thay vì hardcode 2 rule. |
| `mcp/server.py` *(sửa, dòng cũ 146-198)* | `CLASSIFY_RULES` + `AMBIGUOUS_FORM_PATTERNS` đổi thành helper `_get_classify_rules()` + `_get_ambiguous_patterns()` load từ YAML. `vbhc_classify` gọi helper mỗi call (sau sync sẽ refresh). |

### Test (đã pass)

```bash
# 1. Validate file cũ — output giống y trước refactor
python scripts/validate_thethuc.py examples/Bao-cao-Quy-I-Nam-2026-...docx
# → 7 ✓ / 2 ⚠ / 0 ✗ (Số VB trống cho VPHC điền + Dấu manual)

# 2. Classifier hoạt động qua YAML
vbhc_classify("Soạn báo cáo quý I/2026") → match "Báo cáo"
vbhc_classify("Công văn xin ý kiến")     → 2 matches (xin ý kiến + công văn)
vbhc_classify("góp ý dự thảo Thông tư X") → ambiguous (Báo cáo vs Công văn)

# 3. KEY TEST — thêm typo mới vào YAML không đổi code → flag được ngay
# Append {find: "sảo sát", replace: "khảo sát"} vào typo-fixes.yaml
# → assess_against_nd30(text="Báo cáo sảo sát ý kiến") → flag "Lỗi chính tả"

# 4. Offline fallback — YAML bị ẩn → hardcode _FALLBACK chạy bình thường
mv tri-thuc-template/rules/the-thuc.yaml .hidden
clear_cache()
check_quoc_hieu(text) → vẫn pass (rules_source = "none", dùng fallback)

# 5. KB server phục vụ rules
curl -H "Authorization: Bearer $KEY" http://127.0.0.1:8766/kb/rules/the-thuc.yaml
# → 200, 4479 bytes, content-type text/yaml
# Manifest có 3 rules với sha256
```

---

## 5. Phase 2 — Local sync + auto-bootstrap 🟡 (~80%)

### Files đã thêm/sửa

| File | Vai trò | Trạng thái |
|---|---|---|
| `mcp/knowledge_client.py` *(mới)* | HTTP client urllib + ETag + cache + offline fallback. ~330 LOC. API: `load_config`, `save_config`, `is_configured`, `pull_asset`, `sync_manifest`, `sync_all`, `ensure_asset`, `status`. | ✅ DONE |
| `mcp/bootstrap.py` *(mới)* | First-run wizard. CLI: `python -m mcp.bootstrap` (interactive) hoặc `--url --key --org` (non-interactive cho installer). Có `--status`. | ✅ DONE |
| `mcp/server.py` *(sửa)* | Thêm `_resolve_template_path(spec)` (slug→cache→bundled→cloud-pull). Sửa `vbhc_fill_template` chấp nhận cả slug lẫn path. Thêm 2 tool `vbhc_sync_knowledge` + `vbhc_knowledge_status`. | ✅ DONE |
| `scripts/rules_loader.py` đã có `clear_cache()` | Gọi từ `vbhc_sync_knowledge` sau sync để force reload rule YAML | ✅ DONE |

### Test đã pass

```bash
# Setup: VBHC_HOME isolated tại temp dir, không đụng config thật
VBHC_HOME="C:\Users\AD\AppData\Local\Temp\vbhc-home-test"

# 1. Bootstrap non-interactive
python mcp/bootstrap.py --url http://127.0.0.1:8766 \
    --key vbhc_devkey<...> --org so-gddt-tuyen-quang
# → Ghi config.yaml. Sync 3 templates + 3 rules + 2 code files. 0 errors.

# 2. Re-sync (test ETag — XEM PHẦN ISSUE BÊN DƯỚI)
# Hiện tại mọi asset trả 200 (chưa 304 vì FileResponse Starlette không emit ETag
# tự động — cần tay set hoặc upgrade strategy)

# 3. vbhc_knowledge_status
configured: True
cached templates: ['bao-cao.docx', 'cong-van.docx', 'phieu-ghi-y-kien.docx']
cached rules: ['loai-vb.yaml', 'the-thuc.yaml', 'typo-fixes.yaml']
drift: {templates: [], rules: [], code: None}
cloud code_version: v0.9.1+677e9a4d

# 4. vbhc_fill_template với SLUG (key feature mới)
_resolve_template_path("bao-cao")
# → C:\Users\AD\AppData\Local\Temp\vbhc-home-test\cache\templates\bao-cao.docx
# (chứ KHÔNG phải bundled — dùng cache!)
vbhc_fill_template(template_path="bao-cao", output_path="...", replace_ops=[...])
# → output sinh, ND30 auto-validate, dùng template từ cache

# 5. vbhc_classify offline
# Tắt server, set VBHC_CACHE_DIR đúng cache đã sync
vbhc_classify("Tờ trình xin chủ trương") → match "Tờ trình"
rules_source("loai-vb") → "cache"  (xác nhận đọc từ cache đã pull, không từ bundled)
```

### Việc đã đóng Phase 2 (commit 2f8b56a, 2026-05-11)

1. ✅ **Offline smoke test** — 3 scenarios PASS với `PYTHONIOENCODING=utf-8` + isolated test env trỏ port chết (`127.0.0.1:9`, timeout 2s). Test script: `C:\Users\AD\AppData\Local\Temp\test_offline_ensure_asset.py`.
   - Cache hit + fresh → `{pulled: False, fresh: True}`
   - Cache stale + offline → `{pulled: False, stale: True, offline_reason: "..."}`
   - Cache missing + offline → raise `KBError`

2. ✅ **Refactor `vbhc_update_template`** — đổi target từ `SKILL_DIR/resources/templates/` sang `kc.cache_path_for("templates", f"{slug}.docx")` = `~/.vbhc/cache/templates/<slug>.docx`. Sau khi ghi, `_resolve_template_path` tìm thấy slug ngay (đã smoke test). Preview & message mention Phase 4 publish workflow.

3. ✅ **Cập nhật `mcp/README.md`** — refresh count 5 → 13 tools, document `vbhc_sync_knowledge` + `vbhc_knowledge_status` chi tiết, thêm section "Cache layout (v1.0+)" + bootstrap workflow + troubleshooting cloud sync.

4. ⏸ **ETag — improvement nhỏ (optional, defer)** — hiện `FileResponse` không emit ETag → mọi re-sync trả 200. Không critical, sync vẫn correct. Có thể fix sau Phase 5.

---

## 6. Phase 3 — PowerShell installer ⏳

### Mục tiêu

Cán bộ Windows chạy **1 lệnh** là cài xong:

```powershell
iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
```

### Đã làm (2026-05-11)

| File | Vai trò |
|---|---|
| `cloud/install.ps1` *(mới, UTF-8 BOM)* | 1-liner installer. Detect Python ≥3.10, tạo `%LOCALAPPDATA%\vbhc\{repo,venv}\`, clone repo (fallback tarball zip), `pip install mcp python-docx openpyxl pyyaml uvicorn starlette`, prompt URL/key/org (hoặc nhận qua params), gọi `python mcp/bootstrap.py` (KHÔNG dùng `-m mcp.bootstrap` — conflict site-packages), `claude mcp add vbhc -s user -- ...`, smoke test = `bootstrap --status`. |
| `cloud/uninstall.ps1` *(mới, UTF-8 BOM)* | Gỡ entry MCP qua `claude mcp remove vbhc -s user`, xoá `%LOCALAPPDATA%\vbhc\`. Mặc định **giữ** `~/.vbhc/` (config + cache); `-PurgeAll` để xoá luôn. |
| `INSTALL-LOCAL.md` *(mới, root)* | Tài liệu non-tech: prereqs, 1-liner + tham số admin, troubleshooting (Python missing / 401 / 403 / Claude Desktop manual register / cài lại), vị trí file. |

### Quirks học được (cần nhớ)

1. **UTF-8 BOM bắt buộc** cho `.ps1` chứa tiếng Việt — Windows PowerShell 5.1 dùng codepage hệ thống nếu thiếu BOM. Add bằng `python -c "open(f,'wb').write(b'\xef\xbb\xbf' + open(f,'rb').read())"`.

2. **Không dùng `python -m mcp.bootstrap`** — site-packages `mcp` (lib chính thức) mask local `mcp/` folder (no `__init__.py`). Invoke trực tiếp script: `python <repo>/mcp/bootstrap.py`.

3. **Test isolated** dùng `VBHC_HOME` env var: `VBHC_HOME=C:\Temp\test-home powershell -File install.ps1 -SkipMcpRegister -McpName vbhc-test ...`. Tránh đụng real config + Claude entry.

### Test đã pass (2026-05-11)

```
VBHC_HOME=C:\Users\AD\AppData\Local\Temp\vbhc-install-test-home \
powershell -ExecutionPolicy Bypass -File cloud\install.ps1 \
    -NonInteractive \
    -InstallDir C:\...\vbhc-install-test \
    -CloudUrl http://127.0.0.1:8766 \
    -ApiKey vbhc_devkey... \
    -OrgId so-gddt-tuyen-quang \
    -SkipMcpRegister
```

→ 8 steps PASS (Python ✓, dir ✓, git clone ✓, venv+pip ✓, prompt skip ✓, bootstrap sync 3 templates+3 rules+2 code ✓, mcp register skipped, smoke status JSON drift=empty ✓).

Uninstall: `powershell -File cloud\uninstall.ps1 -NonInteractive -InstallDir ... -McpName vbhc-test-NEVER-EXIST` → InstallDir cleaned ✓, `~/.vbhc/` giữ (default) ✓.

### Test plan còn chưa làm (defer Phase 5)

- Máy Windows sạch (chưa có Python) — test friendly error message + winget hint
- Claude Desktop (không có `claude` CLI) — verify manual register instruction
- Mạng có proxy/firewall — verify error messages clear

---

## 7. Phase 4 — Admin publish workflow ⏳

### Mục tiêu

Admin "học mẫu" trên máy local → push template lên cloud → mọi user khác nhận khi sync tiếp.

### Specs

1. **Mở rộng `manage_keys.py` thêm scope:**
   ```yaml
   - id: "admin-bien-cuong"
     key: "vbhc_..."
     scope: ["read", "admin"]   # mới — default ["read"]
   ```

2. **Sửa `cloud/kb_server.py`:**
   - POST `/kb/templates/<slug>.docx` — yêu cầu scope `admin`, accept multipart upload, ghi vào `KB_DIR/templates/<slug>.docx`, rebuild manifest, bump version.
   - Có version retention (`templates-archive/<slug>-<ver>.docx`) để rollback.
   - Audit log: ai upload gì khi nào.

3. **Tool MCP mới `vbhc_publish_template(slug)`:**
   - Đọc `~/.vbhc/cache/templates/<slug>.docx` (đã được `vbhc_update_template` ghi)
   - POST lên cloud
   - Tự sync manifest sau push để các máy khác thấy version mới

4. **Tool `vbhc_publish_rule(name)`** (optional Phase 4.5) — admin push rule YAML mới.

### Test

- Admin local: `vbhc_learn_template(mau.docx)` → `vbhc_update_template("cong-van", confirmed=True)` (ghi cache) → `vbhc_publish_template("cong-van")` → manifest cloud bump
- User B máy khác: `vbhc_sync_knowledge` → thấy version mới → `vbhc_fill_template("cong-van", ...)` dùng template mới

---

## 8. Phase 5 — Migration v0.9 → v1.0 + cleanup ⏳

### Specs

1. **`MIGRATION-v1.0.md`** cho cán bộ đang dùng cloud MCP v0.9
   - 3 bước: backup, cài installer, gỡ MCP config cũ
2. **Gỡ MCP HTTP cũ trong `mcp/server.py`:**
   - Xóa code `--http` mode (lines 1100-1168 hiện tại)
   - Hoặc giữ readonly để transition (gỡ tool file-I/O, chỉ giữ classify/validate)
3. **Cập nhật doc nền:**
   - `README.md` — kiến trúc mới
   - `SKILL.md` — workflow tham chiếu 13 tool (thêm 2 mới + 1 publish)
   - `HANDOFF.md` — cập nhật section "Architecture" + "Tools"
   - `INSTALL.md` — đổi flow cài đặt (PowerShell installer thay vì git clone)
4. **Bump version** trong `mcp/pyproject.toml` → `v1.0.0`
5. **Git tag `v1.0.0`** + push

---

## 9. Critical files — tổng kết

### Files MỚI trong v1.0

```
cloud/
├── kb_server.py            # Phase 1 — HTTP server
├── build_manifest.py       # Phase 1
├── vbhc-kb.service         # Phase 1
├── README.md               # Phase 1
├── install.ps1             # Phase 3 (chưa làm)
└── uninstall.ps1           # Phase 3 (chưa làm)

mcp/
├── knowledge_client.py     # Phase 2 — HTTP client + cache
└── bootstrap.py            # Phase 2 — first-run wizard

scripts/
└── rules_loader.py         # Phase 1.5 — YAML loader cache→bundled

tri-thuc-template/rules/
├── the-thuc.yaml           # Phase 1.5 — 9 mục ND30
├── typo-fixes.yaml         # Phase 1.5 — chính tả + encoding
└── loai-vb.yaml            # Phase 1.5 — classifier + ambiguous forms

doc/
├── HANDOFF-v1.0-WIP.md     # File này
├── PLAN-v1.0.md            # Plan duyệt
└── memory/                 # Bộ nhớ Claude
    ├── MEMORY.md           # Index
    ├── user_domain.md
    ├── project_vbhc.md
    ├── skill_soan_thao_vbhc.md
    ├── project_template_fill.md
    ├── feedback_template_first.md
    ├── git_push_skill_vbhc.md
    ├── vps_deploy_vbhc.md
    ├── mcp_word_setup.md
    └── handoff_pointer.md
```

### Files đã SỬA (theo thứ tự nguyên tử nhỏ → lớn)

| File | Vùng thay đổi | Phase |
|---|---|---|
| `scripts/validate_thethuc.py` | Toàn bộ — refactor load YAML, giữ `_FALLBACK` dict đầy | 1.5 |
| `scripts/learn_template.py` | Lines 199-205 cũ — loop typo từ YAML | 1.5 |
| `mcp/server.py` | Lines 146-217 cũ — CLASSIFY_RULES + AMBIGUOUS đổi thành helper | 1.5 |
| `mcp/server.py` | Lines 219+ — import knowledge_client, thêm `_resolve_template_path` | 2 |
| `mcp/server.py` | `vbhc_fill_template` — đổi `Path()` thành `_resolve_template_path()` | 2 |
| `mcp/server.py` | Cuối file — thêm `vbhc_sync_knowledge` + `vbhc_knowledge_status` tool | 2 |

### Files KHÔNG đụng

- `mcp/auth.py` — reuse y nguyên cho cả MCP HTTP cũ + KB server mới
- `scripts/vbhc_doc_builder.py` — XML helpers, không liên quan rules
- `scripts/build_*_template.py` — generators, không liên quan
- Tất cả `tri-thuc-template/*.yaml` (gốc) — không đổi

---

## 10. Test setup — env vars + paths

```bash
# Isolated test (không đụng config thật ~/.vbhc/)
VBHC_HOME="C:\Users\AD\AppData\Local\Temp\vbhc-home-test"
VBHC_KB_DIR="C:\Users\AD\AppData\Local\Temp\vbhc-kb-test"
VBHC_API_KEYS_FILE="C:\Users\AD\AppData\Local\Temp\test-api-keys.yaml"
VBHC_CACHE_DIR="$VBHC_HOME\cache"   # optional override

# Dev API key
KEY="vbhc_devkey0000000000000000000000000000000000000000000000000000000"

# Run sequence (mở 2 terminal)
# T1: KB server
python cloud/kb_server.py --host 127.0.0.1 --port 8766 \
    --kb-dir "$VBHC_KB_DIR" --api-keys-file "$VBHC_API_KEYS_FILE"

# T2: bootstrap + test
python mcp/bootstrap.py --url http://127.0.0.1:8766 --key $KEY --org so-gddt-tuyen-quang
python mcp/bootstrap.py --status
```

**Cleanup giữa các test:**
```bash
rm -rf "$VBHC_HOME"
# api-keys.yaml file giữ nguyên (KB server tự update last_used)
```

---

## 11. Known issues / Gotchas

1. **Unicode print trên Windows** — `cp1252` không encode được tiếng Việt. Mỗi script test phải có `PYTHONIOENCODING=utf-8` hoặc print qua `sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`. `server.py` đã làm sẵn (lines 36-38).

2. **ETag chưa hoạt động** — Starlette `FileResponse` không emit `ETag` header mặc định → mọi re-sync trả 200, không 304. Sync vẫn correct nhưng tốn băng thông. Fix sau: emit ETag từ sha256 trong handler, hoặc dựa `If-Modified-Since` (đã có sẵn).

3. **Port conflict khi test** — nếu test trước chưa kill process cũ, server mới bind fail trên 8766. Dùng `taskkill /F /IM python.exe` (Windows) hoặc cẩn thận `TaskStop` task_id của BG process.

4. **`_resolve_template_path` auto-bootstrap chỉ chạy khi `is_configured()`** — nếu chưa có config.yaml + slug không có cache + không có bundled → trả `Path(raw)` cho caller báo "file not found". Đúng behavior (không silent fail).

5. **`vbhc_classify` constants** — `CLASSIFY_RULES` và `AMBIGUOUS_FORM_PATTERNS` ở module level vẫn còn (backward compat). Nhưng function gọi `_get_classify_rules()` mỗi call (qua `rules_loader` cache), nên thay rule YAML + clear_cache() → lần gọi sau dùng mới.

6. **`vbhc_update_template` chưa migrate** — đang ghi vào `SKILL_DIR/resources/templates/` (path read-only trên VPS). Phải đổi sang `~/.vbhc/cache/templates/` trong Phase 4 trước khi publish.

7. **`UPGRADE-MULTI-CLIENT.md`** ở root skill nói về kiến trúc đa-session v0.9 (Basic Auth → Bearer). KIẾN TRÚC NÀY ĐÃ BỊ THAY THẾ bởi v1.0 (local thin-MCP). Document đó nên đánh dấu deprecated trong Phase 5.

---

## 12. Bộ nhớ Claude (`doc/memory/`)

Đã copy 10 file từ `C:\Users\AD\.claude\projects\D--SKILL-AI-SoanThaoVB-\memory\` vào `doc/memory/` để Codex đọc được. Highlights:

- `user_domain.md` — User là cán bộ Sở GD&ĐT Tuyên Quang, soạn VBHC theo ND30/2020
- `project_vbhc.md` — Mục tiêu dự án
- `skill_soan_thao_vbhc.md` — Skill location + 11 tools v0.9
- `vps_deploy_vbhc.md` — Production endpoint `mcp.hagiang.edu.vn`, aaPanel
- `git_push_skill_vbhc.md` — **"đưa lên git" = auto add+commit+push, không hỏi confirm**; remote `github.com/biencuong/vbhc`
- `feedback_template_first.md` — File `Mau_*` trong `1-tham-chieu/` PHẢI làm khung, chỉ thay thể thức ND30
- `project_template_fill.md` — Convention `<NNNN>-<mô-tả>`, workaround search_and_replace fail trên cell
- `mcp_word_setup.md` — word-mcp-live v1.6.2 cài user scope (KHÔNG còn dùng trong v1.0 — disconnect rồi)

---

## 13. Tasks cho phiên tiếp theo

**Phase 2 + Phase 3 đã đóng** (commits 2f8b56a + 595dace + 2026-05-11). Sang Phase 4.

**Ưu tiên 1 — Phase 4 (0.5 ngày):**
- Viết `cloud/install.ps1` theo specs ở section 6
- Thêm `scope` vào api-keys schema + manage_keys.py
- POST handler trong kb_server.py
- Tool `vbhc_publish_template` trong server.py

**Ưu tiên 2 — Phase 5 (1 ngày):**
- `MIGRATION-v1.0.md`
- Gỡ HTTP mode trong server.py
- Cập nhật README, SKILL.md, HANDOFF.md (root)
- Tag `v1.0.0`

**Việc deploy lên VPS (sau khi xong Phase 5):**
- SSH vào `mcp.hagiang.edu.vn`
- `git pull` repo
- Run `cloud/build_manifest.py --import-from-repo .` để sinh KB_DIR
- Copy `cloud/install.ps1` + `cloud/uninstall.ps1` vào KB_DIR (cùng chỗ với manifest) để route `/install.ps1` + `/uninstall.ps1` serve được
- Install systemd `vbhc-kb.service`
- Sửa nginx aaPanel thêm `location /kb` + `location /install.ps1` + `location /uninstall.ps1`
- Test 1-liner installer trên máy thật (chưa cài)

---

## 14. Plan đã duyệt (tham chiếu)

Xem file đầy đủ tại `doc/PLAN-v1.0.md` (đã copy từ `~/.claude/plans/soft-splashing-bee.md`).

---

*Tạo bởi Claude Opus 4.7, 2026-05-11. Phiên tiếp theo (Codex) bắt đầu từ section 13.*
