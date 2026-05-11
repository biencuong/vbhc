# Cài đặt — Router

> **v1.0 — kiến trúc đã đổi.** File này giờ chỉ là router. Chọn vai trò của bạn:

## Bạn là cán bộ (dùng skill để soạn VBHC)?

→ **[INSTALL-LOCAL.md](INSTALL-LOCAL.md)** — Cài Windows 1-liner PowerShell.

```powershell
iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
```

## Bạn đang dùng v0.9 cloud MCP HTTP?

→ **[MIGRATION-v1.0.md](MIGRATION-v1.0.md)** — 3 bước migrate sang v1.0 local.

## Bạn là admin/IT triển khai cloud KB Hub trên VPS?

→ **[INSTALL-AAPANEL.md](INSTALL-AAPANEL.md)** — Deploy Ubuntu + aaPanel + nginx + systemd.
→ **[cloud/README.md](cloud/README.md)** — Reference cloud/kb_server.py + build_manifest.py.

## Bạn là developer muốn dev/test/contribute?

```bash
# Clone repo
git clone https://github.com/biencuong/vbhc.git
cd vbhc

# Deps
pip install mcp python-docx openpyxl pyyaml uvicorn starlette

# Test local KB server (port 8766, dev key)
python cloud/build_manifest.py --kb-dir /tmp/kb-dev --import-from-repo .
python cloud/kb_server.py --host 127.0.0.1 --port 8766 \
    --kb-dir /tmp/kb-dev --api-keys-file <dev-keys.yaml>

# Bootstrap local thin-MCP với KB local
VBHC_HOME=/tmp/vbhc-dev python mcp/bootstrap.py \
    --url http://127.0.0.1:8766 --key vbhc_devkey0000...

# Register stdio MCP với Claude Code
claude mcp add vbhc-dev -s user -- python "$PWD/mcp/server.py"
```

Cấu hình dev keys với scope `read,admin`:

```bash
python scripts/manage_keys.py --file <keys.yaml> add admin1 --scope read,admin
```

Test smoke + e2e:

```bash
# Smoke offline (ensure_asset cache hit/stale/missing) — xem doc/HANDOFF-v1.0-WIP.md
# Smoke install.ps1 trên isolated env — xem same
# Smoke publish workflow — xem Phase 4 test
```

Chi tiết kiến trúc + quirks: **[doc/HANDOFF-v1.0-WIP.md](doc/HANDOFF-v1.0-WIP.md)**.

---

## Reference cũ (v0.9, đã deprecated)

File `INSTALL.md` trước đây (3 scenarios HTTP) còn trong git history. Để xem:

```bash
git log --all -- INSTALL.md | head    # tìm commit trước v1.0
git show <commit>:INSTALL.md | less   # xem nội dung
```

Hoặc xem branch tag `v0.9.1`.
