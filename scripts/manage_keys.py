"""manage_keys.py — CLI quản lý API keys cho VBHC MCP server.

Usage:
    manage_keys.py add <id> [--description TEXT] [--ips ip1,ip2] [--rate-limit N]
    manage_keys.py list [--show-keys]
    manage_keys.py revoke <id>
    manage_keys.py rotate <id>           # giữ id, sinh key mới
    manage_keys.py delete <id>           # xoá hẳn

Mặc định đọc/ghi `$VBHC_API_KEYS_FILE` (fallback `/root/.vbhc/api-keys.yaml`).
Override bằng `--file PATH`.

`add` in ra key 1 lần — admin LƯU LẠI ngay để cấp cho client. Sau đó key vẫn nằm
trong YAML (file đã chmod 600 — chỉ admin đọc được).
"""
from __future__ import annotations

import argparse
import os
import secrets
import sys, io
from datetime import date, datetime, timezone
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import yaml


_ORG_DIR = Path(os.environ.get("VBHC_ORG_DIR", str(Path.home() / ".vbhc" / "org")))
DEFAULT_PATH = Path(
    os.environ.get("VBHC_API_KEYS_FILE", str(_ORG_DIR / "api-keys.yaml"))
)


def gen_key() -> str:
    return "vbhc_" + secrets.token_hex(32)


def load(path: Path) -> dict:
    if not path.is_file():
        return {"keys": []}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if "keys" not in data:
        data["keys"] = []
    return data


def save(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                   encoding="utf-8")
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def find(records: list[dict], kid: str) -> dict | None:
    for r in records:
        if r.get("id") == kid:
            return r
    return None


def cmd_add(args):
    data = load(args.file)
    if find(data["keys"], args.id):
        print(f"[ERR] id '{args.id}' đã tồn tại — dùng `rotate` để đổi key, hoặc chọn id khác",
              file=sys.stderr)
        return 1
    key = gen_key()
    rec = {
        "id": args.id,
        "key": key,
        "description": args.description or "",
        "allowed_ips": [s.strip() for s in (args.ips or "").split(",") if s.strip()],
        "rate_limit_per_minute": int(args.rate_limit),
        "created": date.today().isoformat(),
        "last_used": None,
        "revoked": False,
    }
    data["keys"].append(rec)
    save(args.file, data)
    print(f"[OK] Added key '{args.id}' vào {args.file}")
    print()
    print(f"  Key:         {key}")
    print(f"  Description: {rec['description']}")
    print(f"  Allowed IPs: {rec['allowed_ips'] or '(any)'}")
    print(f"  Rate limit:  {rec['rate_limit_per_minute']} req/min")
    print()
    print("⚠ LƯU LẠI KEY TRÊN — đặt vào config client với header:")
    print(f"     Authorization: Bearer {key}")
    print("⚠ Key vẫn còn trong file (chmod 600 cho admin). Nếu mất, dùng `rotate {id}` để tạo key mới.")
    return 0


def cmd_list(args):
    data = load(args.file)
    if not data["keys"]:
        print(f"(không có key nào trong {args.file})")
        return 0
    rows = []
    for r in data["keys"]:
        key = r.get("key", "")
        if not args.show_keys and len(key) > 14:
            key_disp = key[:10] + "..." + key[-4:]
        else:
            key_disp = key
        rows.append({
            "id": r.get("id", "?"),
            "key": key_disp,
            "description": r.get("description", "")[:40],
            "ips": ",".join(r.get("allowed_ips") or []) or "(any)",
            "rate": str(r.get("rate_limit_per_minute", 120)),
            "last_used": r.get("last_used") or "-",
            "revoked": "YES" if r.get("revoked") else "no",
        })
    cols = ["id", "key", "description", "ips", "rate", "last_used", "revoked"]
    widths = {c: max(len(c), max(len(r[c]) for r in rows)) for c in cols}
    sep = "  ".join("-" * widths[c] for c in cols)
    print("  ".join(c.ljust(widths[c]) for c in cols))
    print(sep)
    for r in rows:
        print("  ".join(r[c].ljust(widths[c]) for c in cols))
    return 0


def cmd_revoke(args):
    data = load(args.file)
    rec = find(data["keys"], args.id)
    if rec is None:
        print(f"[ERR] không tìm thấy id '{args.id}'", file=sys.stderr)
        return 1
    if rec.get("revoked"):
        print(f"[INFO] '{args.id}' đã revoked từ trước")
        return 0
    rec["revoked"] = True
    save(args.file, data)
    print(f"[OK] Revoked key '{args.id}' — request từ key này sẽ bị từ chối ngay khi server reload config")
    print(f"     (server cache config khi start; restart MCP service để có hiệu lực)")
    return 0


def cmd_rotate(args):
    data = load(args.file)
    rec = find(data["keys"], args.id)
    if rec is None:
        print(f"[ERR] không tìm thấy id '{args.id}'", file=sys.stderr)
        return 1
    new_key = gen_key()
    rec["key"] = new_key
    rec["revoked"] = False
    rec["last_used"] = None
    save(args.file, data)
    print(f"[OK] Rotated key '{args.id}'")
    print()
    print(f"  New key: {new_key}")
    print()
    print("⚠ LƯU LẠI KEY TRÊN — cập nhật config client. Key cũ KHÔNG còn tác dụng sau khi restart MCP service.")
    return 0


def cmd_delete(args):
    data = load(args.file)
    rec = find(data["keys"], args.id)
    if rec is None:
        print(f"[ERR] không tìm thấy id '{args.id}'", file=sys.stderr)
        return 1
    data["keys"] = [r for r in data["keys"] if r.get("id") != args.id]
    save(args.file, data)
    print(f"[OK] Deleted key '{args.id}' (xoá hẳn khỏi YAML)")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Quản lý API keys VBHC MCP")
    ap.add_argument("--file", type=Path, default=DEFAULT_PATH,
                    help=f"Đường dẫn api-keys.yaml (default: {DEFAULT_PATH})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("add", help="Thêm key mới")
    p.add_argument("id")
    p.add_argument("--description", default="")
    p.add_argument("--ips", default="", help="Comma-separated allowed IPs (rỗng = allow all)")
    p.add_argument("--rate-limit", type=int, default=120, help="Req/min (default 120)")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="Liệt kê tất cả keys")
    p.add_argument("--show-keys", action="store_true", help="Hiện full key (mặc định mask)")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("revoke", help="Vô hiệu hoá key (vẫn giữ trong YAML)")
    p.add_argument("id")
    p.set_defaults(func=cmd_revoke)

    p = sub.add_parser("rotate", help="Đổi key mới, giữ id")
    p.add_argument("id")
    p.set_defaults(func=cmd_rotate)

    p = sub.add_parser("delete", help="Xoá hẳn key khỏi YAML")
    p.add_argument("id")
    p.set_defaults(func=cmd_delete)

    args = ap.parse_args()
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
