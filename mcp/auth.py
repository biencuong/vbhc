"""API key auth middleware cho MCP server (HTTP transport).

Schema YAML (api-keys.yaml):

    keys:
      - id: "admin"
        key: "vbhc_<64hex>"
        description: "Admin laptop"
        allowed_ips: []                    # [] = allow all
        rate_limit_per_minute: 120
        created: "2026-05-11"
        last_used: null                    # ISO datetime hoặc null
        revoked: false

Middleware kiểm:
  1. Header `Authorization: Bearer <key>` — thiếu → 401
  2. Key tồn tại trong YAML — không → 401
  3. Key không revoked — revoked → 401
  4. IP nguồn (X-Real-IP từ nginx) ∈ allowed_ips (nếu list rỗng → allow all) — sai → 403
  5. Rate limit token bucket per-key — vượt → 429
  6. Update last_used in-memory + log audit + flush về YAML mỗi 60s

Stdio mode (local agent) KHÔNG dùng module này — process boundary đã tin cậy.
"""
from __future__ import annotations

import asyncio
import json
import logging
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

log = logging.getLogger("vbhc.auth")
if not log.handlers:
    h = logging.StreamHandler(sys.stderr)
    h.setFormatter(logging.Formatter("[%(asctime)s] %(name)s %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)


# =====================================================================
# Helpers
# =====================================================================

def gen_key() -> str:
    """Generate new API key: 'vbhc_<32-byte-hex>' (64 chars after prefix)."""
    return "vbhc_" + secrets.token_hex(32)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# =====================================================================
# Rate limiter (token bucket per-key, in-memory)
# =====================================================================

class _Bucket:
    __slots__ = ("capacity", "tokens", "refill_per_sec", "last")

    def __init__(self, per_minute: int):
        self.capacity = float(per_minute)
        self.tokens = float(per_minute)
        self.refill_per_sec = per_minute / 60.0
        self.last = time.monotonic()

    def take(self) -> bool:
        now = time.monotonic()
        delta = now - self.last
        self.tokens = min(self.capacity, self.tokens + delta * self.refill_per_sec)
        self.last = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


# =====================================================================
# Config
# =====================================================================

class APIKeyConfig:
    """Load + manage API keys file. Thread-safe lookup + rate limit."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._dirty = False
        self._buckets: dict[str, _Bucket] = {}
        self.records: list[dict] = []        # raw list từ yaml.keys
        self.by_key: dict[str, dict] = {}    # key string → record
        self._load()

    def _load(self):
        if not self.path.is_file():
            log.warning("API keys file not found: %s — server sẽ KHÔNG accept request nào",
                        self.path)
            self.records = []
            self.by_key = {}
            return
        text = self.path.read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(text) or {}
        except yaml.YAMLError as e:
            log.error("YAML parse error in %s: %s", self.path, e)
            self.records = []
            self.by_key = {}
            return
        self.records = list(data.get("keys") or [])
        self.by_key = {}
        for rec in self.records:
            k = rec.get("key", "").strip()
            if not k:
                continue
            self.by_key[k] = rec
        log.info("Loaded %d API keys from %s", len(self.by_key), self.path)

    @property
    def keys(self) -> list[str]:
        return list(self.by_key.keys())

    def lookup(self, key: str) -> Optional[dict]:
        with self._lock:
            return self.by_key.get(key)

    def take_token(self, rec: dict) -> bool:
        """Token bucket per-key. rate_limit_per_minute từ record (default 120)."""
        with self._lock:
            kid = rec.get("id", "")
            bucket = self._buckets.get(kid)
            limit = int(rec.get("rate_limit_per_minute", 120))
            if bucket is None or bucket.capacity != float(limit):
                bucket = _Bucket(limit)
                self._buckets[kid] = bucket
            return bucket.take()

    def mark_used(self, rec: dict):
        with self._lock:
            rec["last_used"] = _now_iso()
            self._dirty = True

    def flush(self):
        """Ghi list keys + last_used về YAML. Gọi định kỳ + lúc shutdown."""
        with self._lock:
            if not self._dirty:
                return
            data = {"keys": self.records}
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                           encoding="utf-8")
            tmp.replace(self.path)
            self._dirty = False


# =====================================================================
# Middleware
# =====================================================================

class APIKeyMiddleware(BaseHTTPMiddleware):
    """Starlette middleware: yêu cầu Bearer token hợp lệ cho mọi request."""

    def __init__(self, app, config: APIKeyConfig):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next):
        # Lấy IP nguồn — nginx forward qua X-Real-IP / X-Forwarded-For
        ip = (
            request.headers.get("X-Real-IP")
            or (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
            or (request.client.host if request.client else "")
        )
        path = request.url.path

        auth = request.headers.get("Authorization", "")
        if not auth.lower().startswith("bearer "):
            return self._reject(401, "Missing 'Authorization: Bearer <key>' header",
                                ip, path, kid="-")

        key = auth[7:].strip()
        rec = self.config.lookup(key)
        if rec is None:
            return self._reject(401, "Invalid API key", ip, path, kid="?")

        kid = rec.get("id", "?")

        if rec.get("revoked"):
            return self._reject(401, f"API key '{kid}' đã bị revoke",
                                ip, path, kid=kid)

        allowed_ips = rec.get("allowed_ips") or []
        if allowed_ips and ip and ip not in allowed_ips:
            return self._reject(403, f"IP {ip} không được phép cho key '{kid}'",
                                ip, path, kid=kid)

        if not self.config.take_token(rec):
            return self._reject(429,
                                f"Rate limit vượt ({rec.get('rate_limit_per_minute', 120)}/min)",
                                ip, path, kid=kid)

        self.config.mark_used(rec)

        try:
            resp = await call_next(request)
        except Exception:
            log.exception("Request handler error path=%s kid=%s", path, kid)
            raise

        log.info("auth_ok kid=%s ip=%s method=%s path=%s status=%d",
                 kid, ip, request.method, path, resp.status_code)
        return resp

    def _reject(self, status: int, reason: str, ip: str, path: str, kid: str) -> Response:
        log.warning("auth_deny kid=%s ip=%s path=%s status=%d reason=%s",
                    kid, ip, path, status, reason)
        body = json.dumps({"error": reason}, ensure_ascii=False)
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if status == 401:
            headers["WWW-Authenticate"] = 'Bearer realm="vbhc"'
        return Response(body, status_code=status, headers=headers)


# =====================================================================
# Background flush task (called from server entry point)
# =====================================================================

async def periodic_flush(config: APIKeyConfig, interval_sec: int = 60):
    """Async loop ghi last_used về YAML mỗi `interval_sec` giây."""
    while True:
        await asyncio.sleep(interval_sec)
        try:
            config.flush()
        except Exception:
            log.exception("Flush keys file failed")
