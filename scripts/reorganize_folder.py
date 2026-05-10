"""Reorganize a messy folder into the standard <NNNN>-<slug>/ structure.

Usage:
    python reorganize_folder.py <messy_folder> [--name "phieu-bieu-quyet-..."] [--dry-run]

Behavior:
    1. Determine new folder name <NNNN>-<slug> (next number under parent's cong-viec/).
    2. Create new folder + 3-tham-chieu/ subfolder.
    3. Move all files from messy folder into 3-tham-chieu/ (preserve names).
    4. Create empty 1-yeu-cau.md (from template) and 2-du-lieu.yaml (from template).
    5. Try to remove old empty folder (skip if locked).

Exit codes:
    0 = OK
    1 = error (missing folder, name conflict, etc.)
"""
import argparse
import shutil
import sys
from pathlib import Path

from _common import slugify_vn, next_folder_number, human_size

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TPL_REQ = SKILL_DIR / "resources" / "templates" / "1-yeu-cau.md.tpl"
TPL_YAML = SKILL_DIR / "resources" / "templates" / "2-du-lieu.yaml.tpl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", help="Path to messy folder containing source files")
    ap.add_argument("--name", default=None, help="Custom slug for new folder (without NNNN-)")
    ap.add_argument("--parent", default=None,
                    help="Parent dir for new folder (default: parent of source, or ./cong-viec)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = Path(args.source).resolve()
    if not src.is_dir():
        print(f"ERROR: '{src}' is not a directory", file=sys.stderr)
        return 1

    # Decide parent
    if args.parent:
        parent = Path(args.parent).resolve()
    else:
        # If src is inside a folder named cong-viec → use that
        if src.parent.name == "cong-viec":
            parent = src.parent
        else:
            parent = src.parent
    parent.mkdir(parents=True, exist_ok=True)

    # Decide new name
    nnnn = next_folder_number(parent)
    if args.name:
        slug = slugify_vn(args.name)
    else:
        slug = slugify_vn(src.name) or "ho-so-moi"
    new_name = f"{nnnn}-{slug}"
    new_path = parent / new_name

    if new_path.exists():
        print(f"ERROR: target '{new_path}' already exists", file=sys.stderr)
        return 1

    # List files to move
    files = [f for f in src.iterdir() if f.is_file()]
    print(f"Source: {src}")
    print(f"Target: {new_path}")
    print(f"Files to move: {len(files)}")
    for f in files:
        print(f"  - {f.name} ({human_size(f.stat().st_size)})")

    if args.dry_run:
        print("\n[DRY RUN] No changes made.")
        return 0

    # Execute
    new_path.mkdir(parents=True)
    ky_thuat = new_path / "0-ky-thuat"
    tham_chieu = new_path / "1-tham-chieu"
    ky_thuat.mkdir()
    tham_chieu.mkdir()

    moved = 0
    for f in files:
        dst = tham_chieu / f.name
        shutil.move(str(f), str(dst))
        moved += 1

    # Create metadata files from templates → 0-ky-thuat/
    yc = ky_thuat / "1-yeu-cau.md"
    if TPL_REQ.exists():
        yc.write_text(TPL_REQ.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        yc.write_text("# Yêu cầu công việc\n\n(điền sau)\n", encoding="utf-8")

    dl = ky_thuat / "2-du-lieu.yaml"
    if TPL_YAML.exists():
        dl.write_text(TPL_YAML.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        dl.write_text("# Dữ liệu\n", encoding="utf-8")

    # Try to remove old folder
    try:
        src.rmdir()
        old_status = "deleted"
    except OSError:
        old_status = f"NOT deleted (may be locked or non-empty): {src}"

    print(f"\n✓ Created: {new_path}")
    print(f"✓ Moved {moved} file(s) to 1-tham-chieu/")
    print(f"✓ Created 0-ky-thuat/{{1-yeu-cau.md, 2-du-lieu.yaml}} from template")
    print(f"✓ Old folder: {old_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
