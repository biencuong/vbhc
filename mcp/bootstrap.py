"""First-run bootstrap wizard cho local thin-MCP.

Tạo ~/.vbhc/config.yaml lần đầu, gọi sync_all() để pull mọi asset.

Usage:
    python -m mcp.bootstrap                          # interactive prompt
    python -m mcp.bootstrap --url URL --key KEY      # non-interactive
    python -m mcp.bootstrap --url URL --key KEY --org so-gddt-tuyen-quang
    python -m mcp.bootstrap --status                 # in trạng thái không sửa

Được PowerShell installer (Phase 3) gọi với --url + --key truyền từ user.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Cho phép `python -m mcp.bootstrap` lẫn `python mcp/bootstrap.py`
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import knowledge_client as kc  # noqa: E402


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{label}{suffix}: ").strip()
    return val or default


def interactive_bootstrap() -> int:
    print("=== VBHC local MCP — bootstrap ===\n")
    print(f"Config sẽ ghi tại: {kc.CONFIG_PATH}")
    print(f"Cache sẽ tạo tại: {kc.CACHE_DIR}\n")

    existing = kc.load_config() if kc.CONFIG_PATH.is_file() else None
    if existing and existing.get("cloud_url"):
        print(f"Đã có config: {existing.get('cloud_url')} (org={existing.get('org_id') or '—'})")
        if _prompt("Ghi đè? (y/N)", "N").lower() != "y":
            print("Hủy.")
            return 0

    cloud_url = _prompt(
        "Cloud URL (vd https://mcp.hagiang.edu.vn)",
        existing.get("cloud_url") if existing else "",
    )
    if not cloud_url:
        print("ERROR: thiếu cloud_url", file=sys.stderr)
        return 2

    api_key = _prompt(
        "API key (vbhc_...)",
        existing.get("api_key") if existing else "",
    )
    if not api_key:
        print("ERROR: thiếu api_key", file=sys.stderr)
        return 2

    org_id = _prompt(
        "Org ID (tùy chọn, vd so-gddt-tuyen-quang)",
        existing.get("org_id") if existing else "",
    )

    cfg = dict(kc.DEFAULT_CONFIG)
    cfg.update({"cloud_url": cloud_url.rstrip("/"),
                "api_key": api_key,
                "org_id": org_id or ""})
    kc.save_config(cfg)
    print(f"\n[OK] Đã ghi {kc.CONFIG_PATH}")

    print("\n=== Sync lần đầu ===")
    try:
        summary = kc.sync_all()
    except kc.KBError as e:
        print(f"[FAIL] Sync lỗi: {e}", file=sys.stderr)
        print("Kiểm tra cloud_url + api_key có đúng không, mạng có vào được không.",
              file=sys.stderr)
        return 3

    c = summary["counts"]
    print(f"[OK] Đã sync: templates={c['templates']} rules={c['rules']} "
          f"code={c['code']} org={c['org']} errors={c['errors']}")
    if c["errors"]:
        print("\nLỗi:")
        for e in summary["errors"]:
            print(f"  - {e['kind']}/{e['name']}: {e['error']}")
        return 4
    return 0


def non_interactive_bootstrap(url: str, key: str, org: str = "") -> int:
    cfg = dict(kc.DEFAULT_CONFIG)
    cfg.update({"cloud_url": url.rstrip("/"), "api_key": key, "org_id": org})
    kc.save_config(cfg)
    print(f"[OK] Đã ghi {kc.CONFIG_PATH}", file=sys.stderr)
    try:
        summary = kc.sync_all()
    except kc.KBError as e:
        print(f"[FAIL] Sync: {e}", file=sys.stderr)
        return 3
    print(json.dumps(summary["counts"], ensure_ascii=False), file=sys.stderr)
    return 0 if summary["counts"]["errors"] == 0 else 4


def print_status() -> int:
    info = kc.status()
    print(json.dumps(info, indent=2, ensure_ascii=False))
    return 0 if info.get("configured") else 1


def main():
    p = argparse.ArgumentParser(description="VBHC local MCP bootstrap")
    p.add_argument("--url", help="Cloud URL (non-interactive)")
    p.add_argument("--key", help="API key (non-interactive)")
    p.add_argument("--org", default="", help="Org ID (tùy chọn)")
    p.add_argument("--status", action="store_true", help="Chỉ in status")
    args = p.parse_args()

    if args.status:
        sys.exit(print_status())
    if args.url and args.key:
        sys.exit(non_interactive_bootstrap(args.url, args.key, args.org))
    sys.exit(interactive_bootstrap())


if __name__ == "__main__":
    main()
