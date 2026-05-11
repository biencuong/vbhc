# `doc/` — Tài liệu bàn giao v1.0

Folder này chứa toàn bộ context cần thiết để **phiên tiếp theo** (Codex hoặc agent khác) tiếp tục dự án nâng cấp v1.0.

## Đọc theo thứ tự

1. **[HANDOFF-v1.0-WIP.md](HANDOFF-v1.0-WIP.md)** — tài liệu chính, đầy đủ ngữ cảnh + đang dở chỗ nào + việc cần tiếp.
2. **[PLAN-v1.0.md](PLAN-v1.0.md)** — plan kiến trúc đầy đủ đã được user duyệt (Local Thin-MCP + Cloud Knowledge Hub + Auto-bootstrap).
3. **[memory/](memory/)** — bộ nhớ persistent của Claude từ các phiên trước (user profile, project context, feedback, references).
   - Bắt đầu bằng [memory/MEMORY.md](memory/MEMORY.md) (index).

## Tài liệu nền (ở root skill, không ở đây)

- `../HANDOFF.md` — bàn giao kiến trúc skill pre-v1.0
- `../SKILL.md` — workflow 7 bước + anti-patterns
- `../UPGRADE-MULTI-CLIENT.md` — bối cảnh đa client v0.9 (đang được v1.0 thay thế)
- `../README.md`, `../INSTALL.md`, `../INSTALL-AAPANEL.md` — chưa cập nhật cho v1.0
