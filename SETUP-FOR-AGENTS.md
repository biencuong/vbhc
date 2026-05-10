# Setup hướng dẫn cho các agent

Skill `soan-thao-vbhc` gồm 2 thành phần độc lập:

| Thành phần | Vai trò | Cài như nào |
|---|---|---|
| **MCP server `vbhc`** | 9 tools deterministic (classify, create_workfolder, reorganize, fill_template, validate, aggregate_survey, regenerate_check, **load_org_config**, **suggest_noi_nhan**) | JSON config trong agent |
| **Skill text** | Workflow 6 pha + interview questions + danh mục VB | Native (nếu agent hỗ trợ) hoặc inject vào system prompt |

## 3-tier storage layout (bắt buộc khi setup multi-user)

| Tier | Vị trí | Mục đích | Sửa đổi |
|---|---|---|---|
| **SKILL** | `D:\SKILL_AI\skills\soan-thao-vbhc\` | Code + danh-muc-loai-vb chuẩn | Read-only |
| **ORG**   | `$VBHC_ORG_DIR` (default `~/.vbhc/org/`) | Cấu hình chung cơ quan: thông tin cơ quan, người ký, **phân công nhiệm vụ**, **căn cứ pháp lý mẫu** | Cơ quan tự sửa |
| **USER**  | Tham số trong tool call (`parent_dir`, `work_folder`) hoặc `$VBHC_USER_DIR` | File công việc cụ thể + tham chiếu | Mỗi user/máy |

**Cài ORG tier (1 lần / cơ quan):**

```powershell
# Windows: tạo ORG dir mặc định + copy template
New-Item -ItemType Directory -Path "$HOME\.vbhc\org" -Force
Copy-Item "D:\SKILL_AI\skills\soan-thao-vbhc\tri-thuc-template\*.yaml" `
          -Destination "$HOME\.vbhc\org\"
# Sửa nội dung trong $HOME\.vbhc\org\05-thong-tin-co-quan.yaml v.v.
```

```bash
# Mac/Linux:
mkdir -p ~/.vbhc/org
cp /path/to/skills/soan-thao-vbhc/tri-thuc-template/*.yaml ~/.vbhc/org/
# Sửa nội dung cho phù hợp cơ quan.
```

Hoặc dùng folder khác (vd team share trên server):
```powershell
[Environment]::SetEnvironmentVariable("VBHC_ORG_DIR", "\\fileserver\SoGDDT_VBHC", "User")
```

## Yêu cầu chung

```bash
pip install mcp python-docx openpyxl
```

Python ≥ 3.10. Test:
```bash
python -c "import mcp, docx, openpyxl; print('OK')"
```

---

## A. MCP server — universal config

Có **2 cách deploy** MCP server:

### A.1. Stdio (local, mỗi máy 1 process — đơn giản nhất)

Đa số agent dùng JSON config tương tự nhau. Đường dẫn config khác nhau:

| Agent | File config |
|---|---|
| Claude Desktop | `%APPDATA%\Claude\claude_desktop_config.json` (Win) / `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) |
| Claude Code | `~/.claude.json` (hoặc `claude mcp add vbhc -s user -- ...`) |
| Cursor | `~/.cursor/mcp.json` |
| Cline | UI Settings → MCP Servers |
| qwenpaw | `~/.qwenpaw/config.json` (đoán) |

Nội dung chung:

```json
{
  "mcpServers": {
    "vbhc": {
      "command": "python",
      "args": ["D:\\SKILL_AI\\skills\\soan-thao-vbhc\\mcp\\server.py"]
    }
  }
}
```

Trên Mac/Linux:
```json
{
  "mcpServers": {
    "vbhc": {
      "command": "python3",
      "args": ["/path/to/skills/soan-thao-vbhc/mcp/server.py"]
    }
  }
}
```

Restart agent. Tools sẽ xuất hiện dưới prefix `mcp__vbhc__*` (hoặc `vbhc.*` tùy agent).

### A.2. HTTP server (deploy 1 server cho team / phòng / Sở)

**Server side** (chạy trên VPS hoặc máy chủ nội bộ):

```bash
# Cài deps trên server
pip install mcp python-docx openpyxl pyyaml

# Chạy server (foreground, hoặc dùng systemd/pm2)
python /opt/vbhc/mcp/server.py --http --host 0.0.0.0 --port 8765
```

Server log:
```
[vbhc] HTTP server: http://0.0.0.0:8765/mcp
[vbhc] SKILL_DIR = /opt/vbhc
[vbhc] ORG_DIR   = /opt/vbhc-org
```

**Client side** (config trong agent):

```json
{
  "mcpServers": {
    "vbhc": {
      "url": "http://your-server.local:8765/mcp"
    }
  }
}
```

(thay URL bằng địa chỉ thật, dùng HTTPS + reverse proxy nếu deploy ngoài LAN)

**Lưu ý khi deploy HTTP:**
- ORG dir chứa thông tin chung cơ quan (chia sẻ giữa users → đặt trên server)
- USER dir vẫn ở máy mỗi người (file công việc + tham chiếu) — tool nhận `parent_dir` qua tham số, KHÔNG đọc từ disk server
- Cần thêm authentication nếu mở ra ngoài LAN (FastMCP có hooks middleware)

### Verify MCP đã chạy

```bash
python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"
# Server block chờ stdin → đó là behavior đúng. Ctrl+C để dừng.
```

---

## B. Skill — 2 cách

### Cách 1: Agent hỗ trợ Anthropic Skill format (Claude Desktop/Code)

Copy hoặc symlink skill folder vào nơi agent scan:

**Claude Desktop / Claude Code:**
```powershell
# Windows (PowerShell admin)
New-Item -ItemType SymbolicLink `
    -Path "$env:USERPROFILE\.claude\skills\soan-thao-vbhc" `
    -Target "D:\SKILL_AI\skills\soan-thao-vbhc"
```

```bash
# Mac/Linux
ln -s /path/to/skills/soan-thao-vbhc ~/.claude/skills/soan-thao-vbhc
```

### Cách 2: Agent KHÔNG hỗ trợ skill native (Cursor, Cline, Continue, custom)

Inject SKILL.md + resources vào system prompt / custom instructions:

#### Cursor
Tạo file `.cursor/rules/soan-thao-vbhc.md` trong project, sửa frontmatter:

```markdown
---
description: Soạn VBHC theo NĐ 30/2020. Trigger khi user nói "soạn công văn/tờ trình/báo cáo/phiếu biểu quyết..."
globs: ["**/cong-viec/**"]
alwaysApply: false
---

[Paste toàn bộ nội dung SKILL.md vào đây]
```

#### Cline
Settings → Custom Instructions → paste nội dung SKILL.md + workflow-7-buoc.md.

#### Custom agent (Python)
```python
from pathlib import Path

SKILL_DIR = Path("D:/SKILL_AI/skills/soan-thao-vbhc")

def build_system_prompt():
    files = [
        SKILL_DIR / "SKILL.md",
        SKILL_DIR / "resources" / "workflow-7-buoc.md",
        SKILL_DIR / "resources" / "interview-questions.md",
        SKILL_DIR / "resources" / "danh-muc-loai-vb.md",
        SKILL_DIR / "resources" / "the-thuc-vbhc-checklist.md",
    ]
    return "\n\n---\n\n".join(f.read_text(encoding="utf-8") for f in files)

# Pass to your LLM
system_prompt = build_system_prompt()
```

---

## C. Hướng dẫn cụ thể từng agent

### Claude Desktop / Claude Code

```powershell
# 1. MCP
claude mcp add vbhc -s user -- python "D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py"

# 2. Skill
New-Item -ItemType SymbolicLink `
    -Path "$env:USERPROFILE\.claude\skills\soan-thao-vbhc" `
    -Target "D:\SKILL_AI\skills\soan-thao-vbhc"

# 3. Restart Claude Code
# 4. Test: "soạn cho tôi 1 báo cáo góp ý..."
```

### Cursor (kèm Claude/Qwen/GPT)

`~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "vbhc": {
      "command": "python",
      "args": ["D:\\SKILL_AI\\skills\\soan-thao-vbhc\\mcp\\server.py"]
    }
  }
}
```

Skill: copy SKILL.md → `.cursor/rules/` trong project Vietnam admin doc của bạn.

### qwenpaw

Test trước:
```bash
qwenpaw --help | grep -i mcp
qwenpaw --help | grep -i skill
```

Nếu có lệnh `qwenpaw mcp add` → dùng tương tự Claude Code.
Nếu chỉ có file config JSON → dùng pattern mcpServers như trên.

Skill: nếu qwenpaw có `~/.qwenpaw/skills/` → copy folder vào. Không có thì inject system prompt.

### Cline / Roo Code

UI → MCP Servers → Add:
- Name: `vbhc`
- Command: `python`
- Args: `D:\SKILL_AI\skills\soan-thao-vbhc\mcp\server.py`

Skill: paste SKILL.md vào Custom Instructions.

### Continue.dev

`~/.continue/config.json`:
```json
{
  "mcpServers": [
    {
      "name": "vbhc",
      "command": "python",
      "args": ["D:\\SKILL_AI\\skills\\soan-thao-vbhc\\mcp\\server.py"]
    }
  ]
}
```

### Aider

Aider không hỗ trợ MCP native (tới tháng 5/2026), nhưng:
1. Bật `--read-only` cho `D:/SKILL_AI/skills/soan-thao-vbhc/SKILL.md` để Aider load như reference
2. Hoặc dùng `aider --message-file` với system prompt = SKILL.md

### LangChain / LlamaIndex / custom agent

Dùng `mcp` Python SDK làm client:
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="python",
    args=["D:/SKILL_AI/skills/soan-thao-vbhc/mcp/server.py"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("vbhc_classify",
                                          {"description": "soạn báo cáo..."})
```

Skill: load SKILL.md + resources → inject system prompt như section B.

---

## D. Verify after setup

Trong agent, hỏi:
> Liệt kê các tool MCP `vbhc_*` mà bạn có

Nếu agent trả lời 7 tools → **MCP OK**.

Tiếp theo:
> Tôi muốn soạn 1 phiếu biểu quyết cho thành viên UBND tỉnh

Nếu agent gọi `vbhc_classify` → confirm "Phiếu biểu quyết" → hỏi tiếp về người ký → **Skill OK**.

---

## E. Troubleshooting

### "ModuleNotFoundError: mcp"
→ `pip install mcp` (Python ≥ 3.10).

### "ModuleNotFoundError: docx"
→ `pip install python-docx` (KHÔNG phải `pip install docx`).

### Agent không thấy tools
→ Check agent log có lỗi spawn server không. Test server trực tiếp:
```bash
echo '{"jsonrpc":"2.0","method":"initialize","id":1,"params":{}}' | python server.py
```
Phải trả về JSON response → server OK.

### Path Windows vs Mac
- Windows: dùng double backslash `D:\\path\\to\\file` hoặc forward slash `D:/path/to/file`
- Mac/Linux: forward slash thường

### Tracked changes không có tên thật
Server `vbhc` dùng python-docx — không hỗ trợ tracked changes. Cần dùng song song `word-mcp-live` (Windows-only) cho live editing.

---

## F. Đóng gói để share cho team

Nếu muốn share skill này cho đồng nghiệp / team:

1. Zip folder `soan-thao-vbhc/` (hoặc push lên GitHub)
2. Đồng nghiệp:
   - Extract / clone về máy
   - Cài deps: `pip install mcp python-docx openpyxl`
   - Sửa path trong config JSON theo máy của họ
   - Sửa `tri-thuc/05-thong-tin-co-quan.yaml` nếu khác cơ quan

Hoặc package thành 1 PyPI package + uvx:
```bash
# Future: uvx soan-thao-vbhc
```
(Cần thêm setup.py / pyproject.toml ở root + publish.)
