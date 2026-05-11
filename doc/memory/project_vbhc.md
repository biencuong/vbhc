---
name: VBHC MCP project
description: Mục tiêu xây hệ MCP fill nội dung vào template .docx chuẩn Nghị định 30/2020
type: project
originSessionId: 89cb4eaa-185b-4534-8ccd-a20b1b647050
---
Thư mục dự án: D:\SKILL_AI\SoanThaoVB_

Mục tiêu: Dùng MCP Word + bộ template .docx tự tạo theo Nghị định 30/2020 để AI fill nội dung tự động.

**Why:** Không có MCP công khai nào hỗ trợ sẵn mẫu VBHC Việt Nam (Quốc hiệu, Tiêu ngữ, 25 mẫu của ND30). Phải tự build tầng template lên trên một MCP Word có sẵn.

**How to apply:** Khi user giao việc liên quan, kiến trúc gồm 3 lớp:
1. MCP Word (Office-Word-MCP của GongRzhe HOẶC MCP-Doc của MeterLong) — engine
2. Thư mục `templates/` chứa các file .docx mẫu chuẩn ND30 (mỗi loại 1 file, có placeholder Jinja2 nếu dùng docxtpl)
3. Skill/script wrapper để chọn template + fill data + xuất file

Lưu ý Office-Word-MCP đã archive 3/2026 → cân nhắc fork hoặc dùng MCP-Doc thay thế. Cần xác nhận với user trước khi cài.
