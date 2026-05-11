"""VBHC Knowledge Hub — HTTP API phục vụ assets (templates, rules, code bundle).

Vai trò: thay vai trò của MCP HTTP cloud cũ. Server KHÔNG còn xử lý file của user;
chỉ làm "nguồn chân lý" cho các thứ chia sẻ trong tổ chức.

Routes:
    GET  /healthz                          (public)  — health check
    GET  /install.ps1                      (public)  — PowerShell installer 1-liner
    GET  /kb/manifest.json                 (auth)    — version + url của mọi asset
    GET  /kb/templates/<name>.docx         (auth)    — binary template
    GET  /kb/rules/<name>.yaml             (auth)    — YAML rule
    GET  /kb/code/scripts.tar.gz           (auth)    — bundle scripts/
    GET  /kb/code/version.txt              (auth)    — code-runtime version
    GET  /kb/org/<org_id>/<filename>       (auth)    — cấu hình per-org
    POST /kb/templates/<name>.docx         (auth+adm)— admin upload (Phase 4)

Auth: Bearer API key — reuse mcp/auth.py (cùng api-keys.yaml). Path `/install.ps1`
và `/healthz` là public (để 1-liner installer chạy được).

Run:
    python kb_server.py --host 127.0.0.1 --port 8766
    python kb_server.py --kb-dir /var/lib/vbhc-kb --api-keys-file /root/.vbhc/org/api-keys.yaml

Nginx reverse proxy (phía aaPanel):
    location /kb { proxy_pass http://127.0.0.1:8766; ... }
    location /install.ps1 { proxy_pass http://127.0.0.1:8766; ... }
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import re
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Import auth module từ mcp/ (cùng repo)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "mcp"))

from auth import APIKeyConfig, APIKeyMiddleware, periodic_flush  # noqa: E402

from starlette.applications import Starlette  # noqa: E402
from starlette.middleware import Middleware  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import (  # noqa: E402
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    Response,
)
from starlette.routing import Mount, Route  # noqa: E402

log = logging.getLogger("vbhc.kb")
if not log.handlers:
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


# =====================================================================
# Config (set at startup, read by route handlers)
# =====================================================================

class KBConfig:
    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir.resolve()

    def asset_path(self, *parts: str) -> Path:
        """Resolve asset path under kb_dir, refusing path traversal."""
        target = (self.kb_dir / Path(*parts)).resolve()
        # Ensure target stays inside kb_dir
        try:
            target.relative_to(self.kb_dir)
        except ValueError:
            raise PermissionError(f"Path traversal blocked: {parts}")
        return target


KB: KBConfig | None = None  # set in main()


# =====================================================================
# Validation: name patterns — chặn path traversal qua URL params
# =====================================================================

SAFE_SLUG = re.compile(r"^[a-z0-9][a-z0-9\-_]{0,63}$")
SAFE_FILENAME = re.compile(r"^[a-z0-9][a-z0-9\-_.]{0,127}\.(yaml|yml|docx|json|txt|md)$",
                           re.IGNORECASE)


def _bad_request(msg: str) -> Response:
    return JSONResponse({"error": msg}, status_code=400)


def _not_found(msg: str) -> Response:
    return JSONResponse({"error": msg}, status_code=404)


# =====================================================================
# Public routes (no auth)
# =====================================================================

async def healthz(request: Request) -> Response:
    return JSONResponse({"status": "ok", "kb_dir": str(KB.kb_dir)})


INSTALL_PS1_FALLBACK = """\
# vbhc installer placeholder — chưa được tải lên KB_DIR
# Đặt file install.ps1 tại $KB_DIR/install.ps1 hoặc tham khảo INSTALL-LOCAL.md
Write-Host "[vbhc] Installer chưa sẵn sàng. Liên hệ admin." -ForegroundColor Yellow
"""


async def install_ps1(request: Request) -> Response:
    """Serve PowerShell installer. Public (không cần auth) để 1-liner chạy được:
        iwr https://mcp.hagiang.edu.vn/install.ps1 | iex
    """
    p = KB.kb_dir / "install.ps1"
    if p.is_file():
        return FileResponse(
            str(p),
            media_type="text/plain; charset=utf-8",
            headers={"Cache-Control": "no-cache"},
        )
    return PlainTextResponse(INSTALL_PS1_FALLBACK, media_type="text/plain; charset=utf-8")


# =====================================================================
# Auth-protected routes (under /kb/*)
# =====================================================================

async def manifest(request: Request) -> Response:
    p = KB.kb_dir / "manifest.json"
    if not p.is_file():
        return _not_found("manifest.json chưa được build. Chạy build_manifest.py trên VPS.")
    return FileResponse(
        str(p),
        media_type="application/json",
        headers={"Cache-Control": "no-cache"},
    )


async def template(request: Request) -> Response:
    slug = request.path_params.get("slug", "")
    if not SAFE_SLUG.match(slug):
        return _bad_request(f"Invalid template slug: {slug!r}")
    try:
        p = KB.asset_path("templates", f"{slug}.docx")
    except PermissionError as e:
        return _bad_request(str(e))
    if not p.is_file():
        return _not_found(f"Template not found: {slug}")
    return FileResponse(
        str(p),
        media_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        filename=f"{slug}.docx",
    )


async def rule(request: Request) -> Response:
    name = request.path_params.get("name", "")
    if not SAFE_SLUG.match(name):
        return _bad_request(f"Invalid rule name: {name!r}")
    try:
        p = KB.asset_path("rules", f"{name}.yaml")
    except PermissionError as e:
        return _bad_request(str(e))
    if not p.is_file():
        # Cho phép .yml fallback
        try:
            p_yml = KB.asset_path("rules", f"{name}.yml")
        except PermissionError as e:
            return _bad_request(str(e))
        if p_yml.is_file():
            p = p_yml
        else:
            return _not_found(f"Rule not found: {name}")
    return FileResponse(
        str(p),
        media_type="text/yaml; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


async def code_bundle(request: Request) -> Response:
    p = KB.kb_dir / "code" / "scripts.tar.gz"
    if not p.is_file():
        return _not_found("code bundle chưa sẵn sàng — chạy build_manifest.py --import-from-repo")
    return FileResponse(
        str(p),
        media_type="application/gzip",
        filename="scripts.tar.gz",
    )


async def code_version(request: Request) -> Response:
    p = KB.kb_dir / "code" / "version.txt"
    if not p.is_file():
        return _not_found("code version chưa sẵn sàng")
    return FileResponse(
        str(p),
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache"},
    )


async def org_config(request: Request) -> Response:
    org_id = request.path_params.get("org_id", "")
    filename = request.path_params.get("filename", "")
    if not SAFE_SLUG.match(org_id):
        return _bad_request(f"Invalid org_id: {org_id!r}")
    if not SAFE_FILENAME.match(filename):
        return _bad_request(f"Invalid filename: {filename!r}")
    try:
        p = KB.asset_path("org", org_id, filename)
    except PermissionError as e:
        return _bad_request(str(e))
    if not p.is_file():
        return _not_found(f"Org config not found: {org_id}/{filename}")
    media = "text/yaml; charset=utf-8" if filename.lower().endswith((".yaml", ".yml")) \
        else "application/octet-stream"
    return FileResponse(str(p), media_type=media, headers={"Cache-Control": "no-cache"})


# =====================================================================
# Admin upload (Phase 4 — placeholder cho giờ trả 501)
# =====================================================================

async def template_upload(request: Request) -> Response:
    return JSONResponse(
        {"error": "Admin upload chưa kích hoạt — sẽ làm ở Phase 4 (vbhc_publish_template)"},
        status_code=501,
    )


# =====================================================================
# App factory
# =====================================================================

def build_app(api_keys: APIKeyConfig) -> Starlette:
    public_routes = [
        Route("/healthz", healthz, methods=["GET"]),
        Route("/install.ps1", install_ps1, methods=["GET"]),
    ]

    # Paths đây KHÔNG có prefix /kb — Mount("/kb", ...) sẽ strip prefix trước khi
    # routing đến sub-app, nên matching path bắt đầu từ sau /kb.
    protected_routes = [
        Route("/manifest.json", manifest, methods=["GET"]),
        Route("/templates/{slug}.docx", template, methods=["GET"]),
        Route("/templates/{slug}.docx", template_upload, methods=["POST"]),
        Route("/rules/{name}.yaml", rule, methods=["GET"]),
        Route("/rules/{name}.yml", rule, methods=["GET"]),
        Route("/code/scripts.tar.gz", code_bundle, methods=["GET"]),
        Route("/code/version.txt", code_version, methods=["GET"]),
        Route("/org/{org_id}/{filename}", org_config, methods=["GET"]),
    ]

    # Sub-app gắn middleware auth (tránh áp middleware lên /healthz và /install.ps1)
    protected = Starlette(routes=protected_routes,
                          middleware=[Middleware(APIKeyMiddleware, config=api_keys)])

    @asynccontextmanager
    async def lifespan(_app):
        flush_task = asyncio.create_task(periodic_flush(api_keys, 60))
        try:
            yield
        finally:
            flush_task.cancel()
            try:
                await flush_task
            except asyncio.CancelledError:
                pass
            api_keys.flush()

    # Mount auth-protected sub-app dưới /kb — middleware auth chỉ áp ở đây,
    # /healthz và /install.ps1 public.
    return Starlette(
        routes=public_routes + [Mount("/kb", app=protected)],
        lifespan=lifespan,
    )


def main():
    parser = argparse.ArgumentParser(description="VBHC Knowledge Hub HTTP server")
    parser.add_argument("--host", default="127.0.0.1",
                        help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8766,
                        help="Bind port (default: 8766)")
    parser.add_argument(
        "--kb-dir",
        default=os.environ.get("VBHC_KB_DIR") or "/var/lib/vbhc-kb",
        help="Knowledge Hub root directory (default: $VBHC_KB_DIR or /var/lib/vbhc-kb)",
    )
    parser.add_argument(
        "--api-keys-file",
        default=os.environ.get("VBHC_API_KEYS_FILE")
            or str(Path.home() / ".vbhc" / "org" / "api-keys.yaml"),
        help="API keys YAML (default: $VBHC_API_KEYS_FILE hoặc ~/.vbhc/org/api-keys.yaml)",
    )
    args = parser.parse_args()

    global KB
    KB = KBConfig(Path(args.kb_dir).expanduser())

    api_keys = APIKeyConfig(Path(args.api_keys_file).expanduser())

    print(f"[vbhc-kb] HTTP server: http://{args.host}:{args.port}", file=sys.stderr)
    print(f"[vbhc-kb] KB_DIR    = {KB.kb_dir}", file=sys.stderr)
    print(f"[vbhc-kb] API keys  = {args.api_keys_file} ({len(api_keys.keys)} key(s))",
          file=sys.stderr)

    import uvicorn
    app = build_app(api_keys)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
