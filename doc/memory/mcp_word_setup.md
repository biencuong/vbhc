---
name: word MCP setup
description: Cấu hình MCP word-mcp-live đã cài cho user (scope user, dùng cho VBHC theo Nghị định 30)
type: reference
originSessionId: 89cb4eaa-185b-4534-8ccd-a20b1b647050
---
MCP server `word` (word-mcp-live v1.6.2) đã được cài qua `uv tool install word-mcp-live` và đăng ký với Claude Code ở scope user (~/.claude.json).

- Executable: `C:\Users\AD\AppData\Roaming\uv\tools\word-mcp-live\Scripts\word_mcp_server.exe`
- Env hiện tại: MCP_AUTHOR=User, MCP_AUTHOR_INITIALS=U (placeholder — user có thể đổi để tracked changes hiển thị tên thật)
- 124 tools: 80 cross-platform (python-docx) + 44 Windows COM live editing

Đổi tên tác giả tracked changes:
```
claude mcp remove word -s user
claude mcp add word -s user -e MCP_AUTHOR="Tên thật" -e MCP_AUTHOR_INITIALS="TT" -- "C:\Users\AD\AppData\Roaming\uv\tools\word-mcp-live\Scripts\word_mcp_server.exe"
```

Cập nhật package: `uv tool upgrade word-mcp-live`

Tools sẽ xuất hiện dưới dạng `mcp__word__*` sau khi restart Claude Code.
