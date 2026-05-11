"""Helper load rules YAML từ cache (ưu tiên) hoặc bundled (fallback).

Thứ tự lookup:
    1. ~/.vbhc/cache/rules/<name>.yaml   ← sync từ cloud KB Hub (mới nhất)
    2. <SKILL_DIR>/tri-thuc-template/rules/<name>.yaml   ← bundled với repo
    3. None  ← caller dùng hardcoded fallback trong Python

Có cache nhỏ in-memory để tránh re-parse YAML mỗi lần gọi.

Public API:
    load_rules(name: str) -> dict | None
    rules_source(name: str) -> str  # debug: cache | bundled | none
    clear_cache()                   # gọi sau khi sync để buộc reload
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

# Cache directory (sync target từ cloud)
_CACHE_DIR = Path(
    os.environ.get("VBHC_CACHE_DIR")
    or (Path.home() / ".vbhc" / "cache")
).expanduser()

# Bundled directory (rơi vào khi cache thiếu hoặc offline)
# scripts/ → repo root → tri-thuc-template/rules/
_BUNDLED_DIR = Path(__file__).resolve().parent.parent / "tri-thuc-template" / "rules"

# In-memory cache: name → (path_used, parsed_dict)
_loaded: dict[str, tuple[str, dict]] = {}


def _candidate_paths(name: str) -> list[tuple[str, Path]]:
    """Trả [(source_label, path)] theo thứ tự ưu tiên."""
    stem = name.removesuffix(".yaml").removesuffix(".yml")
    return [
        ("cache", _CACHE_DIR / "rules" / f"{stem}.yaml"),
        ("cache", _CACHE_DIR / "rules" / f"{stem}.yml"),
        ("bundled", _BUNDLED_DIR / f"{stem}.yaml"),
        ("bundled", _BUNDLED_DIR / f"{stem}.yml"),
    ]


def load_rules(name: str) -> dict[str, Any] | None:
    """Load rules YAML. Trả None nếu không tìm thấy ở cả cache lẫn bundled."""
    if name in _loaded:
        return _loaded[name][1]
    for source, path in _candidate_paths(name):
        if path.is_file():
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                continue
            _loaded[name] = (source, data)
            return data
    return None


def rules_source(name: str) -> str:
    """Debug: trả 'cache' / 'bundled' / 'none' cho rule đã load."""
    if name not in _loaded:
        # Force load để biết nguồn
        load_rules(name)
    if name in _loaded:
        return _loaded[name][0]
    return "none"


def clear_cache():
    """Gọi sau khi sync_knowledge → buộc reload từ disk lần tới."""
    _loaded.clear()
