"""Build manifest.json cho Knowledge Hub.

Scan thư mục assets (templates, rules, code bundle), tính sha256 + size + mtime,
sinh file manifest.json mà KB server sẽ phục vụ tại /kb/manifest.json.

Layout assets mặc định (có thể override qua env / CLI):

    <KB_DIR>/
      manifest.json              ← sinh bởi script này
      templates/
        bao-cao.docx
        cong-van.docx
        phieu-ghi-y-kien.docx
      rules/                     ← sẽ tạo ở Phase 1.5
        the-thuc.yaml
        loai-vb.yaml
        typo-fixes.yaml
      code/
        scripts.tar.gz           ← bundle thư mục scripts/ của repo
        version.txt              ← "v1.0.0+<git-sha>"
      org/                       ← (Phase 4) cấu hình per-org
        <org_id>/
          05-thong-tin-co-quan.yaml
          phan-cong-nhiem-vu.yaml
          can-cu-phap-ly-mau.yaml

CLI:
    python build_manifest.py                       # KB_DIR = $VBHC_KB_DIR hoặc /var/lib/vbhc-kb
    python build_manifest.py --kb-dir /tmp/kb      # override
    python build_manifest.py --import-from-repo    # copy assets từ repo vào KB_DIR rồi build
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path


MANIFEST_NAME = "manifest.json"
SCHEMA_VERSION = 1


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def file_record(path: Path, url: str) -> dict:
    st = path.stat()
    return {
        "sha256": sha256_of(path),
        "size": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc)
            .isoformat(timespec="seconds"),
        "url": url,
    }


def scan_dir(root: Path, sub: str, url_prefix: str, suffixes: tuple[str, ...]) -> dict:
    """Quét thư mục root/sub, trả {basename_without_ext: file_record}."""
    out: dict[str, dict] = {}
    d = root / sub
    if not d.is_dir():
        return out
    for p in sorted(d.iterdir()):
        if not p.is_file() or not p.name.lower().endswith(suffixes):
            continue
        slug = p.stem
        out[slug] = file_record(p, f"{url_prefix}/{p.name}")
    return out


def get_git_version(repo: Path) -> str:
    """Lấy 'v<latest-tag>+<sha>' hoặc fallback timestamp nếu không có git."""
    try:
        sha = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--short=8", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sha = "unknown"
    try:
        tag = subprocess.check_output(
            ["git", "-C", str(repo), "describe", "--tags", "--abbrev=0"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        tag = "v0.0.0"
    return f"{tag}+{sha}" if sha != "unknown" else tag


def import_assets_from_repo(repo: Path, kb_dir: Path):
    """Copy assets từ repo (SKILL dir) sang KB_DIR. Dùng cho VPS deploy step."""
    src_tpl = repo / "resources" / "templates"
    dst_tpl = kb_dir / "templates"
    dst_tpl.mkdir(parents=True, exist_ok=True)
    for f in src_tpl.iterdir():
        if f.is_file() and f.suffix.lower() == ".docx":
            shutil.copy2(f, dst_tpl / f.name)

    src_rules = repo / "tri-thuc-template" / "rules"
    if src_rules.is_dir():
        dst_rules = kb_dir / "rules"
        dst_rules.mkdir(parents=True, exist_ok=True)
        for f in src_rules.iterdir():
            if f.is_file() and f.suffix.lower() in (".yaml", ".yml"):
                shutil.copy2(f, dst_rules / f.name)

    # Bundle scripts/ thành tarball để client tải về cập nhật code-runtime
    src_scripts = repo / "scripts"
    dst_code = kb_dir / "code"
    dst_code.mkdir(parents=True, exist_ok=True)
    tar_path = dst_code / "scripts.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(src_scripts, arcname="scripts")
    (dst_code / "version.txt").write_text(
        get_git_version(repo) + "\n", encoding="utf-8"
    )

    # PowerShell installer + uninstaller — kb_server serve qua /install.ps1
    # và /uninstall.ps1 (public routes). Copy lên KB_DIR root.
    for ps1 in ("install.ps1", "uninstall.ps1"):
        src = repo / "cloud" / ps1
        if src.is_file():
            shutil.copy2(src, kb_dir / ps1)


def build_manifest(kb_dir: Path) -> dict:
    templates = scan_dir(kb_dir, "templates", "/kb/templates", (".docx",))
    rules = scan_dir(kb_dir, "rules", "/kb/rules", (".yaml", ".yml"))

    code: dict = {}
    code_tar = kb_dir / "code" / "scripts.tar.gz"
    code_ver = kb_dir / "code" / "version.txt"
    if code_tar.is_file():
        code = file_record(code_tar, "/kb/code/scripts.tar.gz")
        if code_ver.is_file():
            code["version"] = code_ver.read_text(encoding="utf-8").strip()

    # ORG configs — gom theo org_id (subdir)
    orgs: dict[str, dict] = {}
    org_root = kb_dir / "org"
    if org_root.is_dir():
        for org_dir in sorted(org_root.iterdir()):
            if not org_dir.is_dir():
                continue
            files: dict[str, dict] = {}
            for p in sorted(org_dir.iterdir()):
                if p.is_file() and p.suffix.lower() in (".yaml", ".yml"):
                    files[p.name] = file_record(
                        p, f"/kb/org/{org_dir.name}/{p.name}"
                    )
            if files:
                orgs[org_dir.name] = files

    return {
        "schema": SCHEMA_VERSION,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "templates": templates,
        "rules": rules,
        "code": code,
        "orgs": orgs,
    }


def main():
    parser = argparse.ArgumentParser(description="Build KB Hub manifest.json")
    parser.add_argument(
        "--kb-dir",
        default=os.environ.get("VBHC_KB_DIR") or "/var/lib/vbhc-kb",
        help="Knowledge Hub root directory (default: $VBHC_KB_DIR or /var/lib/vbhc-kb)",
    )
    parser.add_argument(
        "--import-from-repo",
        default=None,
        help="Path to skill repo — copy templates/rules/scripts vào KB_DIR trước khi build",
    )
    args = parser.parse_args()

    kb_dir = Path(args.kb_dir).expanduser().resolve()
    kb_dir.mkdir(parents=True, exist_ok=True)

    if args.import_from_repo:
        repo = Path(args.import_from_repo).expanduser().resolve()
        if not repo.is_dir():
            print(f"ERROR: repo not found: {repo}", file=sys.stderr)
            sys.exit(2)
        import_assets_from_repo(repo, kb_dir)
        print(f"[ok] imported assets from {repo} → {kb_dir}", file=sys.stderr)

    manifest = build_manifest(kb_dir)
    out = kb_dir / MANIFEST_NAME
    out.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    n_tpl = len(manifest["templates"])
    n_rules = len(manifest["rules"])
    n_org = len(manifest["orgs"])
    code_ver = manifest["code"].get("version", "—")
    print(
        f"[ok] manifest written: {out}\n"
        f"     templates={n_tpl} rules={n_rules} orgs={n_org} code={code_ver}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
