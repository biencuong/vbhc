"""HTTP client cho cloud Knowledge Hub.

Trách nhiệm:
  1. Đọc/ghi ~/.vbhc/config.yaml (cloud_url, api_key, org_id)
  2. Pull manifest.json + assets (templates, rules, code) về ~/.vbhc/cache/
  3. ETag-based conditional GET — không tải lại file nếu sha256 không đổi
  4. Auto-bootstrap: tool call thiếu asset → tự pull (blocking) trước khi chạy
  5. Offline fallback: không kết nối được → dùng cache hiện có

Layout cache:
    ~/.vbhc/
    ├── config.yaml                 ← cloud_url + api_key + org_id
    ├── cache/
    │   ├── manifest.json           ← copy của manifest cloud
    │   ├── etag.json               ← {url → ETag} cho conditional GET
    │   ├── last_sync.json          ← timestamp + summary
    │   ├── templates/<slug>.docx
    │   ├── rules/<name>.yaml
    │   └── code/scripts.tar.gz + version.txt
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

# =====================================================================
# Paths
# =====================================================================

VBHC_HOME = Path(os.environ.get("VBHC_HOME") or (Path.home() / ".vbhc")).expanduser()
CONFIG_PATH = VBHC_HOME / "config.yaml"
CACHE_DIR = Path(
    os.environ.get("VBHC_CACHE_DIR") or (VBHC_HOME / "cache")
).expanduser()
ETAG_PATH = CACHE_DIR / "etag.json"
LAST_SYNC_PATH = CACHE_DIR / "last_sync.json"
MANIFEST_PATH = CACHE_DIR / "manifest.json"


# =====================================================================
# Config
# =====================================================================

DEFAULT_CONFIG: dict[str, Any] = {
    "cloud_url": "",                  # vd: "https://mcp.hagiang.edu.vn"
    "api_key": "",                    # vd: "vbhc_<64hex>"
    "org_id": "",                     # tùy chọn, vd: "so-gddt-tuyen-quang"
    "auto_sync_hours": 24,            # TTL cho background re-sync
    "offline_ok": True,               # cho phép dùng bundled fallback nếu không kết nối
}


def load_config() -> dict[str, Any]:
    """Đọc ~/.vbhc/config.yaml. Trả default nếu chưa có."""
    if not CONFIG_PATH.is_file():
        return dict(DEFAULT_CONFIG)
    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError:
        return dict(DEFAULT_CONFIG)
    merged = dict(DEFAULT_CONFIG)
    merged.update(data)
    return merged


def save_config(cfg: dict[str, Any]):
    """Ghi ~/.vbhc/config.yaml."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(
        yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    tmp.replace(CONFIG_PATH)
    # chmod 600 trên POSIX
    if sys.platform != "win32":
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except OSError:
            pass


def is_configured() -> bool:
    cfg = load_config()
    return bool(cfg.get("cloud_url") and cfg.get("api_key"))


# =====================================================================
# ETag persistence
# =====================================================================

def _load_etags() -> dict[str, str]:
    if not ETAG_PATH.is_file():
        return {}
    try:
        return json.loads(ETAG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_etags(etags: dict[str, str]):
    ETAG_PATH.parent.mkdir(parents=True, exist_ok=True)
    ETAG_PATH.write_text(
        json.dumps(etags, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# =====================================================================
# HTTP helpers
# =====================================================================

class KBError(Exception):
    pass


def _build_url(cloud_url: str, path: str) -> str:
    base = cloud_url.rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def _http_get(
    url: str,
    api_key: str,
    etag: Optional[str] = None,
    timeout: int = 30,
) -> tuple[Optional[bytes], Optional[str], int]:
    """GET với Bearer auth + optional If-None-Match.
    Trả (body | None nếu 304, etag mới | None, status)."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {api_key}")
    if etag:
        req.add_header("If-None-Match", etag)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            new_etag = resp.headers.get("ETag")
            body = resp.read()
            return body, new_etag, resp.status
    except urllib.error.HTTPError as e:
        if e.code == 304:
            return None, etag, 304
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            err_body = ""
        raise KBError(f"HTTP {e.code} {url}: {err_body}") from e
    except urllib.error.URLError as e:
        raise KBError(f"Network error {url}: {e}") from e


def _http_post(
    url: str,
    api_key: str,
    body: bytes,
    content_type: str = "application/octet-stream",
    timeout: int = 60,
) -> tuple[bytes, int]:
    """POST raw bytes với Bearer. Trả (response_body, status). Raise KBError nếu lỗi."""
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", content_type)
    req.add_header("Content-Length", str(len(body)))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.status
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            err_body = ""
        raise KBError(f"HTTP {e.code} POST {url}: {err_body}") from e
    except urllib.error.URLError as e:
        raise KBError(f"Network error POST {url}: {e}") from e


def _save_atomic(path: Path, body: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(body)
    tmp.replace(path)


def _sha256(body: bytes) -> str:
    h = hashlib.sha256()
    h.update(body)
    return h.hexdigest()


# =====================================================================
# Asset paths (cache layout)
# =====================================================================

# asset_kind ('templates' | 'rules' | 'code' | 'org' | None=manifest)
# → (relative path in cache, URL path on server)

def cache_path_for(kind: str, name: str = "") -> Path:
    if kind == "manifest":
        return MANIFEST_PATH
    if kind == "templates":
        return CACHE_DIR / "templates" / name
    if kind == "rules":
        return CACHE_DIR / "rules" / name
    if kind == "code":
        return CACHE_DIR / "code" / name
    if kind == "org":
        return CACHE_DIR / "org" / name
    raise ValueError(f"Unknown asset kind: {kind!r}")


def url_path_for(kind: str, name: str = "") -> str:
    if kind == "manifest":
        return "/kb/manifest.json"
    if kind == "templates":
        return f"/kb/templates/{name}"
    if kind == "rules":
        return f"/kb/rules/{name}"
    if kind == "code":
        return f"/kb/code/{name}"
    if kind == "org":
        return f"/kb/org/{name}"
    raise ValueError(f"Unknown asset kind: {kind!r}")


# =====================================================================
# Public API
# =====================================================================

def pull_asset(
    kind: str,
    name: str = "",
    *,
    use_etag: bool = True,
    timeout: int = 30,
) -> dict[str, Any]:
    """Tải 1 asset từ cloud về cache. Trả dict {pulled, cached, status, path, sha256}.

    Raise KBError nếu network fail hoặc HTTP error.
    """
    cfg = load_config()
    if not cfg.get("cloud_url") or not cfg.get("api_key"):
        raise KBError("Chưa có cloud_url/api_key — chạy bootstrap trước.")

    url_path = url_path_for(kind, name)
    url = _build_url(cfg["cloud_url"], url_path)

    etags = _load_etags()
    etag = etags.get(url) if use_etag else None
    dst = cache_path_for(kind, name)

    body, new_etag, status = _http_get(url, cfg["api_key"], etag=etag, timeout=timeout)

    if status == 304 and dst.is_file():
        return {
            "pulled": False, "cached": True, "status": 304,
            "path": str(dst), "sha256": _sha256(dst.read_bytes()),
        }

    if body is None:
        # 304 nhưng cache thiếu — buộc pull lại không ETag
        return pull_asset(kind, name, use_etag=False, timeout=timeout)

    _save_atomic(dst, body)
    if new_etag:
        etags[url] = new_etag
        _save_etags(etags)

    return {
        "pulled": True, "cached": False, "status": status,
        "path": str(dst), "sha256": _sha256(body), "size": len(body),
    }


def sync_manifest(timeout: int = 30) -> dict[str, Any]:
    """Pull manifest.json. Trả manifest đã parse."""
    info = pull_asset("manifest", use_etag=True, timeout=timeout)
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {**info, "manifest": data}


def publish_template(slug: str, source_path: Path | None = None,
                     timeout: int = 60) -> dict[str, Any]:
    """Upload 1 template từ local cache lên cloud KB Hub.

    Args:
        slug: slug loại VB (vd "bao-cao"). Phải khớp [a-z0-9][a-z0-9_-]*.
        source_path: file .docx nguồn. Default: ~/.vbhc/cache/templates/<slug>.docx
                     (file mà vbhc_update_template ghi xuống).
        timeout: HTTP timeout.

    Returns:
        dict response từ server: {ok, slug, sha256, size, archived_to,
        manifest_generated}. Raise KBError nếu network fail hoặc HTTP error.

    Note: server yêu cầu key có scope `admin`. 403 nếu thiếu.
    """
    cfg = load_config()
    if not cfg.get("cloud_url") or not cfg.get("api_key"):
        raise KBError("Chưa có cloud_url/api_key — chạy bootstrap trước.")

    src = source_path or cache_path_for("templates", f"{slug}.docx")
    src = Path(src)
    if not src.is_file():
        raise KBError(f"Không tìm thấy template tại {src} — chạy vbhc_update_template trước.")

    body = src.read_bytes()
    url_path = url_path_for("templates", f"{slug}.docx")
    url = _build_url(cfg["cloud_url"], url_path)

    resp_body, status = _http_post(
        url, cfg["api_key"], body,
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
        timeout=timeout,
    )
    try:
        result = json.loads(resp_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise KBError(f"Response không parse được JSON: {e} — raw: {resp_body[:200]!r}")

    if status != 200 or not result.get("ok"):
        raise KBError(f"Publish failed (status={status}): {result}")
    return result


def pull_if_missing(kind: str, name: str) -> dict[str, Any]:
    """Pull asset chỉ khi cache thiếu. Idempotent."""
    dst = cache_path_for(kind, name)
    if dst.is_file():
        return {"pulled": False, "cached": True, "path": str(dst)}
    return pull_asset(kind, name)


def _is_stale(path: Path, ttl_hours: float) -> bool:
    if not path.is_file():
        return True
    age = time.time() - path.stat().st_mtime
    return age > ttl_hours * 3600


def ensure_asset(kind: str, name: str, *, ttl_hours: float = 24.0) -> dict[str, Any]:
    """Đảm bảo asset có trong cache. Pull nếu thiếu hoặc stale.

    Dùng làm hook trước mỗi tool call cần asset. Gọi nhiều lần safe (cached
    sau lần đầu, network 304 nếu ETag khớp).
    """
    dst = cache_path_for(kind, name)
    if dst.is_file() and not _is_stale(dst, ttl_hours):
        return {"pulled": False, "fresh": True, "path": str(dst)}
    try:
        return pull_asset(kind, name)
    except KBError as e:
        # Offline fallback: nếu có cache cũ thì dùng, nếu không thì raise
        if dst.is_file():
            return {"pulled": False, "stale": True, "path": str(dst),
                    "offline_reason": str(e)}
        raise


def sync_all(timeout: int = 60) -> dict[str, Any]:
    """Sync toàn bộ: manifest + tất cả assets liệt kê trong manifest.

    Trả summary: pulled/cached counts + errors per asset.
    """
    cfg = load_config()
    if not is_configured():
        raise KBError("Chưa có cloud_url/api_key — chạy bootstrap trước.")

    manifest_info = sync_manifest(timeout=timeout)
    manifest = manifest_info["manifest"]

    results: dict[str, list] = {"templates": [], "rules": [], "code": [], "org": []}
    errors: list[dict] = []

    for slug, rec in (manifest.get("templates") or {}).items():
        name = f"{slug}.docx"
        try:
            r = pull_asset("templates", name, timeout=timeout)
            results["templates"].append({"name": name, **{k: r[k] for k in ("pulled", "status")}})
        except KBError as e:
            errors.append({"kind": "templates", "name": name, "error": str(e)})

    for stem, rec in (manifest.get("rules") or {}).items():
        name = f"{stem}.yaml"
        try:
            r = pull_asset("rules", name, timeout=timeout)
            results["rules"].append({"name": name, **{k: r[k] for k in ("pulled", "status")}})
        except KBError as e:
            errors.append({"kind": "rules", "name": name, "error": str(e)})

    # Code bundle (1 file)
    if manifest.get("code"):
        for name in ("scripts.tar.gz", "version.txt"):
            try:
                r = pull_asset("code", name, timeout=timeout)
                results["code"].append({"name": name, **{k: r[k] for k in ("pulled", "status")}})
            except KBError as e:
                errors.append({"kind": "code", "name": name, "error": str(e)})

    # Per-org config
    org_id = cfg.get("org_id")
    if org_id and (manifest.get("orgs") or {}).get(org_id):
        for filename in (manifest["orgs"][org_id] or {}).keys():
            name = f"{org_id}/{filename}"
            try:
                r = pull_asset("org", name, timeout=timeout)
                results["org"].append({"name": name, **{k: r[k] for k in ("pulled", "status")}})
            except KBError as e:
                errors.append({"kind": "org", "name": name, "error": str(e)})

    summary = {
        "synced_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "manifest_status": manifest_info["status"],
        "results": results,
        "errors": errors,
        "counts": {
            "templates": len(results["templates"]),
            "rules": len(results["rules"]),
            "code": len(results["code"]),
            "org": len(results["org"]),
            "errors": len(errors),
        },
    }

    LAST_SYNC_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_SYNC_PATH.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


def status() -> dict[str, Any]:
    """Trả thông tin cache hiện tại: version local vs cloud, last sync, drift."""
    cfg = load_config()
    out: dict[str, Any] = {
        "configured": is_configured(),
        "cloud_url": cfg.get("cloud_url"),
        "org_id": cfg.get("org_id") or None,
        "cache_dir": str(CACHE_DIR),
    }

    local_manifest: dict | None = None
    if MANIFEST_PATH.is_file():
        try:
            local_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            out["local_manifest"] = {
                "schema": local_manifest.get("schema"),
                "generated": local_manifest.get("generated"),
                "templates": list((local_manifest.get("templates") or {}).keys()),
                "rules": list((local_manifest.get("rules") or {}).keys()),
                "code_version": (local_manifest.get("code") or {}).get("version"),
            }
        except (json.JSONDecodeError, OSError):
            out["local_manifest"] = None

    if LAST_SYNC_PATH.is_file():
        try:
            out["last_sync"] = json.loads(LAST_SYNC_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            out["last_sync"] = None

    # Đếm assets thực có trong cache
    cache_inv: dict[str, list[str]] = {"templates": [], "rules": []}
    if (CACHE_DIR / "templates").is_dir():
        cache_inv["templates"] = sorted(
            p.name for p in (CACHE_DIR / "templates").iterdir()
            if p.is_file() and p.suffix == ".docx"
        )
    if (CACHE_DIR / "rules").is_dir():
        cache_inv["rules"] = sorted(
            p.name for p in (CACHE_DIR / "rules").iterdir()
            if p.is_file() and p.suffix in (".yaml", ".yml")
        )
    out["cached_assets"] = cache_inv

    # So với cloud (nếu kết nối được)
    if is_configured():
        try:
            info = sync_manifest(timeout=10)
            cloud_m = info["manifest"]
            out["cloud_manifest"] = {
                "generated": cloud_m.get("generated"),
                "code_version": (cloud_m.get("code") or {}).get("version"),
            }
            out["drift"] = _detect_drift(local_manifest, cloud_m)
        except KBError as e:
            out["cloud_error"] = str(e)

    return out


def _detect_drift(local: dict | None, cloud: dict) -> dict:
    """So sánh local vs cloud manifest, trả danh sách asset cần pull."""
    drift = {"templates": [], "rules": [], "code": None}
    if not local:
        return {**drift, "all_missing": True}

    local_tpl = local.get("templates") or {}
    cloud_tpl = cloud.get("templates") or {}
    for slug, rec in cloud_tpl.items():
        if local_tpl.get(slug, {}).get("sha256") != rec.get("sha256"):
            drift["templates"].append(slug)

    local_rules = local.get("rules") or {}
    cloud_rules = cloud.get("rules") or {}
    for name, rec in cloud_rules.items():
        if local_rules.get(name, {}).get("sha256") != rec.get("sha256"):
            drift["rules"].append(name)

    local_code = (local.get("code") or {}).get("version")
    cloud_code = (cloud.get("code") or {}).get("version")
    if local_code != cloud_code:
        drift["code"] = {"local": local_code, "cloud": cloud_code}

    return drift
