# Hướng dẫn cho Codex — đọc trước khi code

> **Bạn là Codex** đang tiếp nhận dự án `soan-thao-vbhc` (Skill MCP soạn thảo Văn Bản Hành Chính theo NĐ 30/2020/NĐ-CP của VN) từ một phiên Claude trước. File này tóm tắt mọi thứ bạn cần để code tiếp **trong < 5 phút đọc**.

---

## 1. Bài toán 1 đoạn

User là cán bộ Sở GD&ĐT Tuyên Quang. Đã có Skill VBHC chạy 2 chế độ: (a) local stdio trên máy user (file OK, update khó), (b) cloud HTTP trên VPS (update dễ, không thấy file local). Đang chuyển sang kiến trúc **v1.0**: cloud thành "Knowledge Hub" (chỉ phục vụ templates + rules), local thành "thin-MCP" (xử lý file + tự pull asset từ cloud khi cần). Plan 5 phase, đang dở Phase 2 (~80%).

---

## 2. Đọc theo thứ tự

| File | Mục đích | Thời gian |
|---|---|---|
| `doc/HANDOFF-v1.0-WIP.md` | **Đọc đầu tiên — đầy đủ.** Section 13 = việc cần làm | 10 phút |
| `doc/PLAN-v1.0.md` | Plan kiến trúc đã duyệt (chỉ đọc khi cần ngữ cảnh sâu) | 5 phút |
| `doc/memory/MEMORY.md` | Index + 10 file memory ngắn (preferences user) | 3 phút |
| `HANDOFF.md` (root) | Kiến trúc skill pre-v1.0 — đọc nếu cần hiểu code cũ | tham chiếu |

**Không cần đọc:**
- `INSTALL-AAPANEL.md`, `MIGRATION-v0.9.md`, `UPGRADE-MULTI-CLIENT.md` — v0.9 sẽ bị deprecate ở Phase 5
- `examples/` — chỉ đọc khi debug template
- `tri-thuc-template/*.yaml` (ngoài folder `rules/`) — config mẫu cho ORG

---

## 3. Layout dự án

```
soan-thao-vbhc/
├── cloud/                    # 🆕 v1.0 — Cloud Knowledge Hub
│   ├── kb_server.py          # Starlette, port 8766
│   ├── build_manifest.py     # Sinh manifest.json
│   ├── vbhc-kb.service       # Systemd unit
│   ├── README.md             # Deploy guide
│   ├── install.ps1           # ❌ Phase 3 — chưa làm
│   └── uninstall.ps1         # ❌ Phase 3 — chưa làm
│
├── mcp/                      # MCP server (local stdio)
│   ├── server.py             # 11 tool cũ + 2 tool mới (sync_knowledge, knowledge_status)
│   ├── auth.py               # Bearer middleware (reuse cho cả KB server)
│   ├── knowledge_client.py   # 🆕 HTTP client + cache + offline fallback
│   └── bootstrap.py          # 🆕 First-run wizard
│
├── scripts/                  # Helpers Python
│   ├── vbhc_doc_builder.py   # ⚠ KHÔNG ĐỤNG — XML helpers core
│   ├── validate_thethuc.py   # 🔄 Refactored — load rule YAML
│   ├── learn_template.py     # 🔄 Refactored — typo từ YAML
│   ├── rules_loader.py       # 🆕 YAML loader (cache→bundled)
│   └── ... (10+ scripts khác)
│
├── tri-thuc-template/
│   ├── rules/                # 🆕 3 YAML rule
│   │   ├── the-thuc.yaml     # 9 mục ND30
│   │   ├── typo-fixes.yaml   # Typo + encoding
│   │   └── loai-vb.yaml      # 27+ loại VB
│   └── *.yaml                # Cấu hình ORG (không đụng)
│
├── resources/templates/      # 3 template .docx chuẩn ND30 (bundled fallback)
├── deploy/                   # Systemd cũ cho MCP HTTP (sẽ retire ở Phase 5)
├── doc/                      # 📁 Bàn giao (folder hiện tại)
└── examples/                 # File mẫu test
```

---

## 4. Quy ước + Preferences user

**(Tổng hợp từ `doc/memory/`. Tuân thủ nghiêm.)**

| Quy ước | Nguồn |
|---|---|
| **Git push không hỏi confirm** — khi user nói "đẩy git/lên git/git push", auto `add . && commit -m "..." && push`. Remote: `github.com/biencuong/vbhc`. | `memory/git_push_skill_vbhc.md` |
| **File `Mau_*` trong `1-tham-chieu/` PHẢI làm khung** — không tạo lại từ đầu, chỉ thay thể thức ND30 | `memory/feedback_template_first.md` |
| **Folder USER convention:** `<NNNN>-<mô-tả>/` 4 số đầu + slug VN | `memory/project_template_fill.md` |
| **Validate ND30 9 mục là BẮT BUỘC** — đã có auto-hook trong `vbhc_fill_template` | `HANDOFF.md` section 7 |
| **Đ encoding bug:** file `.doc` cũ chứa `Ð` (U+00D0) thay `Đ` (U+0110) — phải fix trước xử lý | `HANDOFF.md` section 9.2 (B2) |
| **Output user-facing dùng tiếng Việt**, code comment cũng tiếng Việt | Nhìn code hiện tại |

---

## 5. Test local — setup nhanh

```bash
# Env vars cho test isolated (không đụng config thật ~/.vbhc/)
export VBHC_HOME="C:/Users/AD/AppData/Local/Temp/vbhc-home-test"
export VBHC_KB_DIR="C:/Users/AD/AppData/Local/Temp/vbhc-kb-test"
export VBHC_API_KEYS_FILE="C:/Users/AD/AppData/Local/Temp/test-api-keys.yaml"
export PYTHONIOENCODING=utf-8                                # ⚠ BẮT BUỘC trên Windows

# Dev API key (chỉ dùng trong test):
KEY="vbhc_devkey0000000000000000000000000000000000000000000000000000000"

# Test sequence:
# T1: build manifest từ repo
python cloud/build_manifest.py --kb-dir "$VBHC_KB_DIR" --import-from-repo .

# T2: chạy KB server (background)
python cloud/kb_server.py --host 127.0.0.1 --port 8766 \
    --kb-dir "$VBHC_KB_DIR" --api-keys-file "$VBHC_API_KEYS_FILE" &

# T3: bootstrap local
python mcp/bootstrap.py --url http://127.0.0.1:8766 --key $KEY --org so-gddt-tuyen-quang

# T4: smoke test
python mcp/bootstrap.py --status
python scripts/validate_thethuc.py examples/Bao-cao-Quy-I-Nam-2026-So-GDDT-Tuyen-Quang.docx

# Cleanup
rm -rf "$VBHC_HOME"
```

**File `test-api-keys.yaml` đã tồn tại** tại `C:\Users\AD\AppData\Local\Temp\test-api-keys.yaml` (key dev, không phải production).

---

## 6. Việc CẦN LÀM ngay (Ưu tiên 1, ~0.3 ngày)

> Đóng nốt Phase 2. Chi tiết ở `HANDOFF-v1.0-WIP.md` section 13.

### 6.1 Retry offline test (5 phút)

Test bị interrupt khi user còn xem dở. Retry với `PYTHONIOENCODING=utf-8`:

```bash
PYTHONIOENCODING=utf-8 VBHC_HOME="$VBHC_HOME" python -c "
import sys; sys.path.insert(0, 'mcp')
import knowledge_client as kc
# Test 1: cache fresh
r = kc.ensure_asset('templates', 'bao-cao.docx', ttl_hours=24)
print('fresh:', {k: r.get(k) for k in ('pulled', 'fresh')})
# Test 2: stale + server down → offline fallback
r = kc.ensure_asset('templates', 'bao-cao.docx', ttl_hours=0)
print('stale:', {k: r.get(k) for k in ('pulled', 'stale', 'offline_reason')})
# Test 3: missing + offline → KBError
try:
    kc.ensure_asset('templates', 'never-existed.docx')
except kc.KBError as e:
    print(f'missing+offline OK: {str(e)[:60]}')
"
```

Expected: test 1 trả `fresh=True`, test 2 trả `stale=True` + `offline_reason="Network error..."`, test 3 raise.

### 6.2 Refactor `vbhc_update_template` (15 phút)

File: `mcp/server.py` ~line 1021-1097 (function `vbhc_update_template`).

**Hiện tại:** ghi vào `SKILL_DIR/resources/templates/<slug>.docx` (read-only trên VPS).

**Cần đổi:** ghi vào `~/.vbhc/cache/templates/<slug>.docx` (writable local cache).

Lý do: Phase 4 sẽ thêm `vbhc_publish_template` để push từ cache → cloud. Nếu update vẫn ghi vào `resources/`, admin không "publish" được vì resources/ là read-only.

**Cách làm:** đổi 1 dòng `target = SKILL_DIR / "resources" / "templates" / ...` → `target = kc.CACHE_DIR / "templates" / ...`. Đảm bảo parent dir tạo trước nếu chưa có.

### 6.3 Cập nhật `mcp/README.md` (5 phút)

Thêm section "Tools v1.0 (mới)" liệt kê:
- `vbhc_sync_knowledge(force, only)` — pull cloud → cache
- `vbhc_knowledge_status()` — show config + cache + drift

### 6.4 Commit + push (1 phút)

User cho phép auto-push không hỏi (xem `memory/git_push_skill_vbhc.md`):

```bash
git add cloud/ mcp/knowledge_client.py mcp/bootstrap.py mcp/server.py \
        scripts/rules_loader.py scripts/validate_thethuc.py scripts/learn_template.py \
        tri-thuc-template/rules/ doc/
git commit -m "v1.0-rc1: Cloud KB Hub + rules YAML + local sync (Phase 1+1.5+2 WIP)

- cloud/: FastAPI KB server, manifest builder, systemd unit
- mcp/: knowledge_client (HTTP + cache + ETag + offline), bootstrap wizard
- mcp/server.py: vbhc_sync_knowledge, vbhc_knowledge_status, _resolve_template_path
- scripts/rules_loader.py: cache→bundled YAML loader
- scripts/validate_thethuc.py + learn_template.py: data-driven rules
- tri-thuc-template/rules/: the-thuc.yaml + typo-fixes.yaml + loai-vb.yaml
- doc/: handoff cho phiên kế tiếp"
git push origin main
```

---

## 7. Việc kế tiếp (sau khi Phase 2 đóng)

**Ưu tiên 2 — Phase 3 PowerShell installer (1 ngày).** Specs đầy đủ ở `HANDOFF-v1.0-WIP.md` section 6.

**Ưu tiên 3 — Phase 4 Admin publish (0.5 ngày).** Specs ở section 7.

**Ưu tiên 4 — Phase 5 Migration + cleanup (1 ngày).** Specs ở section 8.

---

## 8. Cạm bẫy + Lưu ý

1. **Unicode trên Windows** — `cp1252` không encode được tiếng Việt. **Mọi script test phải có `PYTHONIOENCODING=utf-8`.** Code production (`server.py` line 36-38) đã handle sẵn.

2. **Port 8766 conflict** — nếu test trước chưa kill, server mới bind fail. Trên Windows: `taskkill /F /IM python.exe` hoặc tracking PID. Trong Claude Code thì dùng `TaskStop`.

3. **Path Windows trong bash** — dùng forward slash hoặc quote đầy đủ: `"D:\path"` bị bash ăn backslash. Dùng `"D:/path"` hoặc shell PowerShell trực tiếp.

4. **`_resolve_template_path` chỉ auto-pull khi `kc.is_configured()`** — chưa có config → trả path "as-is" cho caller báo lỗi rõ ràng. Đúng behavior, không silent fail.

5. **ETag chưa hoạt động** (known issue) — Starlette `FileResponse` không emit `ETag` mặc định → re-sync trả 200 (re-download), không 304. **Không phá correctness**, chỉ tốn băng thông. Fix tùy chọn ở phase sau.

6. **`vbhc_classify` constants** — `CLASSIFY_RULES` + `AMBIGUOUS_FORM_PATTERNS` ở module level VẪN tồn tại (backward compat). Nhưng function tool gọi `_get_classify_rules()` mỗi lần (qua `rules_loader` cache). Thay YAML + `clear_cache()` → lần gọi sau dùng mới.

7. **File `Mau_*` trong USER folder** — không bao giờ ghi đè. Đó là input của user.

8. **`vbhc_doc_builder.py`** — XML helpers core, **KHÔNG REFACTOR**. Mọi thay đổi format Word đi qua helpers này. Xem `HANDOFF.md` section 5.

---

## 9. Liên hệ / Verify khi xong

- **Smoke test cuối cùng:** workflow đầy đủ — bootstrap → sync → fill_template với slug → validate ND30. Phải pass 0 errors.
- **Đẩy git** sau mỗi phase đóng (user expect, không hỏi confirm).
- **Update `doc/HANDOFF-v1.0-WIP.md`** mỗi khi đóng 1 phase: đổi 🟡 → ✅, thêm bằng chứng test.
- **Trong commit message:** mô tả phase + file thêm/sửa, không cần dài dòng.

---

*File này tạo bởi Claude Opus 4.7, 2026-05-11, để chuyển giao cho Codex.*
